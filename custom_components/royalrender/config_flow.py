"""UI setup, reconfiguration and polling options."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .api import API, AuthenticationError, BridgeError, normalize_url
from .const import DOMAIN, CONF_URL, CONF_API_KEY


class RoyalRenderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def configure(self, step, user_input):
        errors = {}
        entry = self._get_reconfigure_entry() if step == "reconfigure" else None
        if user_input is not None:
            try:
                data = {CONF_URL: normalize_url(user_input[CONF_URL]),
                        CONF_API_KEY: user_input[CONF_API_KEY]}
                result = await API(async_get_clientsession(self.hass), data[CONF_URL], data[CONF_API_KEY]).snapshot()
                if entry and result["bridge_id"] != entry.unique_id:
                    return self.async_abort(reason="wrong_bridge")
                await self.async_set_unique_id(result["bridge_id"])
                if entry:
                    return self.async_update_reload_and_abort(entry, data_updates=data)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Royal Render", data=data)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except (BridgeError, ValueError):
                errors["base"] = "cannot_connect"
        schema = vol.Schema({
            vol.Required(CONF_URL, default=entry.data[CONF_URL] if entry else "http://"):
                selector.TextSelector(),
            vol.Required(CONF_API_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
        })
        return self.async_show_form(step_id=step, data_schema=schema, errors=errors)

    async def async_step_user(self, user_input=None):
        return await self.configure("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self.configure("reconfigure", user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            try:
                result = await API(async_get_clientsession(self.hass), entry.data[CONF_URL],
                                   user_input[CONF_API_KEY]).snapshot()
                if result["bridge_id"] != entry.unique_id:
                    return self.async_abort(reason="wrong_bridge")
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except BridgeError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="reauth_confirm", errors=errors, data_schema=vol.Schema({
            vol.Required(CONF_API_KEY): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return RoyalRenderOptionsFlow()


class RoyalRenderOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required("scan_interval", default=self.config_entry.options.get("scan_interval", 15)):
                vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
        }))
