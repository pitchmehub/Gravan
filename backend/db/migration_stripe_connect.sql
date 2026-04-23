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