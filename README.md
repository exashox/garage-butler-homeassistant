<p align="center"><img src="brand/logo.svg" alt="GarageButler" width="420"></p>

# GarageButler for Home Assistant

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=exashox&repository=garage-butler-homeassistant&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=garagebutler)
[![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fexashox%2Fgarage-butler-homeassistant%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fgaragebutler%2Fmileage_from_car.yaml)

Custom integration that brings GarageButler
vehicles, due dates and ToDos into Home Assistant – and sends the mileage back.

> **Status: prepared ahead of the backend** (version in [`VERSION`](VERSION), changes in [`CHANGELOG.md`](CHANGELOG.md)). The integration talks to the
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

**HACS (recommended, gets updates):** click **Open in HACS** above – or HACS → ⋮ →
Custom repositories → `https://github.com/exashox/garage-butler-homeassistant`, type
*Integration* – then **Download** and **restart Home Assistant**. New releases show up
as updates in Home Assistant.

**Manual:** copy the folder `custom_components/garagebutler` so that you end up with
`/config/custom_components/garagebutler/manifest.json`, then restart Home Assistant.
Updates: copy again.

Requires Home Assistant 2025.3 or later (brand images: 2026.3). Works with every
installation type (OS, Supervised, Container, Core) – it is an integration, not an add-on.

## Setup

1. GarageButler app → Settings → Home Assistant → create a connection, copy the code.
2. Click **Add integration** above (or Settings → Devices & services → Add integration →
   GarageButler) and paste the code.

The buttons use [My Home Assistant](https://my.home-assistant.io/): on first use it asks
for the address of your Home Assistant. *Add integration* only works after installing and
restarting – before that Home Assistant answers "This integration does not support
configuration via the UI".

The code (`gbha1:…`) contains the server URL, the public anon key and a personal
token. Revoking the token in the app makes Home Assistant ask for a new code.

## Development

```sh
python -m unittest discover tests   # data layer and versions, no Home Assistant needed
python tool/render_brand.py         # brand/*.svg → custom_components/garagebutler/brand/*.png
```

Brand images: the SVG sources in `brand/` derive from the app's butler mark
(`garage-butler/assets/logos/garagebutler-mark.svg`) with a smart-home badge. Home Assistant
2026.3+ shows the PNGs from `custom_components/garagebutler/brand/`. `brand/favicon.png` (32×32,
dark rounded square like the app favicon) is for web pages, repo avatars and the like.

### Branches and releases

- Source of truth is `nero/garage-butler-homeassistant` on git.exalabs.de; Gitea push-mirrors
  every push to the public [GitHub repository](https://github.com/exashox/garage-butler-homeassistant),
  which HACS and the buttons use. Issues are on GitHub.
- Work happens on `develop`; `main` only carries released versions, each tagged `vX.Y.Z`.
- Note every change in `CHANGELOG.md` under *Unveröffentlicht* (German, like the other Exolva projects).
- Release: `tool/release.sh X.Y.Z` on a clean, pushed `develop` – sets `VERSION` and
  `manifest.json`, dates the changelog, fast-forwards `main`, tags and pushes; then creates
  the GitHub release from the changelog section (with the `gh` CLI, otherwise it prints the
  link to create it by hand). HACS offers each GitHub release as an update.

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
