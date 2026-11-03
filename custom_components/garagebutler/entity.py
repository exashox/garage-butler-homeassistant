"""Base entity: one device per vehicle."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GarageButlerConfigEntry, GarageButlerCoordinator
from .model import Vehicle


class GarageButlerEntity(CoordinatorEntity[GarageButlerCoordinator]):
    """Entity of one vehicle."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GarageButlerCoordinator, vehicle_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.vehicle_id = vehicle_id
        self._attr_unique_id = f"{vehicle_id}_{key}"
        vehicle = coordinator.data.vehicles[vehicle_id]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vehicle_id)},
            name=vehicle.name,
            manufacturer=vehicle.make,
            model=vehicle.model,
        )

    @property
    def vehicle(self) -> Vehicle | None:
        """Current data of the vehicle (None once it is gone or inactive)."""
        return self.coordinator.data.vehicles.get(self.vehicle_id)

    @property
    def available(self) -> bool:
        return super().available and self.vehicle is not None


def add_vehicle_entities(
    entry: GarageButlerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    build: Callable[[GarageButlerCoordinator, str], Iterable[Entity]],
) -> None:
    """Add the entities of every vehicle now and of vehicles added later."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = [vid for vid in coordinator.data.vehicles if vid not in known]
        if not new:
            return
        known.update(new)
        async_add_entities([e for vid in new for e in build(coordinator, vid)])

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))
