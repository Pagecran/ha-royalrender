"""Entities share one coordinator and stable bridge-scoped identifiers."""
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class RoyalRenderEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name, machine=None):
        super().__init__(coordinator)
        self.machine = machine
        self._attr_name = name
        base = coordinator.bridge_id
        device_id = f"{base}:machine:{machine}" if machine else base
        self._attr_unique_id = f"{device_id}:{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=machine or "Royal Render", manufacturer="Royal Render",
            model="Render client" if machine else "Bridge",
            via_device=(DOMAIN, base) if machine else None,
        )

    @property
    def machine_data(self):
        return next((m for m in self.coordinator.data["machines"] if m["id"] == self.machine), None)

    @property
    def available(self):
        return super().available and (self.machine is None or self.machine_data is not None)


def discover_machines(entry, async_add_entities, factory):
    coordinator = entry.runtime_data
    known = set()

    def discover():
        entities = []
        for machine in coordinator.data["machines"]:
            if machine["id"] not in known:
                known.add(machine["id"])
                entities.extend(factory(machine["id"]))
        if entities:
            async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))
