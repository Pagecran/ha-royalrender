"""Royal Render Home Assistant integration."""
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import API, BridgeError, AuthenticationError
from .const import DOMAIN, CONF_URL, CONF_API_KEY, PLATFORMS, COMMANDS
from .coordinator import RoyalRenderCoordinator


async def async_setup(hass, config):
    async def action(call):
        entry = hass.config_entries.async_get_entry(call.data["config_entry_id"])
        if entry is None or entry.domain != DOMAIN or not getattr(entry, "runtime_data", None):
            raise HomeAssistantError("Royal Render integration is not loaded")
        coordinator = entry.runtime_data
        if not coordinator.last_update_success or not coordinator.data.get("commands_enabled"):
            raise HomeAssistantError("Bridge unavailable or commands disabled")
        if call.service == "machine_command":
            kind = "machines"
            payload = {k: call.data[k] for k in ("machine", "action")}
        else:
            kind = "assignments"
            payload = {k: call.data[k] for k in ("job_id", "groups", "mode")}
        try:
            await coordinator.api.command(kind, payload)
        except (BridgeError, AuthenticationError) as error:
            raise HomeAssistantError(str(error)) from error
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "machine_command", action, schema=vol.Schema({
        vol.Required("config_entry_id"): str,
        vol.Required("machine"): str,
        vol.Required("action"): vol.In(COMMANDS),
    }))
    hass.services.async_register(DOMAIN, "assign_groups", action, schema=vol.Schema({
        vol.Required("config_entry_id"): str,
        vol.Required("job_id"): vol.All(str, vol.Match(r"^[0-9]+$")),
        vol.Required("groups"): vol.All([str], vol.Length(min=1)),
        vol.Optional("mode", default="add"): vol.In(("add", "remove", "replace")),
    }))
    return True


async def async_setup_entry(hass, entry):
    api = API(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_KEY])
    coordinator = RoyalRenderCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if result:
        entry.runtime_data = None
    return result
