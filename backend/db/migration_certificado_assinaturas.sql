-- ══════════════════════════════════════════════════════════════════
-- Gravan — Certificado de Assinaturas Digitais
--
-- Adiciona:
--   • user_agent em contract_signers (dispositivo/navegador)
--   • certificado_hash em contracts  (hash SHA-256 do doc final)
--   • certificado_at  em contracts   (timestamp de emissão)
--
-- Execute via Supabase SQL Editor com service_role key.
-- Idempotente — seguro rodar mais de uma vez.
-- ══════════════════════════════════════════════════════════════════

-- 1. user_agent no registro de cada assinatura
alter table public.contract_signers
  add column if not exists user_agent text;

-- 2. Hash de integridade do documento certificado
alter table public.contracts
  add column if not exists certificado_hash text;

-- 3. Timestamp de emissão do certificado
alter table public.contracts
  add column if not exists certificado_at timestamptz;

-- Confirma
select
  column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name in ('contract_signers', 'contracts')
  and column_name in ('user_agent', 'certificado_hash', 'certificado_at')
order by table_name, column_name;
