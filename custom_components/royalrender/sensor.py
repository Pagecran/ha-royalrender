"""Farm counters, queue details and individual machine status."""
from homeassistant.components.sensor import SensorEntity

from .entity import RoyalRenderEntity, discover_machines


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([FarmSensor(c, key, name) for key, name in (
        ("jobs_rendering", "Rendering jobs"), ("jobs_waiting", "Waiting jobs"),
        ("jobs_problem", "Problem jobs"), ("machines_rendering", "Rendering machines"),
    )] + [QueueSensor(c)])
    discover_machines(entry, async_add_entities, lambda name: [MachineSensor(c, name)])


class FarmSensor(RoyalRenderEntity, SensorEntity):
    def __init__(self, coordinator, key, name):
        super().__init__(coordinator, key, name)
        self.key = key

    @property
    def native_value(self):
        return self.coordinator.data["summary"][self.key]

    @property
    def icon(self):
        return "mdi:alert-circle" if self.key == "jobs_problem" and self.native_value else "mdi:render"

    @property
    def extra_state_attributes(self):
        if self.key != "jobs_problem":
            return None
        return {"jobs": [j for j in self.coordinator.data["jobs"] if j["problem"]]}


class QueueSensor(RoyalRenderEntity, SensorEntity):
    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator):
        super().__init__(coordinator, "queue", "Queue")

    @property
    def native_value(self):
        return sum(not j["finished"] for j in self.coordinator.data["jobs"])

    @property
    def extra_state_attributes(self):
        return {"jobs": [j for j in self.coordinator.data["jobs"] if not j["finished"]],
                "groups": self.coordinator.data["groups"],
                "updated_at": self.coordinator.data["updated_at"]}


class MachineSensor(RoyalRenderEntity, SensorEntity):
    _attr_icon = "mdi:server"

    def __init__(self, coordinator, machine):
        super().__init__(coordinator, "status", "Status", machine)

    @property
    def native_value(self):
        if not self.machine_data:
            return None
        return " / ".join(dict.fromkeys(self.machine_data["states"]))[:255]

    @property
    def extra_state_attributes(self):
        return self.machine_data
