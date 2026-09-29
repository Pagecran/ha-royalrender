"""Authenticated, cached HTTP interface to a single-threaded native RR SDK."""
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hmac
import logging
from logging.handlers import RotatingFileHandler
import ssl
import time

from aiohttp import web

from . import VERSION
from .config import Config
from .health import HealthTracker
from .sdk import RoyalRenderSDK, CLIENT_COMMANDS

LOG = logging.getLogger(__name__)


class Bridge:
    def __init__(self, config, sdk=None):
        self.config = config
        self.sdk = sdk or RoyalRenderSDK(config)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rr-sdk")
        self.lock = asyncio.Lock()
        self.health = HealthTracker(config.error_window_seconds)
        self.data = None
        self.last_success = 0.0
        self.last_error = None

    async def run(self, function, *args):
        async with self.lock:
            return await asyncio.get_running_loop().run_in_executor(self.executor, function, *args)

    async def refresh(self):
        try:
            data = await self.run(self.sdk.snapshot)
            self.health.apply(data["jobs"], time.monotonic())
            data.update({"bridge_id": self.config.bridge_id, "version": VERSION,
                         "api_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(),
                         "commands_enabled": self.config.allow_commands})
            data["summary"] = {
                "jobs_rendering": sum(j["rendering"] for j in data["jobs"]),
                "jobs_waiting": sum(j["health"] == "waiting" for j in data["jobs"]),
                "jobs_problem": sum(j["problem"] for j in data["jobs"]),
                "machines_rendering": sum(m["rendering"] for m in data["machines"]),
            }
            self.data = data
            self.last_success = time.monotonic()
            self.last_error = None
        except Exception:
            self.last_error = "Royal Render unavailable; inspect bridge logs"
            LOG.exception("Royal Render polling failed")

    def available(self):
        return (self.data is not None and self.last_error is None
                and time.monotonic() - self.last_success < self.config.poll_seconds * 3)


BRIDGE_KEY = web.AppKey("bridge", Bridge)


def create_app(config, sdk=None):
    bridge = Bridge(config, sdk)

    @web.middleware
    async def authenticate(request, handler):
        expected = "Bearer " + config.api_key
        if not hmac.compare_digest(request.headers.get("Authorization", "").encode(), expected.encode()):
            raise web.HTTPUnauthorized()
        return await handler(request)

    app = web.Application(middlewares=[authenticate], client_max_size=16 * 1024)
    app[BRIDGE_KEY] = bridge

    async def snapshot(request):
        if not bridge.available():
            raise web.HTTPServiceUnavailable(text="Royal Render data unavailable or stale")
        return web.json_response(bridge.data, headers={"Cache-Control": "no-store"})

    async def command(request):
        if not config.allow_commands:
            raise web.HTTPForbidden(text="Commands disabled in bridge configuration")
        if not bridge.available():
            raise web.HTTPServiceUnavailable(text="Royal Render data unavailable or stale")
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            if request.match_info["kind"] == "machines":
                if set(payload) != {"machine", "action"} or not isinstance(payload["machine"], str):
                    raise ValueError("Expected machine and action")
                if payload["action"] not in CLIENT_COMMANDS:
                    raise ValueError("Unknown action")
                result = await bridge.run(bridge.sdk.machine_command, payload["machine"], payload["action"])
            elif request.match_info["kind"] == "assignments":
                if set(payload) != {"job_id", "groups", "mode"}:
                    raise ValueError("Expected job_id, groups and mode")
                if (not isinstance(payload["groups"], list) or not payload["groups"]
                        or not all(isinstance(g, str) for g in payload["groups"])):
                    raise ValueError("groups must be a nonempty list of names")
                result = await bridge.run(bridge.sdk.assign_groups, payload["job_id"], payload["groups"], payload["mode"])
            else:
                raise web.HTTPNotFound()
        except (ValueError, TypeError, KeyError):
            raise web.HTTPBadRequest(text="Invalid command or unknown target") from None
        except web.HTTPException:
            raise
        except Exception:
            LOG.exception("Royal Render command failed; not retried")
            raise web.HTTPBadGateway(text="RR command failed; verify RR state before retrying") from None
        LOG.info("Command accepted: %s", result)
        # Accepted is not a promise of immediately observed state.
        return web.json_response(result)

    async def lifecycle(app):
        async def poll():
            while True:
                await bridge.refresh()
                await asyncio.sleep(config.poll_seconds)
        task = asyncio.create_task(poll())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        bridge.executor.shutdown(wait=False, cancel_futures=True)

    app.cleanup_ctx.append(lifecycle)
    app.router.add_get("/api/v1/snapshot", snapshot)
    app.router.add_post("/api/v1/{kind}/command", command)
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--log-file")
    args = parser.parse_args()
    config = Config.load(args.config)
    handlers = [RotatingFileHandler(args.log_file, maxBytes=5_000_000, backupCount=3, encoding="utf-8")] if args.log_file else None
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)
    tls = None
    if config.tls_cert:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(config.tls_cert, config.tls_key)
    web.run_app(create_app(config), host=config.listen_host, port=config.listen_port,
                ssl_context=tls, access_log=None)


if __name__ == "__main__":
    main()
