import time
from unittest.mock import Mock

from aiohttp.test_utils import TestClient, TestServer
import pytest

from rr_ha_bridge.config import Config
from rr_ha_bridge.server import BRIDGE_KEY, create_app


KEY = "a" * 48


@pytest.fixture
async def client():
    cfg = Config("test-bridge", KEY, "unused", "unused", allow_commands=True)
    sdk = Mock()
    sdk.snapshot.return_value = {"machines": [], "jobs": [], "groups": []}
    sdk.machine_command.return_value = {"accepted": True}
    app = create_app(cfg, sdk)
    async with TestClient(TestServer(app)) as client:
        await app[BRIDGE_KEY].refresh()
        yield client, app[BRIDGE_KEY], sdk


async def test_auth_read_and_no_side_effects(client):
    http, bridge, sdk = client
    response = await http.get("/api/v1/snapshot")
    assert response.status == 401
    response = await http.post("/api/v1/machines/command", json={"machine": "node-a", "action": "disable"})
    assert response.status == 401
    sdk.machine_command.assert_not_called()
    response = await http.get("/api/v1/snapshot", headers={"Authorization": f"Bearer {KEY}"})
    assert response.status == 200
    assert (await response.json())["bridge_id"] == "test-bridge"
    sdk.machine_command.assert_not_called()


async def test_commands_not_retried_and_bad_actions_rejected(client):
    http, bridge, sdk = client
    headers = {"Authorization": f"Bearer {KEY}"}
    response = await http.post("/api/v1/machines/command", headers=headers,
                               json={"machine": "node-a", "action": "shell"})
    assert response.status == 400
    sdk.machine_command.assert_not_called()
    sdk.machine_command.side_effect = RuntimeError("transport failed")
    response = await http.post("/api/v1/machines/command", headers=headers,
                               json={"machine": "node-a", "action": "disable"})
    assert response.status == 502
    sdk.machine_command.assert_called_once()


async def test_stale_or_failed_poll_is_unavailable(client):
    http, bridge, sdk = client
    headers = {"Authorization": f"Bearer {KEY}"}
    bridge.last_success = time.monotonic() - 100
    assert (await http.get("/api/v1/snapshot", headers=headers)).status == 503
    assert (await http.post("/api/v1/machines/command", headers=headers,
                           json={"machine": "node-a", "action": "disable"})).status == 503
    sdk.machine_command.assert_not_called()
    sdk.snapshot.side_effect = RuntimeError("RR unavailable")
    await bridge.refresh()
    assert not bridge.available()


async def test_monitor_only_blocks_commands():
    cfg = Config("test", KEY, "unused", "unused")
    sdk = Mock()
    sdk.snapshot.return_value = {"machines": [], "jobs": [], "groups": []}
    app = create_app(cfg, sdk)
    async with TestClient(TestServer(app)) as client:
        response = await client.post("/api/v1/machines/command", headers={"Authorization": f"Bearer {KEY}"},
                                     json={"machine": "node-a", "action": "disable"})
        assert response.status == 403
        sdk.machine_command.assert_not_called()
