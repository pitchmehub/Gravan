-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: Saque com OTP por e-mail + janela de 24h
--
-- COMO EXECUTAR:
--   Supabase → SQL Editor → cole TUDO → RUN. Idempotente.
-- ══════════════════════════════════════════════════════════════════

-- 1. Novas colunas em saques
alter table public.saques add column if not exists otp_hash          text;
alter table public.saques add column if not exists otp_expires_at    timestamptz;
alter table public.saques add column if not exists otp_attempts      int  not null default 0;
alter table public.saques add column if not exists confirmado_em     timestamptz;
alter table public.saques add column if not exists liberar_em        timestamptz;
alter table public.saques add column if not exists cancel_token_hash text;
alter table public.saques add column if not exists cancelado_em      timestamptz;
alter table public.saques add column if not exists cancelado_motivo  text;
alter table public.saques add column if not exists ip_hash           text;
alter table public.saques add column if not exists user_agent        text;

create index if not exists idx_saques_liberar_em on public.saques(liberar_em)
  where status = 'aguardando_liberacao';
create index if not exists idx_saques_perfil_status on public.saques(perfil_id, status);
create index if not exists idx_saques_cancel_token on public.saques(cancel_token_hash)
  where cancel_token_hash is not null;

-- 2. Estados possíveis (texto livre — não usamos enum pra ser tolerante a histórico):
--    pendente_otp        → criado, aguardando código de e-mail
--    aguardando_liberacao→ OTP confirmado; aguarda janela de 24h
--    processando         → janela passou, transfer Stripe em andamento
--    pago                → concluído com sucesso
--    rejeitado           → falha no Stripe / admin negou
--    cancelado           → usuário cancelou via link "não fui eu"
--    expirado            → OTP não foi confirmado em 10 min

-- 3. RLS: o usuário continua vendo só os próprios saques (já coberto em rls_security.sql).

-- 4. Função para liberar saques cuja janela expirou (chamada pelo cron).
--    Marca como 'processando' para o backend então criar o Transfer Stripe.
create or replace function public.saques_a_liberar(p_limit int default 50)
returns setof public.saques
language sql
security definer
as $$
  update public.saques
     set status = 'processando'
   where id in (
     select id from public.saques
      where status = 'aguardando_liberacao'
        and liberar_em <= now()
      order by liberar_em
      limit p_limit
      for update skip locked
   )
  returning *;
$$;

-- 5. Limpeza periódica de OTPs expirados (chamada pelo cron junto)
create or replace function public.saques_expirar_otps()
returns int
language sql
security definer
as $$
  with x as (
    update public.saques
       set status = 'expirado'
     where status = 'pendente_otp'
       and otp_expires_at < now()
    returning 1
  )
  select count(*)::int from x;
$$;

-- 6. View de auditoria rápida pro admin
create or replace view public.saques_pendentes_admin as
select
  id, perfil_id, valor_cents, status,
  created_at, confirmado_em, liberar_em, cancelado_em,
  cancelado_motivo
from public.saques
where status in ('pendente_otp','aguardando_liberacao','processando');

grant select on public.saques_pendentes_admin to authenticated;
