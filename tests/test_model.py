"""Tests of the plain data layer (no Home Assistant needed): python -m unittest discover tests"""

import base64
from datetime import date
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "custom_components" / "garagebutler"))

from model import (  # noqa: E402
    ApiError,
    InvalidCode,
    Snapshot,
    Task,
    TaskStatus,
    parse_connection_code,
)

TODAY = date(2026, 11, 3)


def code(payload, prefix="gbha1:") -> str:
    raw = json.dumps(payload).encode()
    return prefix + base64.urlsafe_b64encode(raw).decode().rstrip("=")


def task(due_date=None, due_mileage=None, statutory=False, title="Oil change") -> Task:
    return Task("t1", title, statutory, due_date, due_mileage)


class ConnectionCodeTest(unittest.TestCase):
    def test_valid(self):
        conn = parse_connection_code(
            code({"url": "https://gb.example/", "key": "anon", "token": "gbt_x"})
        )
        self.assertEqual(conn.url, "https://gb.example")
        self.assertEqual(conn.key, "anon")
        self.assertEqual(conn.token, "gbt_x")

    def test_whitespace_from_copy_paste_is_ignored(self):
        c = code({"url": "https://gb.example", "key": "k", "token": "t"})
        self.assertEqual(parse_connection_code(f"  {c[:10]}\n{c[10:]} ").token, "t")

    def test_invalid(self):
        for bad in (
            "",
            "gbha1:%%%",
            code({"url": "https://gb.example", "key": "k", "token": "t"}, prefix="xx:"),
            code(["not", "a", "dict"]),
            code({"url": "https://gb.example", "key": "k"}),
            code({"url": "http://gb.example", "key": "k", "token": "t"}),
        ):
            with self.subTest(bad=bad), self.assertRaises(InvalidCode):
                parse_connection_code(bad)


class TaskStatusTest(unittest.TestCase):
    """Same cases as TaskService.statusOf in the app."""

    def test_by_date(self):
        self.assertEqual(task(date(2026, 11, 2)).status(TODAY, None), TaskStatus.OVERDUE)
        self.assertEqual(task(TODAY).status(TODAY, None), TaskStatus.DUE_SOON)
        self.assertEqual(task(date(2026, 12, 3)).status(TODAY, None), TaskStatus.DUE_SOON)
        self.assertEqual(task(date(2026, 12, 4)).status(TODAY, None), TaskStatus.OK)

    def test_by_mileage(self):
        self.assertEqual(task(due_mileage=100_000).status(TODAY, 100_000), TaskStatus.OVERDUE)
        self.assertEqual(task(due_mileage=100_000).status(TODAY, 99_000), TaskStatus.DUE_SOON)
        self.assertEqual(task(due_mileage=100_000).status(TODAY, 98_999), TaskStatus.OK)
        self.assertEqual(task(due_mileage=100_000).status(TODAY, None), TaskStatus.OK)

    def test_first_reached_wins(self):
        t = task(date(2027, 6, 1), due_mileage=100_000)
        self.assertEqual(t.status(TODAY, 100_500), TaskStatus.OVERDUE)


SNAPSHOT = {
    "api_version": 1,
    "user": {"id": "u1", "name": "nero"},
    "vehicles": [
        {
            "id": "v1",
            "nickname": None,
            "make": "Volkswagen",
            "model": "T6",
            "license_plate": "OS-GB 123",
            "current_mileage": 99_500,
            "role": "owner",
            "tasks": [
                {"id": "a", "title": "Oil change", "statutory": False,
                 "due_date": "2027-03-01", "due_mileage": 100_000},
                {"id": "b", "title": "Brake fluid", "statutory": False,
                 "due_date": "2027-01-15", "due_mileage": None},
                {"id": "c", "title": "HU", "statutory": True,
                 "due_date": "2026-10-31", "due_mileage": None},
            ],
            "todos": [
                {"id": "d1", "title": "Brake discs scored", "note": None,
                 "important": True, "is_done": False, "done_at": None},
                {"id": "d2", "title": "Wiper", "note": "front left",
                 "important": False, "is_done": True,
                 "done_at": "2026-10-20T08:00:00.123+00:00"},
            ],
        }
    ],
}


class SnapshotTest(unittest.TestCase):
    def test_parse(self):
        snap = Snapshot.from_json(SNAPSHOT)
        self.assertEqual(snap.user_id, "u1")
        vehicle = snap.vehicles["v1"]
        self.assertEqual(vehicle.name, "Volkswagen T6")
        self.assertEqual(vehicle.next_dated(statutory=False).id, "b")
        self.assertEqual(vehicle.next_dated(statutory=True).id, "c")
        self.assertEqual(vehicle.next_by_mileage().km_left(vehicle.current_mileage), 500)
        self.assertEqual(vehicle.worst_status(TODAY), TaskStatus.OVERDUE)
        self.assertEqual([t.id for t in vehicle.tasks_with_status(TODAY, TaskStatus.DUE_SOON)], ["a"])
        self.assertEqual(vehicle.todos[1].done_at.year, 2026)

    def test_without_tasks_is_ok(self):
        data = json.loads(json.dumps(SNAPSHOT))
        data["vehicles"][0]["tasks"] = []
        vehicle = Snapshot.from_json(data).vehicles["v1"]
        self.assertEqual(vehicle.worst_status(TODAY), TaskStatus.OK)
        self.assertIsNone(vehicle.next_by_mileage())

    def test_rejects_unknown_version_and_garbage(self):
        for bad in ({**SNAPSHOT, "api_version": 2}, {"vehicles": []}, [], None):
            with self.subTest(bad=bad), self.assertRaises(ApiError):
                Snapshot.from_json(bad)


if __name__ == "__main__":
    unittest.main()
