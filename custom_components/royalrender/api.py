"""HTTP client; no RR native binaries loaded inside Home Assistant."""
import asyncio
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession, ClientTimeout


class AuthenticationError(Exception):
    pass


class BridgeError(Exception):
    pass


def normalize_url(url):
    url = url.strip().rstrip("/")
    parsed = urlsplit(url)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path):
        raise ValueError("Use a base HTTP(S) URL without credentials, path or query")
    return url


class API:
    def __init__(self, session: ClientSession, url: str, key: str):
        self.session = session
        self.url = normalize_url(url)
        self.key = key

    async def request(self, method, path, payload=None):
        try:
            async with self.session.request(
                method, self.url + "/api/v1/" + path,
                headers={"Authorization": "Bearer " + self.key},
                json=payload, timeout=ClientTimeout(total=20), allow_redirects=False,
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid bridge API key")
                if response.status != 200:
                    raise BridgeError(f"Bridge returned HTTP {response.status}")
                result = await response.json()
                if not isinstance(result, dict):
                    raise BridgeError("Invalid bridge response")
                return result
        except (ClientError, asyncio.TimeoutError, ValueError) as error:
            raise BridgeError("Cannot communicate with bridge") from error

    async def snapshot(self):
        data = await self.request("GET", "snapshot")
        if (data.get("api_version") != 1 or not data.get("bridge_id")
                or not all(isinstance(data.get(k), list) for k in ("machines", "jobs", "groups"))
                or not isinstance(data.get("summary"), dict) or not data.get("updated_at")):
            raise BridgeError("Unsupported or invalid bridge snapshot")
        return data

    async def command(self, kind, payload):
        return await self.request("POST", f"{kind}/command", payload)
