"""Plain data of the GarageButler API – no Home Assistant imports, so it is testable alone."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
import json
from typing import Any

API_VERSION = 1
CODE_PREFIX = "gbha1:"

# Same horizon as TaskService.statusOf in the app.
SOON_DAYS = 30
SOON_KM = 1000


class GarageButlerError(Exception):
    """Base error of the GarageButler API."""


class InvalidCode(GarageButlerError):
    """The connection code cannot be read."""


class AuthError(GarageButlerError):
    """Token unknown or revoked, or wrong anon key."""


class CannotConnect(GarageButlerError):
    """The server cannot be reached."""


class ApiError(GarageButlerError):
    """The server rejected a request or answered unexpectedly."""


@dataclass(frozen=True)
class Connection:
    """Where and as whom to call the API."""

    url: str
    key: str
    token: str


def parse_connection_code(code: str) -> Connection:
    """Read the code the app shows: gbha1: + base64url JSON {url, key, token}."""
    code = "".join(code.split())
    if not code.startswith(CODE_PREFIX):
        raise InvalidCode
    payload = code[len(CODE_PREFIX) :]
    try:
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (binascii.Error, ValueError) as err:
        raise InvalidCode from err
    if not isinstance(data, dict):
        raise InvalidCode
    url, key, token = (data.get(k) for k in ("url", "key", "token"))
    if not all(isinstance(v, str) and v for v in (url, key, token)):
        raise InvalidCode
    if not url.startswith("https://"):
        raise InvalidCode
    return Connection(url.rstrip("/"), key, token)


class TaskStatus(StrEnum):
    """Status of an open maintenance task, worst first."""

    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    OK = "ok"


_SEVERITY = {TaskStatus.OVERDUE: 0, TaskStatus.DUE_SOON: 1, TaskStatus.OK: 2}


@dataclass(frozen=True)
class Task:
    """Open maintenance task or statutory inspection."""

    id: str
    title: str
    statutory: bool
    due_date: date | None
    due_mileage: int | None

    def km_left(self, mileage: int | None) -> int | None:
        """Kilometres until due (negative = overdue)."""
        if self.due_mileage is None or mileage is None:
            return None
        return self.due_mileage - mileage

    def status(self, today: date, mileage: int | None) -> TaskStatus:
        """Mirrors TaskService.statusOf in the app."""
        km_left = self.km_left(mileage)
        if (self.due_date is not None and self.due_date < today) or (
            km_left is not None and km_left <= 0
        ):
            return TaskStatus.OVERDUE
        if (self.due_date is not None and (self.due_date - today).days <= SOON_DAYS) or (
            km_left is not None and km_left <= SOON_KM
        ):
            return TaskStatus.DUE_SOON
        return TaskStatus.OK


@dataclass(frozen=True)
class Todo:
    """Known defect or work without a due date."""

    id: str
    title: str
    note: str | None
    important: bool
    is_done: bool
    done_at: datetime | None


@dataclass(frozen=True)
class Vehicle:
    """Vehicle the user is owner or mechanic of."""

    id: str
    nickname: str | None
    make: str | None
    model: str | None
    license_plate: str | None
    current_mileage: int | None
    role: str
    tasks: tuple[Task, ...]
    todos: tuple[Todo, ...]

    @property
    def name(self) -> str:
        """Nickname, else make and model, else the license plate."""
        make_model = " ".join(p for p in (self.make, self.model) if p)
        return self.nickname or make_model or self.license_plate or "Vehicle"

    def worst_status(self, today: date) -> TaskStatus:
        """Most urgent status of all open tasks (ok without any)."""
        return min(
            (t.status(today, self.current_mileage) for t in self.tasks),
            key=_SEVERITY.__getitem__,
            default=TaskStatus.OK,
        )

    def tasks_with_status(self, today: date, status: TaskStatus) -> list[Task]:
        """Open tasks currently in the given status."""
        return [t for t in self.tasks if t.status(today, self.current_mileage) == status]

    def next_dated(self, statutory: bool) -> Task | None:
        """Open task (or inspection) with the earliest due date."""
        dated = [t for t in self.tasks if t.statutory == statutory and t.due_date]
        return min(dated, key=lambda t: t.due_date, default=None)

    def next_by_mileage(self) -> Task | None:
        """Open task with the lowest due mileage."""
        by_km = [t for t in self.tasks if t.due_mileage is not None]
        return min(by_km, key=lambda t: t.due_mileage, default=None)


@dataclass(frozen=True)
class Snapshot:
    """Answer of ha_snapshot()."""

    user_id: str
    user_name: str | None
    vehicles: dict[str, Vehicle]

    @classmethod
    def from_json(cls, data: Any) -> Snapshot:
        """Parse the JSON of ha_snapshot(); ApiError if it does not fit."""
        try:
            if data["api_version"] != API_VERSION:
                raise ApiError(f"Unsupported API version {data['api_version']}")
            vehicles = [_vehicle(v) for v in data["vehicles"]]
            return cls(
                user_id=str(data["user"]["id"]),
                user_name=data["user"].get("name"),
                vehicles={v.id: v for v in vehicles},
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ApiError(f"Unexpected answer: {err!r}") from err


def _vehicle(v: dict[str, Any]) -> Vehicle:
    return Vehicle(
        id=str(v["id"]),
        nickname=v.get("nickname"),
        make=v.get("make"),
        model=v.get("model"),
        license_plate=v.get("license_plate"),
        current_mileage=_int(v.get("current_mileage")),
        role=v.get("role") or "owner",
        tasks=tuple(
            Task(
                id=str(t["id"]),
                title=t.get("title") or "",
                statutory=bool(t.get("statutory")),
                due_date=_date(t.get("due_date")),
                due_mileage=_int(t.get("due_mileage")),
            )
            for t in v.get("tasks") or ()
        ),
        todos=tuple(
            Todo(
                id=str(d["id"]),
                title=d.get("title") or "",
                note=d.get("note"),
                important=bool(d.get("important")),
                is_done=bool(d.get("is_done")),
                done_at=datetime.fromisoformat(d["done_at"]) if d.get("done_at") else None,
            )
            for d in v.get("todos") or ()
        ),
    )


def _int(value: Any) -> int | None:
    return None if value is None else int(value)


def _date(value: Any) -> date | None:
    return date.fromisoformat(value[:10]) if value else None
