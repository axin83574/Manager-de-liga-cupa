-- Rulare unică în Supabase: SQL Editor → New query → Run.
-- Tabele private folosite numai de aplicația server-side prin service_role.
-- Tabela legacy public.ligi rămâne neatinsă.

create table if not exists public.app_users (
    username text primary key,
    data jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists public.app_leagues (
    id uuid primary key default gen_random_uuid(),
    owner_username text not null references public.app_users(username) on delete cascade,
    nume text not null,
    data jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

create index if not exists app_leagues_owner_updated_idx
    on public.app_leagues (owner_username, updated_at desc);

alter table public.app_users enable row level security;
alter table public.app_leagues enable row level security;

revoke all on public.app_users from anon, authenticated;
revoke all on public.app_leagues from anon, authenticated;
grant all on public.app_users to service_role;
grant all on public.app_leagues to service_role;
