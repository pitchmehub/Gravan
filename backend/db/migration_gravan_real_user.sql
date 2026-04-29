-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: Editora Operacional → Usuário Real
--
-- Substitui o UUID fantasma 00000000-0000-0000-0000-000000000001
-- pelo UUID real do proprietário: e96bd8af-dfb8-4bf1-9ba5-7746207269cd
--
-- Execute via Supabase SQL Editor com service_role key.
-- Idempotente — seguro rodar mais de uma vez.
-- ══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 1. Garante coluna is_gravan_operacional em perfis
-- ────────────────────────────────────────────────────────────────
alter table public.perfis
  add column if not exists is_gravan_operacional boolean not null default false;

-- ────────────────────────────────────────────────────────────────
-- 2. Atualiza o perfil REAL como Editora Operacional Gravan
-- ────────────────────────────────────────────────────────────────
update public.perfis set
  role                  = 'publisher',
  razao_social          = 'GRAVAN EDITORA MUSICAL LTDA.',
  nome_fantasia         = 'Gravan Editora',
  cnpj                  = '64.342.514/0001-08',
  endereco_cidade       = 'Rio de Janeiro',
  endereco_uf           = 'RJ',
  is_gravan_operacional = true,
  cadastro_completo     = true,
  updated_at            = now()
where id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd';

-- ────────────────────────────────────────────────────────────────
-- 3. Migra obras do UUID antigo para o UUID real
-- ────────────────────────────────────────────────────────────────
update public.obras set
  publisher_id      = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd',
  gravan_editora_id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'
where publisher_id = '00000000-0000-0000-0000-000000000001'
   or gravan_editora_id = '00000000-0000-0000-0000-000000000001';

-- ────────────────────────────────────────────────────────────────
-- 4. Migra contratos de edição (contracts_edicao)
-- ────────────────────────────────────────────────────────────────
update public.contracts_edicao set
  publisher_id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'
where publisher_id = '00000000-0000-0000-0000-000000000001';

-- ────────────────────────────────────────────────────────────────
-- 5. Migra assinantes (contract_signers) dos contratos de licenciamento
-- ────────────────────────────────────────────────────────────────
update public.contract_signers set
  user_id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'
where user_id = '00000000-0000-0000-0000-000000000001';

-- ────────────────────────────────────────────────────────────────
-- 6. Migra contratos principais (contracts) seller_id se necessário
-- ────────────────────────────────────────────────────────────────
update public.contracts set
  seller_id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'
where seller_id = '00000000-0000-0000-0000-000000000001';

-- ────────────────────────────────────────────────────────────────
-- 7. Migra wallets (caso tenha sido criada para o UUID fantasma)
-- ────────────────────────────────────────────────────────────────
-- Transfere saldo para o perfil real se havia wallet no UUID antigo
do $$
declare
  v_saldo_antigo bigint;
  v_saldo_atual  bigint;
begin
  select saldo_cents into v_saldo_antigo
    from public.wallets
   where perfil_id = '00000000-0000-0000-0000-000000000001'
   limit 1;

  if v_saldo_antigo is not null then
    select coalesce(saldo_cents, 0) into v_saldo_atual
      from public.wallets
     where perfil_id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'
     limit 1;

    insert into public.wallets (perfil_id, saldo_cents)
    values ('e96bd8af-dfb8-4bf1-9ba5-7746207269cd', v_saldo_atual + v_saldo_antigo)
    on conflict (perfil_id) do update
      set saldo_cents = excluded.saldo_cents,
          updated_at  = now();

    delete from public.wallets
     where perfil_id = '00000000-0000-0000-0000-000000000001';
  end if;
end $$;

-- ────────────────────────────────────────────────────────────────
-- 8. Migra pagamentos_compositores (se houver linhas com o UUID antigo)
-- ────────────────────────────────────────────────────────────────
update public.pagamentos_compositores set
  perfil_id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd'
where perfil_id = '00000000-0000-0000-0000-000000000001';

-- ────────────────────────────────────────────────────────────────
-- 9. Garante FK gravan_editora_id → perfis (para o UUID real)
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'obras_gravan_editora_fk'
  ) then
    alter table public.obras
      add constraint obras_gravan_editora_fk
      foreign key (gravan_editora_id) references public.perfis(id) on delete set null;
  end if;
end $$;

-- ────────────────────────────────────────────────────────────────
-- 10. Confirma resultado
-- ────────────────────────────────────────────────────────────────
select
  id,
  nome,
  role,
  razao_social,
  nome_fantasia,
  cnpj,
  is_gravan_operacional
from public.perfis
where id = 'e96bd8af-dfb8-4bf1-9ba5-7746207269cd';
