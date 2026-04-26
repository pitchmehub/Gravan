-- ============================================================
-- Migration: rastreio de origem (source_transaction) nos saques
-- ============================================================
-- A Stripe Connect EXIGE que toda Transfer envolvendo contas
-- brasileiras seja vinculada à Charge de origem via parâmetro
-- `source_transaction=ch_xxx`. Sem isso, todo Transfer é
-- rejeitado com:
--   "For Transfers involving Brazil, the source_transaction
--    parameter is mandatory."
--
-- Pra atender essa regra, cada saque agora "consome" um ou mais
-- registros da tabela `pagamentos_compositores` (FIFO), e cria
-- uma Stripe Transfer separada por charge, com source_transaction.
--
-- Esta migration adiciona as colunas necessárias e índices.
-- É IDEMPOTENTE: pode rodar várias vezes sem efeito colateral.
-- ============================================================

alter table pagamentos_compositores
  add column if not exists saque_id           uuid references saques(id),
  add column if not exists stripe_charge_id   text,
  add column if not exists liberado_em        timestamptz;

-- Índice rápido pro processador FIFO de saques
create index if not exists idx_pagcomp_perfil_pendente
  on pagamentos_compositores (perfil_id, created_at)
  where status = 'pendente' and saque_id is null;

-- Índice de auditoria por saque
create index if not exists idx_pagcomp_saque
  on pagamentos_compositores (saque_id)
  where saque_id is not null;
