-- Pitch.me — FIX_MISSING.SQL
  -- Cole inteiro no SQL Editor do Supabase. Executa exatamente os 5 itens
  -- que ainda estavam faltando no healthcheck:
  --   • tabela assinaturas
  --   • tabela contratos_licenciamento
  --   • tabela stripe_connect_accounts
  --   • view bi_auditoria_splits
  --   • bucket + policies obras-audio
  -- Idempotente.

  
  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 01/05  —  MIGRATION LICENCIAMENTO                                ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Migração: Contratos de Licenciamento + Assinatura digital
--
-- COMO EXECUTAR:
--   Cole no SQL Editor do Supabase e clique em RUN.
--   Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1. Colunas ISRC / ISWC em obras (opcionais)
alter table public.obras add column if not exists isrc text;
alter table public.obras add column if not exists iswc text;

-- 2. Tabela contracts (contrato de licenciamento)
create table if not exists public.contracts (
  id               uuid primary key default gen_random_uuid(),
  transacao_id     uuid unique references public.transacoes(id) on delete cascade,
  obra_id          uuid not null references public.obras(id)      on delete cascade,
  seller_id        uuid not null references public.perfis(id)     on delete set null,
  buyer_id         uuid not null references public.perfis(id)     on delete set null,
  valor_cents      integer not null,
  contract_html    text not null,
  contract_text    text not null,
  status           text not null default 'pendente',
  versao           text not null default 'v1.0',
  completed_at     timestamptz,
  created_at       timestamptz not null default now(),
  constraint contracts_status_check check (status in ('pendente','assinado','concluído','cancelado'))
);

create index if not exists idx_contracts_obra     on public.contracts (obra_id);
create index if not exists idx_contracts_seller   on public.contracts (seller_id);
create index if not exists idx_contracts_buyer    on public.contracts (buyer_id);

-- 3. Tabela contract_signers (cada parte que precisa assinar)
create table if not exists public.contract_signers (
  id            uuid primary key default gen_random_uuid(),
  contract_id   uuid not null references public.contracts(id) on delete cascade,
  user_id       uuid not null references public.perfis(id)    on delete set null,
  role          text not null,
  share_pct     numeric(6,3),
  signed        boolean not null default false,
  signed_at     timestamptz,
  ip_hash       text,
  created_at    timestamptz not null default now(),
  unique (contract_id, user_id),
  constraint signers_role_check check (role in ('autor','coautor','intérprete','interprete'))
);

create index if not exists idx_signers_contract on public.contract_signers (contract_id);
create index if not exists idx_signers_user     on public.contract_signers (user_id);

-- 4. Tabela de log (auditoria)
create table if not exists public.contract_events (
  id          uuid primary key default gen_random_uuid(),
  contract_id uuid not null references public.contracts(id) on delete cascade,
  user_id     uuid references public.perfis(id) on delete set null,
  event_type  text not null,
  payload     jsonb,
  created_at  timestamptz not null default now()
);
create index if not exists idx_events_contract on public.contract_events (contract_id, created_at desc);

-- 5. RLS — só partes envolvidas podem ver; admin sempre vê
alter table public.contracts        enable row level security;
alter table public.contract_signers enable row level security;
alter table public.contract_events  enable row level security;

drop policy if exists "contracts_sel" on public.contracts;
create policy "contracts_sel" on public.contracts for select using (
  auth.uid() = seller_id
  or auth.uid() = buyer_id
  or exists (select 1 from public.contract_signers s where s.contract_id = contracts.id and s.user_id = auth.uid())
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);

drop policy if exists "signers_sel" on public.contract_signers;
create policy "signers_sel" on public.contract_signers for select using (
  auth.uid() = user_id
  or exists (select 1 from public.contracts c where c.id = contract_signers.contract_id and (c.seller_id = auth.uid() or c.buyer_id = auth.uid()))
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);

drop policy if exists "events_sel" on public.contract_events;
create policy "events_sel" on public.contract_events for select using (
  exists (select 1 from public.contracts c where c.id = contract_events.contract_id and (c.seller_id = auth.uid() or c.buyer_id = auth.uid()))
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);

revoke insert, update, delete on public.contracts        from anon, authenticated;
revoke insert, update, delete on public.contract_signers from anon, authenticated;
revoke insert, update, delete on public.contract_events  from anon, authenticated;

-- 6. Verificação
select
  'table contracts'         as item, exists(select 1 from information_schema.tables where table_schema='public' and table_name='contracts') as ok
union all select 'table contract_signers',  exists(select 1 from information_schema.tables where table_schema='public' and table_name='contract_signers')
union all select 'table contract_events',   exists(select 1 from information_schema.tables where table_schema='public' and table_name='contract_events')
union all select 'obras.isrc',              exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='isrc')
union all select 'obras.iswc',              exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='iswc');


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 02/05  —  MIGRATION ASSINATURA                                   ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Migração: Sistema de Assinatura (STARTER / PRO) + Favoritos + Analytics
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


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 03/05  —  MIGRATION STRIPE CONNECT                               ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ═══════════════════════════════════════════════════════════════════
-- Migration: Stripe Connect (Express Accounts) + Repasses
-- ═══════════════════════════════════════════════════════════════════

-- 1. Colunas Stripe Connect no perfil ─────────────────────────────────
alter table public.perfis
  add column if not exists stripe_account_id text,
  add column if not exists stripe_charges_enabled boolean default false,
  add column if not exists stripe_payouts_enabled boolean default false,
  add column if not exists stripe_onboarding_completo boolean default false,
  add column if not exists stripe_account_atualizado_em timestamptz;

create index if not exists idx_perfis_stripe_account on public.perfis(stripe_account_id);


-- 2. Tabela de repasses (Transfers Stripe) ────────────────────────────
create table if not exists public.repasses (
  id              uuid primary key default gen_random_uuid(),
  transacao_id    uuid not null references public.transacoes(id) on delete cascade,
  perfil_id       uuid not null references public.perfis(id),
  valor_cents     int  not null check (valor_cents > 0),
  share_pct       numeric(6,3) not null,
  stripe_transfer_id  text unique,
  stripe_account_id   text,
  status          text not null default 'pendente',
  erro_msg        text,
  metadata        jsonb default '{}'::jsonb,
  created_at      timestamptz default now(),
  enviado_at      timestamptz,
  liberado_at     timestamptz,
  constraint repasses_status_check check (status in
    ('pendente', 'retido', 'enviado', 'falhou', 'revertido'))
);

create index if not exists idx_repasses_transacao on public.repasses(transacao_id);
create index if not exists idx_repasses_perfil    on public.repasses(perfil_id);
create index if not exists idx_repasses_status    on public.repasses(status);


-- 3. RLS — repasses ──────────────────────────────────────────────────
alter table public.repasses enable row level security;

drop policy if exists repasses_select_own on public.repasses;
drop policy if exists repasses_admin_all  on public.repasses;

create policy repasses_select_own on public.repasses
  for select using (perfil_id = auth.uid());

create policy repasses_admin_all on public.repasses
  for all using (
    exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );


-- 4. View de saldo retido por perfil ──────────────────────────────────
create or replace view public.v_saldo_retido as
select
  perfil_id,
  count(*)::int                     as qtd_repasses_retidos,
  coalesce(sum(valor_cents),0)::int as valor_retido_cents
from public.repasses
where status = 'retido'
group by perfil_id;


-- 5. Saques via Stripe ────────────────────────────────────────────────
alter table public.saques
  add column if not exists stripe_transfer_id text unique,
  add column if not exists stripe_account_id  text,
  add column if not exists metodo             text default 'paypal';

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='saques'
      and column_name='paypal_email' and is_nullable='NO'
  ) then
    execute 'alter table public.saques alter column paypal_email drop not null';
  end if;
end $$;

create index if not exists idx_saques_stripe_transfer on public.saques(stripe_transfer_id);


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 04/05  —  VIEW bi_auditoria_splits                               ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  
  do $$
  begin
    if exists (select 1 from information_schema.tables
                where table_schema='public' and table_name='obras_autores') then
      execute 'drop view if exists public.bi_auditoria_splits cascade';
      execute $v$
        create view public.bi_auditoria_splits as
        select oa.obra_id, o.nome as obra_nome,
               count(*) as qtd_autores, sum(oa.share_pct) as soma_splits
          from public.obras_autores oa
          join public.obras o on o.id = oa.obra_id
         group by oa.obra_id, o.nome
      $v$;
    end if;
  end $$;


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 05/05  —  STORAGE BUCKET + POLICIES (obras-audio)                ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Storage: bucket de áudio das obras
--
-- COMO EXECUTAR:
--   Cole no SQL Editor do Supabase e clique RUN.
--   Idempotente — seguro rodar várias vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1. Cria o bucket (privado). Tamanho máx por arquivo = 10 MB.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'obras-audio', 'obras-audio', false,
  10 * 1024 * 1024,
  array['audio/mpeg','audio/mp3']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- 2. Policies — só usuários autenticados podem upar/ler/deletar
--    seus próprios arquivos (path começa com o auth.uid()).

drop policy if exists "obras-audio insert auth"  on storage.objects;
drop policy if exists "obras-audio select auth"  on storage.objects;
drop policy if exists "obras-audio delete owner" on storage.objects;
drop policy if exists "obras-audio update owner" on storage.objects;

create policy "obras-audio insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "obras-audio select auth"
on storage.objects for select to authenticated
using (bucket_id = 'obras-audio');

create policy "obras-audio update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "obras-audio delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);

