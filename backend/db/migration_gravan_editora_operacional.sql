-- ══════════════════════════════════════════════════════════════════
-- Gravan — EDITORA OPERACIONAL
-- UUID fixo: 00000000-0000-0000-0000-000000000001
--
-- ATENÇÃO: Execute via Supabase SQL Editor com service_role key.
-- Este script PRIMEIRO insere o usuário em auth.users (necessário
-- por causa da FK), depois cria o perfil operacional.
-- ══════════════════════════════════════════════════════════════════

-- 1) Garante enum 'publisher'
do $$
begin
  if not exists (
    select 1 from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    where t.typname = 'user_role' and e.enumlabel = 'publisher'
  ) then
    alter type public.user_role add value 'publisher';
  end if;
end $$;

-- 2) Coluna is_gravan_operacional na tabela perfis
alter table public.perfis
  add column if not exists is_gravan_operacional boolean not null default false;

-- 3) Coluna gravan_editora_id nas obras
alter table public.obras
  add column if not exists gravan_editora_id uuid;

create index if not exists idx_obras_gravan_editora
  on public.obras(gravan_editora_id);

-- 4) Cria o usuário fantasma em auth.users (necessário para FK)
--    Usa INSERT ... ON CONFLICT DO NOTHING para idempotência
insert into auth.users (
  id,
  instance_id,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  raw_app_meta_data,
  raw_user_meta_data,
  is_super_admin,
  role
)
values (
  '00000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000000',
  'editora-operacional@gravan.com.br',
  '',
  now(),
  now(),
  now(),
  '{"provider":"system","providers":["system"]}'::jsonb,
  '{"is_gravan_operacional":true}'::jsonb,
  false,
  'authenticated'
)
on conflict (id) do nothing;

-- 5) Cria/atualiza o perfil da Gravan Editora Operacional
insert into public.perfis (
  id,
  email,
  nome,
  role,
  razao_social,
  nome_fantasia,
  cnpj,
  responsavel_nome,
  endereco_cidade,
  endereco_uf,
  cadastro_completo,
  is_gravan_operacional,
  created_at,
  updated_at
)
values (
  '00000000-0000-0000-0000-000000000001',
  'editora-operacional@gravan.com.br',
  'Gravan Editora Musical',
  'publisher',
  'GRAVAN EDITORA MUSICAL LTDA.',
  'Gravan Editora',
  '64.342.514/0001-08',
  'Gravan Editora Operacional',
  'Rio de Janeiro',
  'RJ',
  true,
  true,
  now(),
  now()
)
on conflict (id) do update set
  email                 = excluded.email,
  nome                  = excluded.nome,
  razao_social          = excluded.razao_social,
  nome_fantasia         = excluded.nome_fantasia,
  cnpj                  = excluded.cnpj,
  is_gravan_operacional = true,
  updated_at            = now();

-- 6) Garante FK em obras.gravan_editora_id (após perfil existir)
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
