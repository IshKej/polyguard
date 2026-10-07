-- PolyGuard's shared state.
--
-- The web API runs as serverless functions: many short-lived copies, none of which
-- can see the others' memory. Anything that must hold across all of them lives here:
-- the spend and abuse guard, saved scans behind share links, and the anonymous
-- answers to the spot the attack game.
--
-- Only the API server touches these tables, with the project's secret key, which
-- acts as the service_role. Row level security is on and there are no policies,
-- and the anon and authenticated roles get no grants, so the public Data API
-- exposes nothing here even to someone holding the publishable key.

-- --------------------------------------------------------------------------
-- Saved scans: a share link is an unguessable id, nothing else
-- --------------------------------------------------------------------------
create table public.scans (
  -- 128 random bits, base64url: the link is the only way in, so it must not be guessable.
  id text primary key check (id ~ '^[A-Za-z0-9_-]{22}$'),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default now() + interval '30 days',
  mode text not null check (mode in ('simulated', 'live')),
  -- True when the bot's replies were left out before saving (the default),
  -- because a reply to an extraction attack can contain the bot's own prompt.
  redacted boolean not null default true,
  -- Only the hash is kept. The token itself goes to the person who saved the scan.
  delete_token_sha256 text not null check (delete_token_sha256 ~ '^[0-9a-f]{64}$'),
  size_bytes integer not null check (size_bytes between 1 and 2000000),
  result jsonb not null
);
create index scans_expires_at_idx on public.scans (expires_at);

alter table public.scans enable row level security;
revoke all on table public.scans from anon, authenticated;
grant select, insert, delete on table public.scans to service_role;

-- --------------------------------------------------------------------------
-- The spot the attack game: one row per answer, nothing about who answered
-- --------------------------------------------------------------------------
create table public.game_answers (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  item_id text not null check (length(item_id) <= 80),
  lang text not null check (lang ~ '^[a-z]{2,3}$'),
  is_attack boolean not null,
  answered_attack boolean not null,
  correct boolean generated always as (is_attack = answered_attack) stored
);
create index game_answers_lang_idx on public.game_answers (lang);

alter table public.game_answers enable row level security;
revoke all on table public.game_answers from anon, authenticated;
grant select, insert on table public.game_answers to service_role;

-- How well people tell an attack from an ordinary request, per language.
create function public.game_stats()
returns table (lang text, answers bigint, correct bigint, attacks_seen bigint, attacks_caught bigint)
language sql
stable
security invoker
set search_path = ''
as $$
  select a.lang,
         count(*),
         count(*) filter (where a.correct),
         count(*) filter (where a.is_attack),
         count(*) filter (where a.is_attack and a.answered_attack)
  from public.game_answers a
  group by a.lang
$$;

-- --------------------------------------------------------------------------
-- The guard: counters every serverless copy shares
--
-- One table of named counters that expire. The API uses it for a daily budget of
-- paid model calls, a per-visitor hourly limit (keyed by a salted hash of the IP,
-- never the IP), the number of live scans running at once, and idempotency keys
-- so a double click cannot start, and pay for, the same scan twice.
-- --------------------------------------------------------------------------
create table public.guard_counters (
  key text primary key check (length(key) <= 200),
  value bigint not null default 0,
  expires_at timestamptz not null
);
create index guard_counters_expires_at_idx on public.guard_counters (expires_at);

alter table public.guard_counters enable row level security;
revoke all on table public.guard_counters from anon, authenticated;
grant select, insert, update, delete on table public.guard_counters to service_role;

-- Add p_amount to a counter, but only if the total stays at or under p_max.
-- Atomic: the upsert takes the row lock, so two functions racing for the last
-- unit of budget cannot both get it. An expired counter starts again from zero.
create function public.guard_take(p_key text, p_amount bigint, p_max bigint, p_ttl_seconds integer)
returns table (allowed boolean, value bigint)
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v bigint;
begin
  insert into public.guard_counters as c (key, value, expires_at)
  values (p_key, 0, now() + make_interval(secs => p_ttl_seconds))
  on conflict (key) do update
    set value = case when c.expires_at < now() then 0 else c.value end,
        expires_at = case when c.expires_at < now()
                          then now() + make_interval(secs => p_ttl_seconds)
                          else c.expires_at end;

  update public.guard_counters c
     set value = c.value + p_amount
   where c.key = p_key and c.value + p_amount <= p_max
  returning c.value into v;

  if v is null then
    return query select false, (select c.value from public.guard_counters c where c.key = p_key);
  else
    return query select true, v;
  end if;
end;
$$;

-- Give units back, as when a live scan ends and frees its slot. Never below zero.
create function public.guard_give(p_key text, p_amount bigint)
returns void
language sql
security invoker
set search_path = ''
as $$
  update public.guard_counters c
     set value = greatest(c.value - p_amount, 0)
   where c.key = p_key
$$;

-- Claim a key once. True the first time; false while an earlier claim is unexpired.
create function public.guard_claim(p_key text, p_ttl_seconds integer)
returns boolean
language plpgsql
security invoker
set search_path = ''
as $$
declare
  claimed boolean;
begin
  insert into public.guard_counters as c (key, value, expires_at)
  values (p_key, 1, now() + make_interval(secs => p_ttl_seconds))
  on conflict (key) do update
    set value = 1, expires_at = excluded.expires_at
    where c.expires_at < now()
  returning true into claimed;
  return coalesce(claimed, false);
end;
$$;

-- Delete what has expired: saved scans past their date, counters long past theirs.
-- Called by the API now and then while it writes, so no scheduler is needed.
create function public.sweep_expired()
returns void
language sql
security invoker
set search_path = ''
as $$
  delete from public.scans where expires_at < now();
  delete from public.guard_counters where expires_at < now() - interval '1 day';
$$;

-- Functions are executable by PUBLIC by default. These are for the server only.
revoke execute on function public.game_stats() from public, anon, authenticated;
revoke execute on function public.guard_take(text, bigint, bigint, integer) from public, anon, authenticated;
revoke execute on function public.guard_give(text, bigint) from public, anon, authenticated;
revoke execute on function public.guard_claim(text, integer) from public, anon, authenticated;
revoke execute on function public.sweep_expired() from public, anon, authenticated;
grant execute on function public.game_stats() to service_role;
grant execute on function public.guard_take(text, bigint, bigint, integer) to service_role;
grant execute on function public.guard_give(text, bigint) to service_role;
grant execute on function public.guard_claim(text, integer) to service_role;
grant execute on function public.sweep_expired() to service_role;
