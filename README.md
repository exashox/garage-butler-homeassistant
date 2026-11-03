# GarageButler for Home Assistant

Custom integration that brings [GarageButler](https://git.exalabs.de/nero/garage-butler)
vehicles, due dates and ToDos into Home Assistant – and sends the mileage back.

> **Status: 0.1.0, prepared ahead of the backend.** The integration talks to the
> Supabase backend of GarageButler, which does not exist yet (the app still runs
> on Firebase). The server side is drafted in [`supabase/ha_api.sql`](supabase/ha_api.sql),
> the contract in [`docs/api.md`](docs/api.md).

## What you get

One device per vehicle (owner or mechanic, inactive vehicles left out):

| Entity | Content |
|---|---|
| `sensor.<vehicle>_mileage` | Current mileage (km) |
| `sensor.<vehicle>_maintenance_status` | `overdue` / `due_soon` / `ok` – worst open task, same rules as the app (30 days / 1000 km) |
| `sensor.<vehicle>_next_maintenance` | Date of the next maintenance task |
| `sensor.<vehicle>_next_inspection` | Date of the next statutory inspection (HU/TÜV, §57a, MFK, APK) |
| `sensor.<vehicle>_distance_to_service` | Kilometres to the next mileage-based task |
| `sensor.<vehicle>_open_todos` | Number of open ToDos |
| `binary_sensor.<vehicle>_maintenance_overdue` | Problem sensor, on while something is overdue |
| `todo.<vehicle>_todos` | The vehicle's ToDos: add, edit, tick off, reopen, delete |
| `calendar.<vehicle>_due_dates` | All-day events on the due dates |

Service `garagebutler.update_mileage` (vehicle device + km) raises the mileage;
lower values are ignored like in the app.

Blueprint [`mileage_from_car`](blueprints/automation/garagebutler/mileage_from_car.yaml)
takes the odometer of any car integration and sends it to GarageButler after the
car stood still for a while (converts miles).

Completing maintenance tasks stays in the app (recurrence, costs, additional fields).

## Installation

**Manual:** copy `custom_components/garagebutler` into the `custom_components`
folder of your Home Assistant config and restart.

**HACS:** HACS only accepts GitHub repositories. Mirror this repository to
GitHub, then add it in HACS → Custom repositories (type *Integration*).

Requires Home Assistant 2025.3 or later. Works with every installation type
(OS, Supervised, Container, Core) – it is an integration, not an add-on.

## Setup

1. GarageButler app → Settings → Home Assistant → create a connection, copy the code.
2. Home Assistant → Settings → Devices & services → Add integration → GarageButler → paste the code.

The code (`gbha1:…`) contains the server URL, the public anon key and a personal
token. Revoking the token in the app makes Home Assistant ask for a new code.

## Development

```sh
python -m unittest discover tests   # data layer, no Home Assistant needed
```

Layout:

- `custom_components/garagebutler/model.py` – snapshot parsing, status rules, connection code (no HA imports)
- `api.py` – HTTP client for the `ha_*` RPCs
- `coordinator.py` – polls the snapshot every 15 minutes
- `sensor.py`, `binary_sensor.py`, `todo.py`, `calendar.py` – platforms
- `services.py` – `update_mileage`

## Still open

- Supabase schema of GarageButler; then move `supabase/ha_api.sql` there as a migration and adjust table/column names.
- App: "Home Assistant" screen (create/list/revoke tokens, show connection code).
- Test against a real Home Assistant (config flow, entities, reauth).
