from unittest.mock import AsyncMock, patch

from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.royalrender.api import BridgeError


async def setup(hass):
    entry = MockConfigEntry(domain="royalrender", unique_id="test-bridge", title="Royal Render",
                            data={"url": "http://bridge.example:8787", "api_key": "x" * 48})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_dynamic_entities_and_outage(hass, api_snapshot):
    entry = await setup(hass)
    assert hass.states.get("sensor.royal_render_rendering_jobs").state == "1"
    assert hass.states.get("binary_sensor.royal_render_jobs_need_attention").state == "on"
    assert hass.states.get("binary_sensor.node_a_rendering").state == "on"
    c = entry.runtime_data
    data = dict(c.data)
    data["machines"] = [*data["machines"], {**data["machines"][0], "id": "node-b", "name": "node-b"}]
    c.async_set_updated_data(data)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.node_b_rendering").state == "on"
    api_snapshot.side_effect = BridgeError("offline")
    await c.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.royal_render_jobs_need_attention").state == "unavailable"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_actions_preserve_job_id_and_unload(hass, api_snapshot):
    entry = await setup(hass)
    with patch("custom_components.royalrender.api.API.command", new_callable=AsyncMock) as command:
        command.return_value = {"accepted": True}
        await hass.services.async_call("royalrender", "assign_groups", {
            "config_entry_id": entry.entry_id, "job_id": "1877000000000000001", "groups": ["CPU"],
        }, blocking=True)
        command.assert_awaited_once_with("assignments", {
            "job_id": "1877000000000000001", "groups": ["CPU"], "mode": "add",
        })
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_ui_flow_and_duplicate(hass, api_snapshot):
    result = await hass.config_entries.flow.async_init("royalrender", context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    with patch("custom_components.royalrender.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"],
            {"url": "http://bridge.example:8787/", "api_key": "x" * 48})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["url"] == "http://bridge.example:8787"
        result = await hass.config_entries.flow.async_init("royalrender", context={"source": "user"},
            data={"url": "http://bridge.example:8787", "api_key": "x" * 48})
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"
