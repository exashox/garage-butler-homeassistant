-- GarageButler Home Assistant API v1 (see docs/api.md).
--
-- DRAFT: GarageButler has no Supabase schema yet. This assumes the Firestore
-- collections become tables of the same name with uuid ids and
--   vehicles.assigned_user_ids / assigned_mechanic_ids  uuid[]
--   vehicles.inactive bool, maintenance_tasks.statutory bool
--   due_date / done_at as date / timestamptz, catalogs with a `name` column.
-- Adjust to the real schema and move into the GarageButler repo as
-- supabase/migrations/<timestamp>_ha_api.sql.

create schema if not exists private;

-- ── API tokens ───────────────────────────────────────────────────────────────

create table public.api_tokens (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid not null references auth.users (id) on delete cascade,
  name         text not null,
  token_hash   bytea not null unique,
  created_at   timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at   timestamptz
);

alter table public.api_tokens enable row level security;

-- The app lists its own tokens; writes go through the functions below only.
create policy api_tokens_select_own on public.api_tokens
  for select to authenticated using (user_id = auth.uid());

revoke all on public.api_tokens from anon;
grant select on public.api_tokens to authenticated;

-- Returns the plain token once; only its hash is stored.
create function public.create_api_token(p_name text)
returns text
language plpgsql security definer
set search_path = public, extensions
as $$
declare
  v_token text;
begin
  if auth.uid() is null then
    raise exception 'not signed in' using errcode = '28000';
  end if;
  v_token := 'gbt_' || translate(encode(gen_random_bytes(32), 'base64'), '+/=', '-_');
  insert into api_tokens (user_id, name, token_hash)
  values (auth.uid(), coalesce(nullif(trim(p_name), ''), 'Home Assistant'), digest(v_token, 'sha256'));
  return v_token;
end $$;

create function public.revoke_api_token(p_id uuid)
returns void
language sql security definer
set search_path = public
as $$
  update api_tokens set revoked_at = now()
  where id = p_id and user_id = auth.uid() and revoked_at is null;
$$;

-- ── Helpers (schema `private` is not exposed by PostgREST) ──────────────────

-- User of the X-GarageButler-Token header; raises 28000 (HTTP 403) otherwise.
create function private.ha_token_user()
returns uuid
language plpgsql security definer
set search_path = public, extensions
as $$
declare
  v_token text := current_setting('request.headers', true)::json ->> 'x-garagebutler-token';
  v_user  uuid;
begin
  if v_token is null or v_token = '' then
    raise exception 'missing token' using errcode = '28000';
  end if;
  update api_tokens set last_used_at = now()
  where token_hash = digest(v_token, 'sha256') and revoked_at is null
  returning user_id into v_user;
  if v_user is null then
    raise exception 'invalid token' using errcode = '28000';
  end if;
  return v_user;
end $$;

-- Raises P0002 (HTTP 404) unless the user is owner or mechanic of an active vehicle.
create function private.ha_check_vehicle(p_user uuid, p_vehicle_id uuid)
returns void
language plpgsql security definer
set search_path = public
as $$
begin
  if not exists (
    select 1 from vehicles v
    where v.id = p_vehicle_id and not v.inactive
      and (p_user = any (v.assigned_user_ids) or p_user = any (v.assigned_mechanic_ids))
  ) then
    raise exception 'vehicle not found' using errcode = 'P0002';
  end if;
end $$;

-- Vehicle of a ToDo the user may change.
create function private.ha_todo_vehicle(p_user uuid, p_todo_id uuid)
returns uuid
language plpgsql security definer
set search_path = public
as $$
declare
  v_vehicle uuid;
begin
  select vehicle_id into v_vehicle from vehicle_todos where id = p_todo_id;
  if v_vehicle is null then
    raise exception 'todo not found' using errcode = 'P0002';
  end if;
  perform private.ha_check_vehicle(p_user, v_vehicle);
  return v_vehicle;
end $$;

revoke all on all functions in schema private from public, anon, authenticated;

-- ── API ─────────────────────────────────────────────────────────────────────

create function public.ha_snapshot()
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_user uuid := private.ha_token_user();
begin
  return json_build_object(
    'api_version', 1,
    'user', json_build_object(
      'id', v_user,
      'name', (select p.username from public_profiles p where p.id = v_user)),
    'vehicles', coalesce((
      select json_agg(json_build_object(
        'id', v.id,
        'nickname', v.nickname,
        'make', mk.name,
        'model', md.name,
        'license_plate', v.license_plate,
        'current_mileage', v.current_mileage,
        'role', case when v_user = any (v.assigned_user_ids) then 'owner' else 'mechanic' end,
        'tasks', coalesce((
          select json_agg(json_build_object(
            'id', t.id,
            'title', t.title,
            'statutory', t.statutory,
            'due_date', t.due_date,
            'due_mileage', t.due_mileage
          ) order by t.due_date nulls last, t.due_mileage nulls last)
          from maintenance_tasks t
          where t.vehicle_id = v.id and not t.is_completed), '[]'::json),
        'todos', coalesce((
          select json_agg(json_build_object(
            'id', d.id,
            'title', d.title,
            'note', d.note,
            'important', d.important,
            'is_done', d.is_done,
            'done_at', d.done_at
          ) order by d.is_done, d.important desc, d.created_at)
          from vehicle_todos d
          where d.vehicle_id = v.id
            and (not d.is_done or d.done_at > now() - interval '30 days')), '[]'::json)
      ) order by v.created_at)
      from vehicles v
      left join vehicle_makes mk on mk.id = v.make_id
      left join vehicle_models md on md.id = v.model_id
      where not v.inactive
        and (v_user = any (v.assigned_user_ids) or v_user = any (v.assigned_mechanic_ids))
    ), '[]'::json));
end $$;

-- Only ever raises the mileage, like fill-ups and completed tasks in the app.
create function public.ha_set_mileage(p_vehicle_id uuid, p_mileage int)
returns json
language plpgsql security definer
set search_path = public
as $$
declare
  v_user    uuid := private.ha_token_user();
  v_mileage int;
begin
  perform private.ha_check_vehicle(v_user, p_vehicle_id);
  if p_mileage is null or p_mileage < 0 or p_mileage > 9999999 then
    raise exception 'mileage out of range' using errcode = '22023';
  end if;
  update vehicles
  set current_mileage = greatest(coalesce(current_mileage, 0), p_mileage)
  where id = p_vehicle_id
  returning current_mileage into v_mileage;
  return json_build_object('current_mileage', v_mileage);
end $$;

create function public.ha_todo_create(p_vehicle_id uuid, p_title text, p_note text default null)
returns uuid
language plpgsql security definer
set search_path = public
as $$
declare
  v_user uuid := private.ha_token_user();
  v_id   uuid;
begin
  perform private.ha_check_vehicle(v_user, p_vehicle_id);
  if nullif(trim(p_title), '') is null or length(p_title) > 200 then
    raise exception 'invalid title' using errcode = '22023';
  end if;
  insert into vehicle_todos (vehicle_id, title, note, important, is_done)
  values (p_vehicle_id, trim(p_title), nullif(trim(p_note), ''), false, false)
  returning id into v_id;
  return v_id;
end $$;

create function public.ha_todo_update(p_todo_id uuid, p_title text, p_note text, p_is_done boolean)
returns void
language plpgsql security definer
set search_path = public
as $$
declare
  v_user uuid := private.ha_token_user();
begin
  perform private.ha_todo_vehicle(v_user, p_todo_id);
  if length(p_title) > 200 then
    raise exception 'invalid title' using errcode = '22023';
  end if;
  update vehicle_todos
  set title   = coalesce(nullif(trim(p_title), ''), title),
      note    = nullif(trim(p_note), ''),
      is_done = coalesce(p_is_done, is_done),
      done_at = case
                  when coalesce(p_is_done, is_done) and not is_done then now()
                  when not coalesce(p_is_done, is_done) then null
                  else done_at
                end
  where id = p_todo_id;
end $$;

create function public.ha_todo_delete(p_todo_id uuid)
returns void
language plpgsql security definer
set search_path = public
as $$
declare
  v_user uuid := private.ha_token_user();
begin
  perform private.ha_todo_vehicle(v_user, p_todo_id);
  delete from vehicle_todos where id = p_todo_id;
end $$;

-- Functions are executable by PUBLIC by default: open the ha_* ones to anon
-- (Home Assistant only has the anon key; the token does the authorisation),
-- token management to signed-in users only.
revoke all on function
  public.create_api_token(text), public.revoke_api_token(uuid),
  public.ha_snapshot(), public.ha_set_mileage(uuid, int),
  public.ha_todo_create(uuid, text, text), public.ha_todo_update(uuid, text, text, boolean),
  public.ha_todo_delete(uuid)
from public;

grant execute on function public.create_api_token(text), public.revoke_api_token(uuid)
  to authenticated;

grant execute on function
  public.ha_snapshot(), public.ha_set_mileage(uuid, int),
  public.ha_todo_create(uuid, text, text), public.ha_todo_update(uuid, text, text, boolean),
  public.ha_todo_delete(uuid)
to anon, authenticated;
