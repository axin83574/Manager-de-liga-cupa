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

create table if not exists public.app_support_messages (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    sender_username text,
    sender_name text not null,
    sender_email text not null default '',
    category text not null default 'Altceva',
    subject text not null,
    message text not null check (char_length(message) between 1 and 4000),
    league_name text not null default '',
    status text not null default 'nou' check (status in ('nou', 'rezolvat'))
);

create index if not exists app_support_messages_created_idx
    on public.app_support_messages (created_at desc);

alter table public.app_support_messages enable row level security;
revoke all on public.app_support_messages from anon, authenticated;
grant all on public.app_support_messages to service_role;
grant usage, select on sequence public.app_support_messages_id_seq to service_role;

create table if not exists public.app_password_resets (
    id bigint generated always as identity primary key,
    username text not null references public.app_users(username) on delete cascade,
    email text not null,
    token_hash text not null unique,
    created_at timestamptz not null default now(),
    expires_at timestamptz not null,
    used_at timestamptz
);

create index if not exists app_password_resets_username_created_idx
    on public.app_password_resets (username, created_at desc);

alter table public.app_password_resets enable row level security;
revoke all on public.app_password_resets from anon, authenticated;
grant all on public.app_password_resets to service_role;
grant usage, select on sequence public.app_password_resets_id_seq to service_role;
