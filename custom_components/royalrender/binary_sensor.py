"""Problem indicators and per-machine render activity."""
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import RoyalRenderEntity, discover_machines


async def async_setup_entry(hass, entry, async_add_entities):
    c = entry.runtime_data
    async_add_entities([ProblemSensor(c)])
    discover_machines(entry, async_add_entities, lambda name: [RenderingSensor(c, name)])


class ProblemSensor(RoyalRenderEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator):
        super().__init__(coordinator, "problem", "Jobs need attention")

    @property
    def is_on(self):
        return self.coordinator.data["summary"]["jobs_problem"] > 0


class RenderingSensor(RoyalRenderEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator, machine):
        super().__init__(coordinator, "rendering", "Rendering", machine)

    @property
    def is_on(self):
        return self.machine_data["rendering"] if self.machine_data else None
