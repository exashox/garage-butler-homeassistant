# GarageButler Home Assistant API (v1)

Contract between the Home Assistant integration and the GarageButler backend
(self-hosted Supabase). The server side is a handful of PostgREST RPCs; the SQL
draft is in [`supabase/ha_api.sql`](../supabase/ha_api.sql) and moves into the
GarageButler repo (`supabase/migrations/`) once its Supabase schema exists.

## Authentication

Users sign in to GarageButler with Google, which a headless Home Assistant
cannot do. Instead each user creates **API tokens** in the app:

1. App: "Connect Home Assistant" calls `create_api_token(name)` (signed in) and
   gets the plain token once – only its SHA-256 hash is stored.
2. App shows a **connection code** to copy:
   `gbha1:` + base64url (no padding) of
   `{"url": "https://garagebutler-api.exalabs.de", "key": "<anon key>", "token": "gbt_…"}`
3. Home Assistant: the config flow asks only for that code.
4. App lists the user's tokens (`select` on `api_tokens`, RLS: own rows) and
   revokes them with `revoke_api_token(id)`. A revoked token makes Home Assistant
   ask for a new code (reauth).

Every call of the integration:

```
POST {url}/rest/v1/rpc/<function>
apikey: <anon key>
Authorization: Bearer <anon key>
X-GarageButler-Token: gbt_…
Content-Type: application/json
```

The `ha_*` functions run as `security definer`, resolve the user from the token
and only touch vehicles the user is assigned to (owner or mechanic). Inactive
vehicles are left out.

## Errors

| HTTP | SQLSTATE | Meaning | Integration |
|---|---|---|---|
| 403 | `28000` | token missing, unknown or revoked | reauth |
| 401 | – | wrong anon key (Kong) | reauth |
| 404 | `P0002` | vehicle/ToDo not found or not accessible | error message |
| 400 | `22023` | invalid parameter (empty title, mileage out of range) | error message |

## Functions

### `ha_snapshot()` → JSON

Everything the integration shows, polled every 15 minutes.

```json
{
  "api_version": 1,
  "user": {"id": "uuid", "name": "nero"},
  "vehicles": [
    {
      "id": "uuid",
      "nickname": "Bulli",
      "make": "Volkswagen",
      "model": "T6",
      "license_plate": "OS-GB 123",
      "current_mileage": 123456,
      "role": "owner",
      "tasks": [
        {"id": "uuid", "title": "Ölwechsel", "statutory": false,
         "due_date": "2026-12-01", "due_mileage": 125000}
      ],
      "todos": [
        {"id": "uuid", "title": "Bremsscheiben vorne riefig", "note": null,
         "important": true, "is_done": false, "done_at": null}
      ]
    }
  ]
}
```

- `tasks`: open maintenance tasks only (incl. statutory inspections, whose
  `due_date` is the last day of the due month).
- `todos`: open ToDos plus those done within the last 30 days.
- Status (overdue / due soon / ok) is computed by the integration with the
  app's rules (`TaskService.statusOf`: due date passed or mileage reached =
  overdue; within 30 days or 1000 km = due soon).
- `api_version` changes only for breaking changes; the integration refuses
  versions it does not know.

### `ha_set_mileage(p_vehicle_id uuid, p_mileage int)` → JSON

Raises `current_mileage`; a lower value is ignored (same as the app: fill-ups
and completed tasks only ever raise it). Returns `{"current_mileage": n}`.

### `ha_todo_create(p_vehicle_id uuid, p_title text, p_note text)` → uuid

### `ha_todo_update(p_todo_id uuid, p_title text, p_note text, p_is_done bool)` → void

`p_title` null/empty keeps the title; `p_note` null clears the note; `done_at`
is set when a ToDo is ticked off and cleared when it is reopened. `important`
is not changed.

### `ha_todo_delete(p_todo_id uuid)` → void

## Not in v1

Completing maintenance tasks (recurrence, follow-up task, cost booking, service
log) stays in the app – it needs the dialog with additional fields.
