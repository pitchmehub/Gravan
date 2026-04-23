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
