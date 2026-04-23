-- ══════════════════════════════════════════════════════════════════
-- Pitch.me — PATCH: ajusta RLS de `perfis` para permitir JOINs
--
-- Rode este SQL UMA VEZ no Supabase se você executou o rls_security.sql
-- e percebeu que os nomes de titular/coautores sumiram na Descoberta
-- e em "Minhas Obras".
--
-- O QUE FAZ:
--   - Permite que QUALQUER usuário autenticado LEIA perfis (via JOIN)
--     → isso resolve o caso dos nomes sumirem no catálogo público
--   - Mantém INSERT / UPDATE / DELETE restritos (só dono e admin)
--   - CPF e RG continuam criptografados no banco (proteção aplicada
--     no backend via `utils/crypto.py`, não depende de RLS).
-- ══════════════════════════════════════════════════════════════════

alter table public.perfis enable row level security;

drop policy if exists "perfis_sel" on public.perfis;

-- SELECT liberado para qualquer usuário autenticado (CPF/RG estão criptografados)
create policy "perfis_sel" on public.perfis for select
  using (auth.role() = 'authenticated');

-- Verificação
select policyname, cmd, qual
  from pg_policies
 where schemaname = 'public'
   and tablename = 'perfis'
 order by cmd, policyname;
