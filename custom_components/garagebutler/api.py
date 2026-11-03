"""HTTP client for the GarageButler API (PostgREST RPCs of the Supabase backend)."""

from __future__ import annotations

from typing import Any

import aiohttp

from .model import ApiError, AuthError, CannotConnect, Connection

TOKEN_HEADER = "X-GarageButler-Token"
TIMEOUT = aiohttp.ClientTimeout(total=20)


class GarageButlerClient:
    """Calls the ha_* functions described in docs/api.md."""

    def __init__(self, session: aiohttp.ClientSession, connection: Connection) -> None:
        self._session = session
        self._conn = connection

    async def snapshot(self) -> Any:
        """Vehicles, open tasks and ToDos of the user."""
        return await self._rpc("ha_snapshot")

    async def set_mileage(self, vehicle_id: str, mileage: int) -> Any:
        """Raise the mileage of a vehicle (lower values are ignored)."""
        return await self._rpc("ha_set_mileage", p_vehicle_id=vehicle_id, p_mileage=mileage)

    async def create_todo(self, vehicle_id: str, title: str, note: str | None) -> Any:
        """Add a ToDo; returns its id."""
        return await self._rpc("ha_todo_create", p_vehicle_id=vehicle_id, p_title=title, p_note=note)

    async def update_todo(
        self, todo_id: str, title: str | None, note: str | None, is_done: bool
    ) -> None:
        """Change title and note, tick off or reopen a ToDo."""
        await self._rpc(
            "ha_todo_update", p_todo_id=todo_id, p_title=title, p_note=note, p_is_done=is_done
        )

    async def delete_todo(self, todo_id: str) -> None:
        """Delete a ToDo."""
        await self._rpc("ha_todo_delete", p_todo_id=todo_id)

    async def _rpc(self, name: str, **params: Any) -> Any:
        headers = {
            "apikey": self._conn.key,
            "Authorization": f"Bearer {self._conn.key}",
            TOKEN_HEADER: self._conn.token,
        }
        try:
            async with self._session.post(
                f"{self._conn.url}/rest/v1/rpc/{name}",
                json=params,
                headers=headers,
                timeout=TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise AuthError(f"{name}: HTTP {resp.status}")
                if resp.status >= 400:
                    body = (await resp.text())[:300]
                    raise ApiError(f"{name}: HTTP {resp.status} {body}")
                if resp.status == 204:
                    return None
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect(f"{name}: {err}") from err
