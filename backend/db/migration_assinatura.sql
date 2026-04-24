-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: Sistema de Assinatura (STARTER / PRO) + Favoritos + Analytics
--
-- COMO EXECUTAR:
--   Cole TODO este arquivo no SQL Editor do Supabase e clique em RUN.
--   Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 0. LIMPEZA LEGADA — remove policies/views/funções de migrações
-- antigas que referenciam "public.Admin" (tabela inexistente que
-- bloqueia novas alterações em `perfis`).
-- ────────────────────────────────────────────────────────────────
do $$
declare
  pol record;
  obj record;
begin
  -- Dropa TODAS as policies cujo definition menciona "Admin" (case-sensitive)
  for pol in
    select schemaname, tablename, policyname
      from pg_policies
     where qual like '%public.Admin%'
        or qual like '%"Admin"%'
        or with_check like '%public.Admin%'
        or with_check like '%"Admin"%'
  loop
    execute format('drop policy if exists %I on %I.%I',
                   pol.policyname, pol.schemaname, pol.tablename);
  end loop;

  -- Dropa views que mencionam Admin
  for obj in
    select schemaname, viewname
      from pg_views
     where definition like '%public.Admin%' or definition like '%"Admin"%'
  loop
    execute format('drop view if exists %I.%I cascade', obj.schemaname, obj.viewname);
  end loop;

  -- Dropa funções que mencionam Admin
  for obj in
    select n.nspname as schemaname, p.proname as funcname,
           pg_get_function_identity_arguments(p.oid) as args
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.prokind = 'f'                -- só funções normais, não aggregates/windows
       and (pg_get_functiondef(p.oid) like '%public.Admin%'
            or pg_get_functiondef(p.oid) like '%"Admin"%')
  loop
    execute format('drop function if exists %I.%I(%s) cascade',
                   obj.schemaname, obj.funcname, obj.args);
  end loop;
end $$;

-- ────────────────────────────────────────────────────────────────
-- 1. perfis — colunas de plano/assinatura
-- ────────────────────────────────────────────────────────────────
alter table public.perfis add column if not exists plano                  text    not null default 'STARTER';
alter table public.perfis add column if not exists status_assinatura      text    not null default 'inativa';
alter table public.perfis add column if not exists assinatura_inicio      timestamptz;
alter table public.perfis add column if not exists assinatura_fim         timestamptz;
alter table public.perfis add column if not exists stripe_customer_id     text;
alter table public.perfis add column if not exists stripe_subscription_id text;

-- Constraints (re-criam idempotentemente)
do $$ begin
  alter table public.perfis drop constraint if exists perfis_plano_check;
  alter table public.perfis add  constraint perfis_plano_check             check (plano in ('STARTER','PRO'));
  alter table public.perfis drop constraint if exists perfis_status_assinatura_check;
  alter table public.perfis add  constraint perfis_status_assinatura_check check (status_assinatura in ('ativa','inativa','cancelada','past_due'));
end $$;

create index if not exists idx_perfis_stripe_customer     on public.perfis (stripe_customer_id);
create index if not exists idx_perfis_stripe_subscription on public.perfis (stripe_subscription_id);

-- ────────────────────────────────────────────────────────────────
-- 2. favoritos (biblioteca pessoal)
-- ────────────────────────────────────────────────────────────────
create table if not exists public.favoritos (
  id          uuid primary key default gen_random_uuid(),
  perfil_id   uuid not null references public.perfis(id) on delete cascade,
  obra_id     uuid not null references public.obras(id)  on delete cascade,
  created_at  timestamptz not null default now(),
  unique (perfil_id, obra_id)
);

create index if not exists idx_favoritos_perfil on public.favoritos (perfil_id);
create index if not exists idx_favoritos_obra   on public.favoritos (obra_id);

-- ────────────────────────────────────────────────────────────────
-- 3. obra_analytics (agregado por obra) + play_events (cru)
-- ────────────────────────────────────────────────────────────────
create table if not exists public.obra_analytics (
  obra_id          uuid primary key references public.obras(id) on delete cascade,
  plays_count      int not null default 0,
  favorites_count  int not null default 0,
  last_played_at   timestamptz
);

create table if not exists public.play_events (
  id          uuid primary key default gen_random_uuid(),
  obra_id     uuid not null references public.obras(id) on delete cascade,
  perfil_id   uuid references public.perfis(id) on delete set null,
  ip_hash     text,
  created_at  timestamptz not null default now()
);

create index if not exists idx_play_events_obra on public.play_events (obra_id, created_at desc);

-- Triggers para manter obra_analytics atualizado
create or replace function public.fn_favoritos_inc()
returns trigger language plpgsql as $$
begin
  insert into public.obra_analytics (obra_id, favorites_count)
       values (new.obra_id, 1)
  on conflict (obra_id) do update set favorites_count = obra_analytics.favorites_count + 1;
  return new;
end $$;

create or replace function public.fn_favoritos_dec()
returns trigger language plpgsql as $$
begin
  update public.obra_analytics
     set favorites_count = greatest(favorites_count - 1, 0)
   where obra_id = old.obra_id;
  return old;
end $$;

drop trigger if exists trg_favoritos_inc on public.favoritos;
create trigger trg_favoritos_inc after insert on public.favoritos
  for each row execute function public.fn_favoritos_inc();

drop trigger if exists trg_favoritos_dec on public.favoritos;
create trigger trg_favoritos_dec after delete on public.favoritos
  for each row execute function public.fn_favoritos_dec();

create or replace function public.fn_play_events_inc()
returns trigger language plpgsql as $$
begin
  insert into public.obra_analytics (obra_id, plays_count, last_played_at)
       values (new.obra_id, 1, new.created_at)
  on conflict (obra_id) do update
     set plays_count    = obra_analytics.plays_count + 1,
         last_played_at = excluded.last_played_at;
  return new;
end $$;

drop trigger if exists trg_play_events_inc on public.play_events;
create trigger trg_play_events_inc after insert on public.play_events
  for each row execute function public.fn_play_events_inc();

-- ────────────────────────────────────────────────────────────────
-- 4. RLS nas novas tabelas
-- ────────────────────────────────────────────────────────────────
alter table public.favoritos      enable row level security;
alter table public.obra_analytics enable row level security;
alter table public.play_events    enable row level security;

-- favoritos: dono lê/escreve o próprio; admin vê tudo
drop policy if exists "favoritos_sel" on public.favoritos;
drop policy if exists "favoritos_ins" on public.favoritos;
drop policy if exists "favoritos_del" on public.favoritos;

create policy "favoritos_sel" on public.favoritos for select
  using (auth.uid() = perfil_id or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'));
create policy "favoritos_ins" on public.favoritos for insert with check (auth.uid() = perfil_id);
create policy "favoritos_del" on public.favoritos for delete using (auth.uid() = perfil_id);

-- obra_analytics: dono da obra vê; público vê só contagens agregadas (via view)
drop policy if exists "analytics_sel_owner" on public.obra_analytics;
create policy "analytics_sel_owner" on public.obra_analytics for select
  using (
    exists (select 1 from public.obras o where o.id = obra_analytics.obra_id and o.titular_id = auth.uid())
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

-- play_events: ninguém lê via REST (apenas backend com service_role); insert liberado
drop policy if exists "play_events_ins" on public.play_events;
create policy "play_events_ins" on public.play_events for insert with check (true);

revoke all on public.play_events from anon, authenticated;
grant insert on public.play_events to anon, authenticated;

-- ────────────────────────────────────────────────────────────────
-- 5. VERIFICAÇÃO
-- ────────────────────────────────────────────────────────────────
select
  'perfis.plano'             as item, exists (select 1 from information_schema.columns where table_schema='public' and table_name='perfis' and column_name='plano')             as ok
union all select 'table favoritos',       exists (select 1 from information_schema.tables  where table_schema='public' and table_name='favoritos')
union all select 'table obra_analytics',  exists (select 1 from information_schema.tables  where table_schema='public' and table_name='obra_analytics')
union all select 'table play_events',     exists (select 1 from information_schema.tables  where table_schema='public' and table_name='play_events');
