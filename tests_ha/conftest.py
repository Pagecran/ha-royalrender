from copy import deepcopy
from unittest.mock import AsyncMock, patch

import pytest


SNAPSHOT = {
    "bridge_id": "test-bridge", "api_version": 1, "version": "0.1.0",
    "updated_at": "2026-09-29T10:00:00+00:00", "commands_enabled": True,
    "summary": {"jobs_rendering": 1, "jobs_waiting": 0, "jobs_problem": 1, "machines_rendering": 1},
    "machines": [{"id": "node-a", "name": "node-a", "enabled": True, "rendering": True,
                  "states": ["Rendering"], "jobs": ["1877000000000000001"], "cpu_percent": 98}],
    "jobs": [{"id": "1877000000000000001", "label": "TEST", "health": "warning",
              "problem": True, "finished": False, "done": 1, "total": 10}],
    "groups": [{"name": "CPU", "clients": ["node-a"]}],
}


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def api_snapshot():
    with patch("custom_components.royalrender.api.API.snapshot", new_callable=AsyncMock) as mock:
        mock.return_value = deepcopy(SNAPSHOT)
        yield mock
