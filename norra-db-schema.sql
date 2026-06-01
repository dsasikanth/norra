-- ============================================================
-- Norra — database schema (Postgres: works on Supabase or AWS RDS)
-- Phase 1 MVP. Run this in Supabase SQL editor or psql.
-- ============================================================

-- One row per customer (clinic / shop / restaurant)
create table if not exists clients (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,                       -- internal label, e.g. "Bronte Creek Physio"
  retell_agent_id text,                                -- Retell agent_id (for pulling calls)
  retell_llm_id   text,                                -- Retell LLM id (the response engine we PATCH)
  timezone        text default 'America/Toronto',
  status          text default 'active',               -- active | paused
  created_at      timestamptz default now()
);

-- The editable knowledge for each customer (1:1 with clients)
create table if not exists client_knowledge (
  client_id       uuid primary key references clients(id) on delete cascade,
  business_name   text,
  business_type   text,                                -- "physiotherapy, massage & chiropractic clinic"
  address         text,
  service_area    text,
  hours           text,
  languages       text,                                -- "English, Hindi, Punjabi, Mandarin"
  services        jsonb default '[]'::jsonb,           -- [{name,duration,price,provider}]
  faqs            jsonb default '[]'::jsonb,           -- [{q,a}]
  policies        text,
  transfer_number text,
  updated_at      timestamptz default now()
);

-- Optional local cache of calls (you can also read live from Retell via the Worker)
create table if not exists calls (
  id           text primary key,                       -- Retell call_id
  client_id    uuid references clients(id) on delete cascade,
  caller       text,
  language     text,
  call_type    text,                                   -- book | lead | order | urgent
  duration_sec int,
  summary      text,
  fields       jsonb default '{}'::jsonb,
  started_at   timestamptz,
  created_at   timestamptz default now()
);
create index if not exists idx_calls_client on calls(client_id, started_at desc);

-- keep updated_at fresh on knowledge edits
create or replace function touch_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists trg_touch_knowledge on client_knowledge;
create trigger trg_touch_knowledge before update on client_knowledge
for each row execute function touch_updated_at();

-- ---- seed example (the test clinic) ----
-- insert into clients (name, retell_agent_id, retell_llm_id)
-- values ('Bronte Creek Physiotherapy', 'agent_xxx', 'llm_xxx');
