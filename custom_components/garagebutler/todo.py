"""ToDo list per vehicle, backed by the GarageButler ToDos."""

from __future__ import annotations

from collections.abc import Awaitable

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import GarageButlerConfigEntry
from .entity import GarageButlerEntity, add_vehicle_entities
from .model import GarageButlerError

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GarageButlerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the ToDo list of every vehicle."""
    add_vehicle_entities(
        entry,
        async_add_entities,
        lambda coordinator, vid: [GarageButlerTodoList(coordinator, vid)],
    )


class GarageButlerTodoList(GarageButlerEntity, TodoListEntity):
    """Known defects and work without a due date ("front brake discs scored")."""

    _attr_translation_key = "todos"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, coordinator, vehicle_id: str) -> None:
        super().__init__(coordinator, vehicle_id, "todos")

    @property
    def todo_items(self) -> list[TodoItem] | None:
        if (vehicle := self.vehicle) is None:
            return None
        return [
            TodoItem(
                uid=d.id,
                summary=d.title,
                description=d.note,
                status=TodoItemStatus.COMPLETED if d.is_done else TodoItemStatus.NEEDS_ACTION,
            )
            for d in vehicle.todos
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self._call(
            self.coordinator.client.create_todo(self.vehicle_id, item.summary or "", item.description)
        )

    async def async_update_todo_item(self, item: TodoItem) -> None:
        await self._call(
            self.coordinator.client.update_todo(
                item.uid,
                item.summary,
                item.description,
                item.status == TodoItemStatus.COMPLETED,
            )
        )

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            await self._call(self.coordinator.client.delete_todo(uid), refresh=False)
        await self.coordinator.async_request_refresh()

    async def _call(self, request: Awaitable, refresh: bool = True) -> None:
        try:
            await request
        except GarageButlerError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"error": str(err)},
            ) from err
        if refresh:
            await self.coordinator.async_request_refresh()
