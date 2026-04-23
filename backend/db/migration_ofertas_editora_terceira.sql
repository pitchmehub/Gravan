-- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Migração: Licenciamento de Obras Editadas por Terceiros
--
-- Permite que obras com contrato de edição prévio (com OUTRA editora)
-- entrem no catálogo. Quando um intérprete licencia uma dessas obras,
-- o valor fica retido (escrow no Stripe — manual capture) e a editora
-- terceira recebe um e-mail com prazo de 72 horas úteis (BRT, 10–18h,
-- excluindo feriados nacionais brasileiros) para se cadastrar e
-- assinar o contrato trilateral. Se ela não cumprir o prazo, o valor
-- é estornado automaticamente para o comprador.
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1. Campos em `obras` para indicar edição prévia por terceiros
alter table public.obras
  add column if not exists obra_editada_terceiros  boolean       not null default false,
  add column if not exists editora_terceira_nome     text,
  add column if not exists editora_terceira_email    text,
  add column if not exists editora_terceira_telefone text,
  add column if not exists editora_terceira_id       uuid references public.perfis(id) on delete set null;

create index if not exists idx_obras_editora_terceira
  on public.obras (editora_terceira_id)
  where editora_terceira_id is not null;

create index if not exists idx_obras_editora_terceira_email
  on public.obras (lower(editora_terceira_email))
  where editora_terceira_email is not null;


-- 2. Tabela de ofertas de licenciamento (escrow + prazo)
create table if not exists public.ofertas_licenciamento (
  id                            uuid primary key default gen_random_uuid(),
  obra_id                       uuid not null references public.obras(id)   on delete restrict,
  comprador_id                  uuid not null references public.perfis(id)  on delete restrict,
  valor_cents                   integer not null check (valor_cents >= 100),

  -- Snapshot da editora terceira no momento da oferta
  editora_terceira_nome         text not null,
  editora_terceira_email        text not null,
  editora_terceira_telefone     text,
  editora_terceira_id           uuid references public.perfis(id) on delete set null,

  -- Token único usado no link enviado por e-mail (cadastro publisher)
  registration_token            text not null unique,

  -- Stripe (manual-capture: hold no cartão até a assinatura)
  stripe_checkout_session_id    text,
  stripe_payment_intent_id      text,

  -- Estado da oferta
  status                        text not null default 'aguardando_editora',
  deadline_at                   timestamptz not null,
  reminder_48h_sent_at          timestamptz,
  reminder_24h_sent_at          timestamptz,

  -- Marcos
  pago_em                       timestamptz,
  editora_cadastrada_em         timestamptz,
  contrato_id                   uuid references public.contracts(id) on delete set null,
  concluida_em                  timestamptz,
  expirada_em                   timestamptz,
  reembolsada_em                timestamptz,
  cancelada_em                  timestamptz,

  created_at                    timestamptz not null default now(),
  updated_at                    timestamptz not null default now(),

  constraint ofertas_status_check check (status in (
    'aguardando_pagamento',
    'aguardando_editora',
    'editora_cadastrada',
    'em_assinatura',
    'concluida',
    'expirada',
    'reembolsada',
    'cancelada'
  ))
);

create index if not exists idx_ofertas_obra        on public.ofertas_licenciamento (obra_id);
create index if not exists idx_ofertas_comprador   on public.ofertas_licenciamento (comprador_id);
create index if not exists idx_ofertas_editora     on public.ofertas_licenciamento (editora_terceira_id);
create index if not exists idx_ofertas_status      on public.ofertas_licenciamento (status);
create index if not exists idx_ofertas_deadline    on public.ofertas_licenciamento (deadline_at) where status in ('aguardando_editora','editora_cadastrada','em_assinatura');
create unique index if not exists uq_ofertas_pi    on public.ofertas_licenciamento (stripe_payment_intent_id) where stripe_payment_intent_id is not null;
create unique index if not exists uq_ofertas_sess  on public.ofertas_licenciamento (stripe_checkout_session_id) where stripe_checkout_session_id is not null;

-- updated_at automático
create or replace function public._touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at := now(); return new; end $$;

drop trigger if exists trg_ofertas_touch on public.ofertas_licenciamento;
create trigger trg_ofertas_touch before update on public.ofertas_licenciamento
  for each row execute function public._touch_updated_at();


-- 3. Coluna em contracts para identificar contratos trilaterais
alter table public.contracts
  add column if not exists trilateral boolean not null default false,
  add column if not exists oferta_id  uuid references public.ofertas_licenciamento(id) on delete set null;

-- Atualiza constraint de roles em contract_signers para aceitar 'editora' e 'pitchme'
do $$
begin
  alter table public.contract_signers drop constraint if exists signers_role_check;
  alter table public.contract_signers add constraint signers_role_check
    check (role in ('autor','coautor','intérprete','interprete','editora','editora_terceira','pitchme'));
exception when others then null;
end $$;


-- 4. RLS — comprador, editora envolvida e admin
alter table public.ofertas_licenciamento enable row level security;

drop policy if exists "ofertas_sel" on public.ofertas_licenciamento;
create policy "ofertas_sel" on public.ofertas_licenciamento for select using (
  auth.uid() = comprador_id
  or auth.uid() = editora_terceira_id
  or exists (
    select 1 from public.obras o
    where o.id = ofertas_licenciamento.obra_id and o.titular_id = auth.uid()
  )
  or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
);

revoke insert, update, delete on public.ofertas_licenciamento from anon, authenticated;


-- 5. Verificação
select
  'obras.obra_editada_terceiros'   as item,
  exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras'
         and column_name='obra_editada_terceiros') as ok
union all select 'obras.editora_terceira_email',
  exists(select 1 from information_schema.columns where table_schema='public' and table_name='obras'
         and column_name='editora_terceira_email')
union all select 'table ofertas_licenciamento',
  exists(select 1 from information_schema.tables where table_schema='public' and table_name='ofertas_licenciamento')
union all select 'contracts.trilateral',
  exists(select 1 from information_schema.columns where table_schema='public' and table_name='contracts'
         and column_name='trilateral');
