"""Calendar per vehicle with the due dates of open tasks and inspections."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import GarageButlerConfigEntry
from .entity import GarageButlerEntity, add_vehicle_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageButlerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar of every vehicle."""
    add_vehicle_entities(
        entry,
        async_add_entities,
        lambda coordinator, vid: [GarageButlerCalendar(coordinator, vid)],
    )


class GarageButlerCalendar(GarageButlerEntity, CalendarEntity):
    """All-day events on the due dates (inspections: last day of the due month)."""

    _attr_translation_key = "due_dates"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id, "due_dates")

    def _events(self) -> list[CalendarEvent]:
        if (vehicle := self.vehicle) is None:
            return []
        events = []
        for task in vehicle.tasks:
            if task.due_date is None:
                continue
            details = []
            if task.due_mileage is not None:
                details.append(f"{task.due_mileage} km")
            events.append(
                CalendarEvent(
                    start=task.due_date,
                    end=task.due_date + timedelta(days=1),
                    summary=f"{task.title} ({vehicle.name})",
                    description=", ".join(details) or None,
                    uid=task.id,
                )
            )
        return sorted(events, key=lambda e: e.start)

    @property
    def event(self) -> CalendarEvent | None:
        """Today's or the next due date."""
        today = dt_util.now().date()
        return next((e for e in self._events() if e.end > today), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [
            e
            for e in self._events()
            if e.start_datetime_local < end_date and e.end_datetime_local > start_date
        ]
