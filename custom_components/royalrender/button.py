"""Explicit commands; no optimistic state changes or automatic command retries."""
from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError

from .api import AuthenticationError, BridgeError
from .const import COMMANDS
from .entity import RoyalRenderEntity, discover_machines


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    discover_machines(entry, async_add_entities, lambda name: [
        MachineButton(c, name, action, label, icon) for action, (label, icon) in COMMANDS.items()
    ])


class MachineButton(RoyalRenderEntity, ButtonEntity):
    def __init__(self, coordinator, machine, action, label, icon):
        super().__init__(coordinator, action, label, machine)
        self.action = action
        self._attr_icon = icon

    @property
    def available(self):
        return super().available and self.coordinator.data.get("commands_enabled", False)

    async def async_press(self):
        if not self.available:
            raise HomeAssistantError("Machine unavailable or commands disabled")
        try:
            await self.coordinator.api.command("machines", {"machine": self.machine, "action": self.action})
        except (BridgeError, AuthenticationError) as error:
            raise HomeAssistantError(str(error)) from error
        await self.coordinator.async_request_refresh()
