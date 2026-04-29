-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: Certificado de Assinaturas Universal
--
-- Adiciona colunas de certificado digital a TODOS os tipos de
-- contrato da plataforma que ainda não possuíam:
--
--   1. contracts_edicao  (Contrato de Edição: autor ↔ editora)
--   2. agregado_convites (Termo de Agregação: artista ↔ editora)
--
-- O contrato de licenciamento (contracts) já possui essas colunas.
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 1. contracts_edicao
-- ────────────────────────────────────────────────────────────────
alter table public.contracts_edicao
  add column if not exists certificado_html text,
  add column if not exists certificado_hash text,
  add column if not exists certificado_at   timestamptz;

-- ────────────────────────────────────────────────────────────────
-- 2. agregado_convites
-- ────────────────────────────────────────────────────────────────
alter table public.agregado_convites
  add column if not exists termo_text       text,       -- versão texto puro do termo (para exibição)
  add column if not exists certificado_html text,
  add column if not exists certificado_hash text,
  add column if not exists certificado_at   timestamptz;

-- ────────────────────────────────────────────────────────────────
-- 3. Confirma resultado
-- ────────────────────────────────────────────────────────────────
select table_name, column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name in ('contracts_edicao', 'agregado_convites')
  and column_name like 'certificado%'
order by table_name, column_name;
