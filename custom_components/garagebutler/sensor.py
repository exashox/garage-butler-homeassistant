"""Sensors per vehicle: mileage, maintenance status, next due dates, open ToDos."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .coordinator import GarageButlerConfigEntry
from .entity import GarageButlerEntity, add_vehicle_entities
from .model import TaskStatus, Vehicle

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class GarageButlerSensorDescription(SensorEntityDescription):
    """Sensor computed from a vehicle and today's date."""

    value_fn: Callable[[Vehicle, date], StateType | date]
    attrs_fn: Callable[[Vehicle, date], dict[str, Any]] = lambda v, today: {}


def _task_attrs(task, vehicle: Vehicle) -> dict[str, Any]:
    if task is None:
        return {}
    return {
        "title": task.title,
        "due_date": task.due_date,
        "due_mileage": task.due_mileage,
        "km_left": task.km_left(vehicle.current_mileage),
    }


def _status_attrs(vehicle: Vehicle, today: date) -> dict[str, Any]:
    return {
        status.value: [t.title for t in vehicle.tasks_with_status(today, status)]
        for status in (TaskStatus.OVERDUE, TaskStatus.DUE_SOON)
    }


def _due_date(task) -> date | None:
    return task.due_date if task else None


SENSORS: tuple[GarageButlerSensorDescription, ...] = (
    GarageButlerSensorDescription(
        key="mileage",
        translation_key="mileage",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda v, today: v.current_mileage,
    ),
    GarageButlerSensorDescription(
        key="maintenance_status",
        translation_key="maintenance_status",
        device_class=SensorDeviceClass.ENUM,
        options=[s.value for s in TaskStatus],
        value_fn=lambda v, today: v.worst_status(today).value,
        attrs_fn=_status_attrs,
    ),
    GarageButlerSensorDescription(
        key="next_maintenance",
        translation_key="next_maintenance",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v, today: _due_date(v.next_dated(statutory=False)),
        attrs_fn=lambda v, today: _task_attrs(v.next_dated(statutory=False), v),
    ),
    GarageButlerSensorDescription(
        key="next_inspection",
        translation_key="next_inspection",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda v, today: _due_date(v.next_dated(statutory=True)),
        attrs_fn=lambda v, today: _task_attrs(v.next_dated(statutory=True), v),
    ),
    GarageButlerSensorDescription(
        key="distance_to_service",
        translation_key="distance_to_service",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
        value_fn=lambda v, today: (
            t.km_left(v.current_mileage) if (t := v.next_by_mileage()) else None
        ),
        attrs_fn=lambda v, today: _task_attrs(v.next_by_mileage(), v),
    ),
    GarageButlerSensorDescription(
        key="open_todos",
        translation_key="open_todos",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda v, today: sum(1 for d in v.todos if not d.is_done),
        attrs_fn=lambda v, today: {
            "important": [d.title for d in v.todos if d.important and not d.is_done]
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageButlerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of every vehicle."""
    add_vehicle_entities(
        entry,
        async_add_entities,
        lambda coordinator, vid: (
            GarageButlerSensor(coordinator, vid, description) for description in SENSORS
        ),
    )


class GarageButlerSensor(GarageButlerEntity, SensorEntity):
    """Sensor of one vehicle."""

    entity_description: GarageButlerSensorDescription

    def __init__(self, coordinator, vehicle_id: str, description: GarageButlerSensorDescription):
        super().__init__(coordinator, vehicle_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | date:
        if (vehicle := self.vehicle) is None:
            return None
        return self.entity_description.value_fn(vehicle, dt_util.now().date())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if (vehicle := self.vehicle) is None:
            return None
        return self.entity_description.attrs_fn(vehicle, dt_util.now().date())
