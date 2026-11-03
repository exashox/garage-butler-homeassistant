"""Problem sensor per vehicle: maintenance overdue."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import GarageButlerConfigEntry
from .entity import GarageButlerEntity, add_vehicle_entities
from .model import TaskStatus

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageButlerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the problem sensor of every vehicle."""
    add_vehicle_entities(
        entry,
        async_add_entities,
        lambda coordinator, vid: [MaintenanceOverdueSensor(coordinator, vid)],
    )


class MaintenanceOverdueSensor(GarageButlerEntity, BinarySensorEntity):
    """On while a maintenance task or inspection is overdue."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "maintenance_overdue"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id, "maintenance_overdue")

    @property
    def is_on(self) -> bool | None:
        if (vehicle := self.vehicle) is None:
            return None
        return vehicle.worst_status(dt_util.now().date()) == TaskStatus.OVERDUE

    @property
    def extra_state_attributes(self) -> dict[str, list[str]] | None:
        if (vehicle := self.vehicle) is None:
            return None
        overdue = vehicle.tasks_with_status(dt_util.now().date(), TaskStatus.OVERDUE)
        return {"tasks": [t.title for t in overdue]}
