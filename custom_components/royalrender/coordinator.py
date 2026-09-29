"""One cached poll per configured bridge, shared by all entities."""
from datetime import timedelta
import logging

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthenticationError, BridgeError
from .job_filter import filter_snapshot

LOG = logging.getLogger(__name__)


class RoyalRenderCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, api):
        super().__init__(hass, LOG, name="Royal Render", config_entry=entry,
                         update_interval=timedelta(seconds=entry.options.get("scan_interval", 15)))
        self.api = api
        self.bridge_id = entry.unique_id
        self.history_days = entry.options.get("history_days", 10)

    async def _async_update_data(self):
        try:
            data = await self.api.snapshot()
            if data["bridge_id"] != self.bridge_id:
                raise UpdateFailed("Bridge identity changed; reconfigure this integration")
            return filter_snapshot(data, self.history_days)
        except AuthenticationError as error:
            raise ConfigEntryAuthFailed(str(error)) from error
        except BridgeError as error:
            raise UpdateFailed(str(error)) from error
