-- Gravan — SETUP_ALL.SQL  (cole inteiro no SQL Editor do Supabase)
  -- Idempotente. Depois rode separadamente storage_buckets.sql.
  
  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 01/08  —  SCHEMA BASE (criado pelo agente)                       ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — SCHEMA BASE  (versão idempotente e tolerante a banco existente)
--
-- Cria/normaliza tabelas, enums, índices e views que TODAS as outras
-- migrações (migration_editora_agregados, migration_licenciamento,
-- migration_assinatura, migration_stripe_connect, rls_security)
-- assumem como já existentes.
--
-- ✅ Funciona em banco vazio.
-- ✅ Funciona em banco que já tem `obras`, `perfis`, etc. parcialmente
--    criadas: usa `alter table ... add column if not exists` em vez
--    de assumir que o create table cria tudo.
--
-- COMO EXECUTAR:
--   1) Cole TODO este arquivo no SQL Editor do Supabase e clique RUN.
--   2) Em seguida, rode na ordem:
--        rls_security.sql
--        migration_editora_agregados.sql
--        migration_licenciamento.sql
--        migration_assinatura.sql
--        migration_stripe_connect.sql
--        patch_rls_perfis_join.sql
--        seed_contrato_edicao.sql
--        storage_buckets.sql
-- ══════════════════════════════════════════════════════════════════

create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

-- ────────────────────────────────────────────────────────────────
-- 1. ENUM user_role
--    (a migração de editora estende este enum com 'publisher')
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if not exists (select 1 from pg_type where typname = 'user_role') then
    create type public.user_role as enum ('compositor','comprador','administrador');
  end if;
end $$;

-- ════════════════════════════════════════════════════════════════
-- 2. PERFIS  (1-1 com auth.users)
-- ════════════════════════════════════════════════════════════════
create table if not exists public.perfis (
  id  uuid primary key references auth.users(id) on delete cascade
);

alter table public.perfis add column if not exists email                 text;
alter table public.perfis add column if not exists nome                  text;
alter table public.perfis add column if not exists nome_artistico        text;
alter table public.perfis add column if not exists role                  public.user_role not null default 'compositor';
alter table public.perfis add column if not exists cpf                   text;
alter table public.perfis add column if not exists rg                    text;
alter table public.perfis add column if not exists telefone              text;
alter table public.perfis add column if not exists endereco_rua          text;
alter table public.perfis add column if not exists endereco_numero       text;
alter table public.perfis add column if not exists endereco_complemento  text;
alter table public.perfis add column if not exists endereco_bairro       text;
alter table public.perfis add column if not exists endereco_cidade       text;
alter table public.perfis add column if not exists endereco_uf           text;
alter table public.perfis add column if not exists endereco_cep          text;
alter table public.perfis add column if not exists cadastro_completo     boolean not null default false;
alter table public.perfis add column if not exists created_at            timestamptz not null default now();
alter table public.perfis add column if not exists updated_at            timestamptz not null default now();

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'perfis_email_unique'
  ) then
    -- só cria a unique se não houver duplicatas
    if not exists (
      select email from public.perfis
      where email is not null group by email having count(*) > 1
    ) then
      alter table public.perfis add constraint perfis_email_unique unique (email);
    end if;
  end if;
end $$;

create index if not exists idx_perfis_email on public.perfis(email);
create index if not exists idx_perfis_role  on public.perfis(role);

-- ════════════════════════════════════════════════════════════════
-- 3. OBRAS
--    Migrações posteriores adicionam: managed_by_publisher,
--    publisher_id, isrc, iswc, e tornam letra NOT NULL.
-- ════════════════════════════════════════════════════════════════
create table if not exists public.obras (
  id  uuid primary key default gen_random_uuid()
);

-- nome OU titulo (algumas instalações antigas usavam "titulo")
alter table public.obras add column if not exists nome           text;
alter table public.obras add column if not exists letra          text;
alter table public.obras add column if not exists genero         text;
alter table public.obras add column if not exists bpm            integer;
alter table public.obras add column if not exists audio_path     text;
alter table public.obras add column if not exists audio_hash     text;
alter table public.obras add column if not exists letra_hash     text;
alter table public.obras add column if not exists capa_url       text;
alter table public.obras add column if not exists preco_cents    integer not null default 0;
alter table public.obras add column if not exists status         text    not null default 'rascunho';
alter table public.obras add column if not exists compositor_id  uuid;
alter table public.obras add column if not exists created_at     timestamptz not null default now();
alter table public.obras add column if not exists updated_at     timestamptz not null default now();

-- Se existia "titular_id" ou "owner_id" ou "autor_id" e não há compositor_id
-- preenchido, copia para a nova coluna (best-effort).
do $$
begin
  if exists (select 1 from information_schema.columns
             where table_schema='public' and table_name='obras' and column_name='titular_id') then
    update public.obras set compositor_id = titular_id where compositor_id is null;
  end if;
  if exists (select 1 from information_schema.columns
             where table_schema='public' and table_name='obras' and column_name='owner_id') then
    update public.obras set compositor_id = owner_id where compositor_id is null;
  end if;
  if exists (select 1 from information_schema.columns
             where table_schema='public' and table_name='obras' and column_name='autor_id') then
    update public.obras set compositor_id = autor_id where compositor_id is null;
  end if;
end $$;

-- FK + check constraint em status (idempotentes)
do $$
declare
  v_udt text;
begin
  if not exists (select 1 from pg_constraint where conname='obras_compositor_fk') then
    alter table public.obras
      add constraint obras_compositor_fk
      foreign key (compositor_id) references public.perfis(id) on delete set null;
  end if;

  -- Descobre se public.obras.status é text ou enum.
  select udt_name into v_udt
    from information_schema.columns
   where table_schema='public' and table_name='obras' and column_name='status';

  if v_udt = 'text' or v_udt is null then
    -- Coluna text → garante o check constraint.
    if not exists (select 1 from pg_constraint where conname='obras_status_check') then
      alter table public.obras
        add constraint obras_status_check
        check (status in ('rascunho','publicada','removida'));
    end if;
  else
    -- Coluna é enum (ex.: obra_status) → adiciona valores que faltarem.
    if not exists (
      select 1 from pg_enum e
        join pg_type t on t.oid = e.enumtypid
       where t.typname = v_udt and e.enumlabel = 'rascunho'
    ) then
      execute format('alter type public.%I add value if not exists %L', v_udt, 'rascunho');
    end if;
    if not exists (
      select 1 from pg_enum e
        join pg_type t on t.oid = e.enumtypid
       where t.typname = v_udt and e.enumlabel = 'publicada'
    ) then
      execute format('alter type public.%I add value if not exists %L', v_udt, 'publicada');
    end if;
    if not exists (
      select 1 from pg_enum e
        join pg_type t on t.oid = e.enumtypid
       where t.typname = v_udt and e.enumlabel = 'removida'
    ) then
      execute format('alter type public.%I add value if not exists %L', v_udt, 'removida');
    end if;
  end if;
end $$;

create index if not exists idx_obras_compositor on public.obras(compositor_id);
create index if not exists idx_obras_status     on public.obras(status);
create index if not exists idx_obras_genero     on public.obras(genero);

-- ════════════════════════════════════════════════════════════════
-- 4. WALLETS
-- ════════════════════════════════════════════════════════════════
create table if not exists public.wallets (
  perfil_id  uuid primary key references public.perfis(id) on delete cascade
);
alter table public.wallets add column if not exists saldo_cents bigint      not null default 0;
alter table public.wallets add column if not exists updated_at  timestamptz not null default now();

-- ════════════════════════════════════════════════════════════════
-- 5. TRANSACOES
-- ════════════════════════════════════════════════════════════════
create table if not exists public.transacoes (
  id  uuid primary key default gen_random_uuid()
);
alter table public.transacoes add column if not exists obra_id      uuid;
alter table public.transacoes add column if not exists comprador_id uuid;
alter table public.transacoes add column if not exists vendedor_id  uuid;
alter table public.transacoes add column if not exists valor_cents  integer not null default 0;
alter table public.transacoes add column if not exists moeda        text    not null default 'BRL';
alter table public.transacoes add column if not exists provedor     text;
alter table public.transacoes add column if not exists provedor_ref text;
alter table public.transacoes add column if not exists status       text    not null default 'pendente';
alter table public.transacoes add column if not exists created_at   timestamptz not null default now();
alter table public.transacoes add column if not exists updated_at   timestamptz not null default now();

do $$
declare v_status text; v_prov text;
begin
  if not exists (select 1 from pg_constraint where conname='transacoes_obra_fk') then
    alter table public.transacoes add constraint transacoes_obra_fk
      foreign key (obra_id) references public.obras(id) on delete set null;
  end if;
  if not exists (select 1 from pg_constraint where conname='transacoes_comprador_fk') then
    alter table public.transacoes add constraint transacoes_comprador_fk
      foreign key (comprador_id) references public.perfis(id) on delete set null;
  end if;
  if not exists (select 1 from pg_constraint where conname='transacoes_vendedor_fk') then
    alter table public.transacoes add constraint transacoes_vendedor_fk
      foreign key (vendedor_id) references public.perfis(id) on delete set null;
  end if;

  select udt_name into v_prov   from information_schema.columns
   where table_schema='public' and table_name='transacoes' and column_name='provedor';
  select udt_name into v_status from information_schema.columns
   where table_schema='public' and table_name='transacoes' and column_name='status';

  if (v_prov = 'text' or v_prov is null)
     and not exists (select 1 from pg_constraint where conname='transacoes_provedor_check') then
    alter table public.transacoes add constraint transacoes_provedor_check
      check (provedor in ('stripe','paypal','manual') or provedor is null);
  end if;
  if (v_status = 'text' or v_status is null)
     and not exists (select 1 from pg_constraint where conname='transacoes_status_check') then
    alter table public.transacoes add constraint transacoes_status_check
      check (status in ('pendente','confirmada','reembolsada','cancelada','pago','revertido'));
  end if;
end $$;

create index if not exists idx_transacoes_obra      on public.transacoes(obra_id);
create index if not exists idx_transacoes_comprador on public.transacoes(comprador_id);
create index if not exists idx_transacoes_status    on public.transacoes(status);

-- ════════════════════════════════════════════════════════════════
-- 6. SAQUES
-- ════════════════════════════════════════════════════════════════
create table if not exists public.saques (
  id uuid primary key default gen_random_uuid()
);
alter table public.saques add column if not exists perfil_id    uuid;
alter table public.saques add column if not exists valor_cents  integer not null default 0;
alter table public.saques add column if not exists paypal_email text;
alter table public.saques add column if not exists status       text    not null default 'pendente';
alter table public.saques add column if not exists created_at   timestamptz not null default now();
alter table public.saques add column if not exists updated_at   timestamptz not null default now();

do $$
declare v_status text;
begin
  if not exists (select 1 from pg_constraint where conname='saques_perfil_fk') then
    alter table public.saques add constraint saques_perfil_fk
      foreign key (perfil_id) references public.perfis(id) on delete cascade;
  end if;
  select udt_name into v_status from information_schema.columns
   where table_schema='public' and table_name='saques' and column_name='status';
  if (v_status = 'text' or v_status is null)
     and not exists (select 1 from pg_constraint where conname='saques_status_check') then
    alter table public.saques add constraint saques_status_check
      check (status in ('pendente','enviado','pago','revertido','falhou'));
  end if;
end $$;

create index if not exists idx_saques_perfil on public.saques(perfil_id);
create index if not exists idx_saques_status on public.saques(status);

-- ════════════════════════════════════════════════════════════════
-- 7. OFERTAS
-- ════════════════════════════════════════════════════════════════
create table if not exists public.ofertas (
  id uuid primary key default gen_random_uuid()
);
alter table public.ofertas add column if not exists obra_id      uuid;
alter table public.ofertas add column if not exists comprador_id uuid;
alter table public.ofertas add column if not exists valor_cents  integer not null default 0;
alter table public.ofertas add column if not exists mensagem     text;
alter table public.ofertas add column if not exists status       text    not null default 'aberta';
alter table public.ofertas add column if not exists created_at   timestamptz not null default now();
alter table public.ofertas add column if not exists updated_at   timestamptz not null default now();

do $$
declare v_status text;
begin
  if not exists (select 1 from pg_constraint where conname='ofertas_obra_fk') then
    alter table public.ofertas add constraint ofertas_obra_fk
      foreign key (obra_id) references public.obras(id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname='ofertas_comprador_fk') then
    alter table public.ofertas add constraint ofertas_comprador_fk
      foreign key (comprador_id) references public.perfis(id) on delete cascade;
  end if;
  select udt_name into v_status from information_schema.columns
   where table_schema='public' and table_name='ofertas' and column_name='status';
  if (v_status = 'text' or v_status is null)
     and not exists (select 1 from pg_constraint where conname='ofertas_status_check') then
    alter table public.ofertas add constraint ofertas_status_check
      check (status in ('aberta','aceita','recusada','expirada','cancelada'));
  end if;
end $$;

create index if not exists idx_ofertas_obra      on public.ofertas(obra_id);
create index if not exists idx_ofertas_comprador on public.ofertas(comprador_id);

-- ════════════════════════════════════════════════════════════════
-- 8. COMENTARIOS
-- ════════════════════════════════════════════════════════════════
create table if not exists public.comentarios (
  id uuid primary key default gen_random_uuid()
);
alter table public.comentarios add column if not exists obra_id    uuid;
alter table public.comentarios add column if not exists perfil_id  uuid;
alter table public.comentarios add column if not exists texto      text;
alter table public.comentarios add column if not exists created_at timestamptz not null default now();

do $$
begin
  if not exists (select 1 from pg_constraint where conname='comentarios_obra_fk') then
    alter table public.comentarios add constraint comentarios_obra_fk
      foreign key (obra_id) references public.obras(id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname='comentarios_perfil_fk') then
    alter table public.comentarios add constraint comentarios_perfil_fk
      foreign key (perfil_id) references public.perfis(id) on delete cascade;
  end if;
end $$;

create index if not exists idx_comentarios_obra on public.comentarios(obra_id);

-- ════════════════════════════════════════════════════════════════
-- 9. PAGAMENTOS_COMPOSITORES
-- ════════════════════════════════════════════════════════════════
create table if not exists public.pagamentos_compositores (
  id uuid primary key default gen_random_uuid()
);
alter table public.pagamentos_compositores add column if not exists transacao_id       uuid;
alter table public.pagamentos_compositores add column if not exists perfil_id          uuid;
alter table public.pagamentos_compositores add column if not exists valor_cents        integer not null default 0;
alter table public.pagamentos_compositores add column if not exists status             text    not null default 'pendente';
alter table public.pagamentos_compositores add column if not exists stripe_transfer_id text;
alter table public.pagamentos_compositores add column if not exists created_at         timestamptz not null default now();
alter table public.pagamentos_compositores add column if not exists updated_at         timestamptz not null default now();

do $$
begin
  if not exists (select 1 from pg_constraint where conname='pgto_transacao_fk') then
    alter table public.pagamentos_compositores add constraint pgto_transacao_fk
      foreign key (transacao_id) references public.transacoes(id) on delete cascade;
  end if;
  if not exists (select 1 from pg_constraint where conname='pgto_perfil_fk') then
    alter table public.pagamentos_compositores add constraint pgto_perfil_fk
      foreign key (perfil_id) references public.perfis(id) on delete cascade;
  end if;
  if coalesce((select udt_name from information_schema.columns
                where table_schema='public' and table_name='pagamentos_compositores'
                  and column_name='status'), 'text') = 'text'
     and not exists (select 1 from pg_constraint where conname='pgto_status_check') then
    alter table public.pagamentos_compositores add constraint pgto_status_check
      check (status in ('pendente','enviado','pago','revertido'));
  end if;
end $$;

create index if not exists idx_pgto_transacao on public.pagamentos_compositores(transacao_id);
create index if not exists idx_pgto_perfil    on public.pagamentos_compositores(perfil_id);

-- ════════════════════════════════════════════════════════════════
-- 10. CONTATO_MENSAGENS
-- ════════════════════════════════════════════════════════════════
create table if not exists public.contato_mensagens (
  id uuid primary key default gen_random_uuid()
);
alter table public.contato_mensagens add column if not exists nome       text;
alter table public.contato_mensagens add column if not exists email      text;
alter table public.contato_mensagens add column if not exists assunto    text;
alter table public.contato_mensagens add column if not exists mensagem   text;
alter table public.contato_mensagens add column if not exists ip_hash    text;
alter table public.contato_mensagens add column if not exists created_at timestamptz not null default now();

-- ════════════════════════════════════════════════════════════════
-- 11. LANDING_CONTENT
--    Garante coluna `key` (chave única usada pelos seeds) mesmo que
--    a tabela já exista com outro layout.
-- ════════════════════════════════════════════════════════════════
create table if not exists public.landing_content (
  id bigserial primary key
);
alter table public.landing_content add column if not exists key        text;
alter table public.landing_content add column if not exists value      jsonb       not null default '{}'::jsonb;
alter table public.landing_content add column if not exists updated_at timestamptz not null default now();

-- Migra valores antigos de coluna "chave" → "key", se existir.
do $$
begin
  if exists (select 1 from information_schema.columns
              where table_schema='public' and table_name='landing_content' and column_name='chave') then
    update public.landing_content set key = chave where key is null;
  end if;
end $$;

-- Garante unique em "key" (necessário para os ON CONFLICT (key) dos seeds).
do $$
begin
  if not exists (select 1 from pg_constraint where conname='landing_content_key_unique') then
    -- só cria se não houver duplicatas
    if not exists (
      select key from public.landing_content
       where key is not null group by key having count(*) > 1
    ) then
      alter table public.landing_content
        add constraint landing_content_key_unique unique (key);
    end if;
  end if;
end $$;

-- ════════════════════════════════════════════════════════════════
-- 12. TRIGGER updated_at  (helper)
-- ════════════════════════════════════════════════════════════════
create or replace function public.tg_set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

do $$
declare t text;
begin
  for t in
    select unnest(array[
      'perfis','obras','transacoes','saques','ofertas',
      'pagamentos_compositores','wallets','landing_content'
    ])
  loop
    execute format(
      'drop trigger if exists tg_%1$s_updated_at on public.%1$s;
       create trigger tg_%1$s_updated_at before update on public.%1$s
       for each row execute function public.tg_set_updated_at();',
      t
    );
  end loop;
end $$;

-- ════════════════════════════════════════════════════════════════
-- 13. VIEWS DE BI
--     OBS: bi_auditoria_splits depende de obras_autores, criada em
--     migration_editora_agregados.sql. Por isso ela é criada dentro
--     de um do-block que checa a existência da tabela.
-- ════════════════════════════════════════════════════════════════
drop view if exists public.catalogo_publico       cascade;
drop view if exists public.bi_volume_transacional cascade;
drop view if exists public.bi_generos_populares   cascade;
drop view if exists public.bi_auditoria_splits    cascade;

create view public.catalogo_publico as
select
  o.id,
  o.nome,
  o.genero,
  o.bpm,
  o.preco_cents,
  o.capa_url,
  o.cover_url,
  o.audio_path,
  o.letra,
  o.letra_status,
  o.status,
  o.compositor_id,
  o.compositor_id                       as titular_id,
  p.nome_artistico                      as compositor_nome,
  coalesce(p.nome_artistico, p.nome)    as titular_nome,
  p.nivel                               as titular_nivel,
  p.avatar_url                          as titular_avatar_url,
  o.created_at
from public.obras o
left join public.perfis p on p.id = o.compositor_id
where o.status::text = 'publicada';

create view public.bi_volume_transacional as
select
  date_trunc('day', created_at)::date as dia,
  count(*)                            as total_transacoes,
  coalesce(sum(valor_cents), 0)       as volume_cents
from public.transacoes
where status::text = 'confirmada'
group by 1
order by 1 desc;

create view public.bi_generos_populares as
select
  o.genero,
  count(t.*)                          as vendas,
  coalesce(sum(t.valor_cents), 0)     as faturamento_cents
from public.obras o
left join public.transacoes t
       on t.obra_id = o.id and t.status::text = 'confirmada'
where o.genero is not null
group by o.genero
order by vendas desc nulls last;

do $$
begin
  if exists (
    select 1 from information_schema.tables
     where table_schema='public' and table_name='obras_autores'
  ) then
    execute $v$
      create view public.bi_auditoria_splits as
      select
        oa.obra_id,
        o.nome             as obra_nome,
        count(*)           as qtd_autores,
        sum(oa.share_pct)  as soma_splits
      from public.obras_autores oa
      join public.obras o on o.id = oa.obra_id
      group by oa.obra_id, o.nome
    $v$;
  end if;
end $$;

-- ════════════════════════════════════════════════════════════════
-- 14. RLS — habilita nas tabelas-base
--     (as policies em si são criadas em rls_security.sql)
-- ════════════════════════════════════════════════════════════════
alter table public.perfis                  enable row level security;
alter table public.obras                   enable row level security;
alter table public.transacoes              enable row level security;
alter table public.wallets                 enable row level security;
alter table public.saques                  enable row level security;
alter table public.ofertas                 enable row level security;
alter table public.comentarios             enable row level security;
alter table public.pagamentos_compositores enable row level security;
alter table public.contato_mensagens       enable row level security;
alter table public.landing_content         enable row level security;

-- ════════════════════════════════════════════════════════════════
-- 15. TRIGGER auto-criar perfil ao criar usuário no auth.users
-- ════════════════════════════════════════════════════════════════
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.perfis (id, email, nome, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'nome', split_part(new.email, '@', 1)),
    coalesce((new.raw_user_meta_data->>'role')::public.user_role, 'compositor')
  )
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists tg_on_auth_user_created on auth.users;
create trigger tg_on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- ════════════════════════════════════════════════════════════════
-- FIM. Próximo passo: rodar rls_security.sql e depois as migrações.
-- ════════════════════════════════════════════════════════════════


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 02/08  —  RLS — Row Level Security                               ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — Row Level Security (versão simplificada, 100% idempotente)
--
-- COMO EXECUTAR:
--   1. Acesse https://app.supabase.com/project/SEU_PROJETO/sql/new
--   2. Cole TODO este arquivo
--   3. Clique em RUN — pode rodar múltiplas vezes sem erro.
--
-- Este arquivo NÃO depende de funções customizadas, NÃO referencia
-- nenhuma tabela "Admin" maiúscula (erro 42P01). Cada bloco é
-- protegido por DO $$ ... IF EXISTS ... $$ e só executa se a tabela
-- realmente existir no banco — seguro para qualquer ambiente.
-- ══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 0. LIMPEZA LEGADA — remove policies/views/funções de migrações
-- antigas que referenciam "public.Admin" (tabela inexistente).
-- ────────────────────────────────────────────────────────────────
do $$
declare
  pol record;
  obj record;
begin
  for pol in
    select schemaname, tablename, policyname
      from pg_policies
     where qual like '%public.Admin%'
        or qual like '%"Admin"%'
        or with_check like '%public.Admin%'
        or with_check like '%"Admin"%'
  loop
    execute format('drop policy if exists %I on %I.%I',
                   pol.policyname, pol.schemaname, pol.tablename);
  end loop;

  for obj in
    select schemaname, viewname
      from pg_views
     where definition like '%public.Admin%' or definition like '%"Admin"%'
  loop
    execute format('drop view if exists %I.%I cascade', obj.schemaname, obj.viewname);
  end loop;

  for obj in
    select n.nspname as schemaname, p.proname as funcname,
           pg_get_function_identity_arguments(p.oid) as args
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.prokind = 'f'                -- só funções normais, não aggregates/windows
       and (pg_get_functiondef(p.oid) like '%public.Admin%'
            or pg_get_functiondef(p.oid) like '%"Admin"%')
  loop
    execute format('drop function if exists %I.%I(%s) cascade',
                   obj.schemaname, obj.funcname, obj.args);
  end loop;
end $$;

-- ────────────────────────────────────────────────────────────────
-- 1. perfis — usuário vê o próprio; admin (role='administrador') vê todos
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='perfis') then
    execute 'alter table public.perfis enable row level security';

    execute 'drop policy if exists "perfis_sel" on public.perfis';
    execute 'drop policy if exists "perfis_ins" on public.perfis';
    execute 'drop policy if exists "perfis_upd" on public.perfis';
    execute 'drop policy if exists "perfis_del" on public.perfis';

    execute $P$
      create policy "perfis_sel" on public.perfis for select
        using (auth.role() = 'authenticated')
    $P$;

    execute $P$
      create policy "perfis_ins" on public.perfis for insert
        with check (auth.uid() = id)
    $P$;

    execute $P$
      create policy "perfis_upd" on public.perfis for update
        using (
          auth.uid() = id
          or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
        )
    $P$;

    execute $P$
      create policy "perfis_del" on public.perfis for delete
        using (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
    $P$;

    execute 'revoke all on public.perfis from anon';
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 2. obras — publicadas são públicas; rascunhos só dono/admin
-- ────────────────────────────────────────────────────────────────
do $$
declare
  has_publicada boolean;
  has_compositor boolean;
  has_titular boolean;
  owner_col text;
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='obras') then
    execute 'alter table public.obras enable row level security';

    select exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='publicada') into has_publicada;
    select exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='compositor_id') into has_compositor;
    select exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='titular_id') into has_titular;

    owner_col := case when has_compositor then 'compositor_id' when has_titular then 'titular_id' else null end;

    execute 'drop policy if exists "obras_sel" on public.obras';
    execute 'drop policy if exists "obras_ins" on public.obras';
    execute 'drop policy if exists "obras_upd" on public.obras';
    execute 'drop policy if exists "obras_del" on public.obras';

    if owner_col is not null then
      execute format($P$
        create policy "obras_sel" on public.obras for select
          using (
            %s
            or auth.uid() = %I
            or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
          )
      $P$,
        case when has_publicada then 'coalesce(publicada, true) = true' else 'true' end,
        owner_col
      );

      execute format($P$
        create policy "obras_ins" on public.obras for insert
          with check (auth.uid() = %I)
      $P$, owner_col);

      execute format($P$
        create policy "obras_upd" on public.obras for update
          using (
            auth.uid() = %I
            or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
          )
      $P$, owner_col);

      execute format($P$
        create policy "obras_del" on public.obras for delete
          using (
            auth.uid() = %I
            or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
          )
      $P$, owner_col);
    end if;
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 3. wallets — só dono/admin
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='wallets') then
    execute 'alter table public.wallets enable row level security';

    execute 'drop policy if exists "wallets_sel" on public.wallets';
    execute 'drop policy if exists "wallets_all" on public.wallets';

    execute $P$
      create policy "wallets_sel" on public.wallets for select
        using (
          auth.uid() = perfil_id
          or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
        )
    $P$;

    execute $P$
      create policy "wallets_all" on public.wallets for all
        using (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
        with check (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
    $P$;

    execute 'revoke all on public.wallets from anon';
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 4. transacoes — só partes envolvidas/admin
-- ────────────────────────────────────────────────────────────────
do $$
declare
  owner_col text;
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='transacoes') then
    execute 'alter table public.transacoes enable row level security';
    execute 'drop policy if exists "trans_sel" on public.transacoes';

    select case
      when exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='compositor_id') then 'compositor_id'
      when exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='titular_id') then 'titular_id'
      else null
    end into owner_col;

    if owner_col is not null then
      execute format($P$
        create policy "trans_sel" on public.transacoes for select
          using (
            auth.uid() = comprador_id
            or auth.uid() in (select %I from public.obras where id = transacoes.obra_id)
            or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
          )
      $P$, owner_col);
    end if;

    execute 'revoke insert, update, delete on public.transacoes from anon, authenticated';
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 5. saques — só dono/admin
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='saques') then
    execute 'alter table public.saques enable row level security';

    execute 'drop policy if exists "saques_sel" on public.saques';
    execute 'drop policy if exists "saques_ins" on public.saques';
    execute 'drop policy if exists "saques_upd" on public.saques';

    execute $P$
      create policy "saques_sel" on public.saques for select
        using (
          auth.uid() = perfil_id
          or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
        )
    $P$;

    execute $P$
      create policy "saques_ins" on public.saques for insert
        with check (auth.uid() = perfil_id)
    $P$;

    execute $P$
      create policy "saques_upd" on public.saques for update
        using (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
    $P$;

    execute 'revoke all on public.saques from anon';
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 6. contato_mensagens — todos podem enviar; só admin lê
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='contato_mensagens') then
    execute 'alter table public.contato_mensagens enable row level security';

    execute 'drop policy if exists "contato_ins" on public.contato_mensagens';
    execute 'drop policy if exists "contato_sel" on public.contato_mensagens';

    execute $P$ create policy "contato_ins" on public.contato_mensagens for insert with check (true) $P$;

    execute $P$
      create policy "contato_sel" on public.contato_mensagens for select
        using (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
    $P$;

    execute 'revoke update, delete on public.contato_mensagens from anon, authenticated';
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 7. contratos_edicao — só titular do contrato/admin
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='contratos_edicao') then
    execute 'alter table public.contratos_edicao enable row level security';

    execute 'drop policy if exists "contratos_sel" on public.contratos_edicao';
    execute 'drop policy if exists "contratos_ins" on public.contratos_edicao';

    execute $P$
      create policy "contratos_sel" on public.contratos_edicao for select
        using (
          auth.uid() = titular_id
          or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
        )
    $P$;

    execute $P$
      create policy "contratos_ins" on public.contratos_edicao for insert
        with check (auth.uid() = titular_id)
    $P$;

    execute 'revoke update, delete on public.contratos_edicao from anon, authenticated';
    execute 'revoke all on public.contratos_edicao from anon';
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 8. coautorias — visualização por partes envolvidas
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='coautorias') then
    execute 'alter table public.coautorias enable row level security';
    execute 'drop policy if exists "coautorias_sel" on public.coautorias';

    execute $P$
      create policy "coautorias_sel" on public.coautorias for select
        using (
          auth.uid() = perfil_id
          or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
        )
    $P$;
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 9. landing_content — leitura pública, escrita só admin
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='landing_content') then
    execute 'alter table public.landing_content enable row level security';

    execute 'drop policy if exists "landing_sel" on public.landing_content';
    execute 'drop policy if exists "landing_all" on public.landing_content';

    execute $P$ create policy "landing_sel" on public.landing_content for select using (true) $P$;

    execute $P$
      create policy "landing_all" on public.landing_content for all
        using (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
        with check (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'))
    $P$;
  end if;
end $$;


-- ────────────────────────────────────────────────────────────────
-- 10. Catálogo público (view) — mantém legibilidade sem auth
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.views where table_schema='public' and table_name='catalogo_publico') then
    execute 'grant select on public.catalogo_publico to anon, authenticated';
  end if;
end $$;


-- ════════════════════════════════════════════════════════════════
-- 11. VERIFICAÇÃO — mostra RLS ativo + nº de policies por tabela
-- ════════════════════════════════════════════════════════════════
select
  tablename as tabela,
  rowsecurity as rls_ativo,
  (select count(*) from pg_policies where pg_policies.tablename = t.tablename) as policies
from pg_tables t
where schemaname = 'public'
  and tablename in (
    'perfis','obras','wallets','transacoes','saques',
    'contato_mensagens','contratos_edicao','coautorias','landing_content'
  )
order by tablename;


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 03/08  —  EDITORA + AGREGADOS + AUDIT_LOGS + CONTRATOS DE EDIÇÃO ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  
  -- ── PRE-PATCH defensivo (agente) ─────────────────────────────────────
  -- Reconcilia layouts antigo (id text PK, valor text) e novo (key, value jsonb)
  -- de public.landing_content para que ambos os INSERTs funcionem.
  do $$
  begin
    if not exists (select 1 from information_schema.tables
                    where table_schema='public' and table_name='landing_content') then
      create table public.landing_content (id bigserial primary key);
    end if;
  end $$;

  alter table public.landing_content add column if not exists key        text;
  alter table public.landing_content add column if not exists value      jsonb;
  alter table public.landing_content add column if not exists updated_at timestamptz not null default now();

  -- Torna colunas legadas (id text, valor text) opcionais e migra dados.
  do $$
  declare v_id_type text;
  begin
    select data_type into v_id_type from information_schema.columns
     where table_schema='public' and table_name='landing_content' and column_name='id';
    if v_id_type = 'text' then
      update public.landing_content set key = id where key is null and id is not null;
      begin alter table public.landing_content alter column id drop not null; exception when others then null; end;
    end if;

    if exists (select 1 from information_schema.columns
                where table_schema='public' and table_name='landing_content' and column_name='valor') then
      update public.landing_content set value = to_jsonb(valor)
       where value is null and valor is not null;
      begin alter table public.landing_content alter column valor drop not null; exception when others then null; end;
    end if;
  end $$;

  -- Garante unique em key (para ON CONFLICT (key))
  do $$
  begin
    if not exists (select 1 from pg_constraint where conname='landing_content_key_unique') then
      if not exists (select key from public.landing_content
                      where key is not null group by key having count(*) > 1) then
        alter table public.landing_content
          add constraint landing_content_key_unique unique (key);
      end if;
    end if;
  end $$;

  -- Trigger: sincroniza id↔key e valor↔value automaticamente, em ambos os sentidos.
  create or replace function public._lc_sync_legacy() returns trigger
  language plpgsql as $$
  declare has_id_text bool; has_valor bool;
  begin
    select (data_type='text') into has_id_text from information_schema.columns
     where table_schema='public' and table_name='landing_content' and column_name='id';
    select true into has_valor from information_schema.columns
     where table_schema='public' and table_name='landing_content' and column_name='valor';

    if coalesce(has_id_text,false) then
      if NEW.id  is null and NEW.key is not null then NEW.id  := NEW.key; end if;
      if NEW.key is null and NEW.id  is not null then NEW.key := NEW.id;  end if;
    end if;

    if coalesce(has_valor,false) then
      if NEW.valor is null and NEW.value is not null then
        NEW.valor := case jsonb_typeof(NEW.value)
                          when 'string' then NEW.value #>> '{}'
                          else NEW.value::text end;
      end if;
      if NEW.value is null and NEW.valor is not null then
        NEW.value := to_jsonb(NEW.valor);
      end if;
    end if;
    return NEW;
  end $$;

  drop trigger if exists _lc_sync_legacy on public.landing_content;
  drop trigger if exists _lc_sync_id_key on public.landing_content;
  create trigger _lc_sync_legacy before insert or update on public.landing_content
    for each row execute function public._lc_sync_legacy();
  -- ─────────────────────────────────────────────────────────────────────
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: EDITORA + AGREGADOS + AUDITORIA + CONTRATOS
--
-- Adiciona:
--   • Role 'publisher' (editora) em perfis
--   • Campos PJ da editora (razão social, CNPJ, responsável legal, etc.)
--   • Vínculo agregado→editora (publisher_id)
--   • Flag is_ghost (perfis criados sem senha, ativação pendente)
--   • Tabela obras_autores (split entre coautores, sempre igual)
--   • Coluna obras.letra (obrigatória) e obras.managed_by_publisher
--   • Tabela audit_logs (auditoria global)
--   • Tabela contracts_edicao (contrato de edição com fee)
--   • Seed: dados bancários GRAVAN e template editora em landing_content
--   • RLS para tudo
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 1. ROLE 'publisher' no enum user_role
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from pg_type where typname = 'user_role') then
    if not exists (
      select 1 from pg_enum e
      join pg_type t on t.oid = e.enumtypid
      where t.typname = 'user_role' and e.enumlabel = 'publisher'
    ) then
      alter type user_role add value 'publisher';
    end if;
  end if;
end $$;

-- ────────────────────────────────────────────────────────────────
-- 2. PERFIS — campos de editora + vínculo agregado + flag ghost
-- ────────────────────────────────────────────────────────────────
alter table public.perfis
  -- PJ Editora
  add column if not exists razao_social         text,
  add column if not exists nome_fantasia        text,
  add column if not exists cnpj                 text,  -- criptografado (PII)
  add column if not exists telefone             text,
  add column if not exists responsavel_nome     text,
  add column if not exists responsavel_cpf      text,  -- criptografado (PII)
  -- Vínculo agregado→editora
  add column if not exists publisher_id         uuid references public.perfis(id) on delete set null,
  add column if not exists agregado_desde       timestamptz,
  -- Ghost user (criado pela editora, ainda sem senha)
  add column if not exists is_ghost             boolean not null default false,
  add column if not exists ghost_invite_token   text,
  add column if not exists ghost_invite_sent_at timestamptz;

create index if not exists idx_perfis_publisher_id on public.perfis(publisher_id);
create index if not exists idx_perfis_cnpj         on public.perfis(cnpj);
create index if not exists idx_perfis_is_ghost     on public.perfis(is_ghost) where is_ghost = true;

comment on column public.perfis.publisher_id is
  'FK para perfis.id da editora à qual este artista está agregado. NULL = artista independente.';
comment on column public.perfis.is_ghost is
  'true quando perfil foi criado por uma editora sem senha — artista ainda precisa ativar conta via convite.';


-- ────────────────────────────────────────────────────────────────
-- 3. OBRAS — letra obrigatória + flag managed_by_publisher
-- ────────────────────────────────────────────────────────────────
alter table public.obras
  add column if not exists letra                text,
  add column if not exists managed_by_publisher boolean not null default false,
  add column if not exists publisher_id         uuid references public.perfis(id) on delete set null;

-- Letra: backfill obras antigas com '' e depois aplica NOT NULL
update public.obras set letra = '' where letra is null;
do $$
begin
  if not exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='obras'
      and column_name='letra' and is_nullable='NO'
  ) then
    alter table public.obras alter column letra set not null;
  end if;
end $$;

create index if not exists idx_obras_publisher on public.obras(publisher_id) where publisher_id is not null;

comment on column public.obras.letra is
  'Letra completa da obra (obrigatória no cadastro a partir de Abril/2026).';
comment on column public.obras.managed_by_publisher is
  'true quando a obra foi cadastrada por uma editora — ativa cláusula de fee 5% no contrato.';


-- ────────────────────────────────────────────────────────────────
-- 4. OBRAS_AUTORES — split entre coautores (sempre igual)
-- ────────────────────────────────────────────────────────────────
create table if not exists public.obras_autores (
  obra_id      uuid not null references public.obras(id) on delete cascade,
  perfil_id    uuid not null references public.perfis(id) on delete cascade,
  papel        text not null default 'coautor',
  share_pct    numeric(6,3) not null,
  is_principal boolean not null default false,
  created_at   timestamptz not null default now(),
  primary key (obra_id, perfil_id),
  constraint obras_autores_papel_check check (papel in ('autor','coautor'))
);

create index if not exists idx_obras_autores_obra   on public.obras_autores(obra_id);
create index if not exists idx_obras_autores_perfil on public.obras_autores(perfil_id);

comment on table public.obras_autores is
  'Vínculo obra↔autor com split. Para N autores, share_pct = 100/N (sempre igual). '
  'O resto da divisão é absorvido pelo is_principal=true.';


-- ────────────────────────────────────────────────────────────────
-- 5. AUDIT_LOGS — log global de ações
-- ────────────────────────────────────────────────────────────────
create table if not exists public.audit_logs (
  id           uuid primary key default gen_random_uuid(),
  user_id      uuid references public.perfis(id) on delete set null,
  action       text not null,
  entity_type  text not null,
  entity_id    uuid,
  metadata     jsonb not null default '{}'::jsonb,
  ip_hash      text,
  user_agent   text,
  created_at   timestamptz not null default now()
);

create index if not exists idx_audit_user      on public.audit_logs(user_id, created_at desc);
create index if not exists idx_audit_entity    on public.audit_logs(entity_type, entity_id, created_at desc);
create index if not exists idx_audit_action    on public.audit_logs(action, created_at desc);
create index if not exists idx_audit_created   on public.audit_logs(created_at desc);

comment on table public.audit_logs is
  'Log de auditoria global. Eventos: obra.criada, obra.editada, contrato.gerado, '
  'contrato.assinado, pagamento.recebido, usuario.cadastrado, admin.acao, etc.';


-- ────────────────────────────────────────────────────────────────
-- 6. CONTRACTS_EDICAO — contrato de edição (com cláusula de fee)
-- ────────────────────────────────────────────────────────────────
create table if not exists public.contracts_edicao (
  id               uuid primary key default gen_random_uuid(),
  obra_id          uuid not null references public.obras(id) on delete cascade,
  publisher_id     uuid not null references public.perfis(id) on delete restrict,
  autor_id         uuid not null references public.perfis(id) on delete restrict,
  share_pct        numeric(6,3) not null,
  contract_html    text not null,
  contract_text    text not null,
  has_fee_clause   boolean not null default true,
  conteudo_hash    text not null,
  status           text not null default 'pendente',
  versao           text not null default 'v1.0',
  signed_by_publisher_at timestamptz,
  signed_by_autor_at     timestamptz,
  publisher_ip_hash      text,
  autor_ip_hash          text,
  completed_at     timestamptz,
  created_at       timestamptz not null default now(),
  unique (obra_id, autor_id),
  constraint contracts_edicao_status_check
    check (status in ('pendente','assinado_parcial','assinado','cancelado'))
);

create index if not exists idx_contracts_edicao_obra      on public.contracts_edicao(obra_id);
create index if not exists idx_contracts_edicao_publisher on public.contracts_edicao(publisher_id);
create index if not exists idx_contracts_edicao_autor     on public.contracts_edicao(autor_id);
create index if not exists idx_contracts_edicao_status    on public.contracts_edicao(status);

comment on table public.contracts_edicao is
  'Contrato de Edição entre Editora e Autor (1 contrato por par obra×autor).';


-- ────────────────────────────────────────────────────────────────
-- 7. SEED — landing_content (template editora + dados bancários)
-- ────────────────────────────────────────────────────────────────
do $$
begin
  if exists (select 1 from information_schema.tables where table_schema='public' and table_name='landing_content') then

    -- Dados bancários da GRAVAN (editáveis via /admin/landing)
    insert into public.landing_content (key, value)
    values ('gravan_dados_bancarios', jsonb_build_object(
      'razao_social', 'GRAVAN',
      'cnpj',         '[PREENCHER]',
      'banco',        '[PREENCHER]',
      'agencia',      '[PREENCHER]',
      'conta',        '[PREENCHER]',
      'titular',      'GRAVAN'
    ))
    on conflict (key) do nothing;

    -- Template do contrato de edição com cláusula de fee
    -- (NÃO sobrescreve se já existir — admin pode editar via CMS)
    insert into public.landing_content (key, value)
    values ('contrato_edicao_publisher_template', to_jsonb(
'CONTRATO DE EDIÇÃO DE OBRAS MUSICAIS — EDITORA

Pelo presente instrumento particular, de um lado:

AUTOR: {{autor_nome}}, portador do RG nº {{autor_rg}}, inscrito no CPF/MF sob o nº {{autor_cpf}}, residente e domiciliado em {{autor_endereco}}, e-mail {{autor_email}}, doravante denominado "AUTOR";

e, de outro lado:

EDITORA: {{publisher_razao_social}} (nome fantasia: {{publisher_nome_fantasia}}), inscrita no CNPJ/MF sob o nº {{publisher_cnpj}}, com sede em {{publisher_endereco}}, neste ato representada por seu responsável legal {{publisher_responsavel_nome}}, CPF {{publisher_responsavel_cpf}}, doravante denominada "EDITORA";

AUTOR e EDITORA, em conjunto "PARTES", firmam o presente Contrato de Edição de Obras Musicais, mediante as cláusulas a seguir.

CONSIDERANDO QUE:
(i) o AUTOR é titular de {{share_autor_pct}}% dos direitos autorais sobre a obra "{{obra_nome}}", doravante "OBRA";
(ii) os demais coautores são: {{coautores_lista}};
(iii) a OBRA será gerida pela EDITORA por meio da plataforma GRAVAN.

CLÁUSULA PRIMEIRA — OBJETO
1.1 O AUTOR contrata com a EDITORA a edição musical de sua parte sobre a OBRA, em regime de exclusividade, sem limitação territorial, nos termos da Lei 9.610/1998.

1.2 Para todos os efeitos legais, integra o presente Contrato o CORPO DA OBRA, conforme cadastrado pelo AUTOR na plataforma GRAVAN, transcrito a seguir:

— CORPO DA OBRA "{{obra_nome}}" —
{{obra_letra}}
— FIM DO CORPO DA OBRA —

CLÁUSULA SEGUNDA — DIREITOS
2.1 Ficam sob a égide da EDITORA todos os direitos patrimoniais sobre a OBRA durante o prazo de proteção legal, em todos os países.
2.2 Ficam reservados ao AUTOR os direitos morais (art. 24 da Lei 9.610/1998).

CLÁUSULA TERCEIRA — ORIGINALIDADE
3.1 O AUTOR declara que a OBRA é de sua autoria/coautoria, livre de plágio e de contratos prévios.

CLÁUSULA QUARTA — REMUNERAÇÃO DO AUTOR
4.1 A EDITORA pagará ao AUTOR sobre as receitas líquidas relativas à parte do AUTOR na OBRA:
  (a) Sincronização: 70% AUTOR / 30% EDITORA;
  (b) Reprodução, distribuição digital, fonomecânicos: 75% AUTOR / 25% EDITORA;
  (c) Execução pública: 75% AUTOR / 25% EDITORA, paga diretamente ao AUTOR pela sociedade de autores.

CLÁUSULA QUINTA — REMUNERAÇÃO DA PLATAFORMA (FEE DE INTERMEDIAÇÃO EDITORIAL)
5.1 Em razão da utilização da plataforma GRAVAN e dos serviços de intermediação, gestão e disponibilização de obras musicais, a EDITORA concorda em pagar à GRAVAN o equivalente a 5% (cinco por cento) sobre todos os valores brutos recebidos pela EDITORA decorrentes da exploração econômica das obras cadastradas na plataforma.

Parágrafo Primeiro: O percentual incidirá sobre todas as receitas, incluindo, mas não se limitando a licenciamento, cessão de direitos, sincronização, distribuição digital e execução pública.

Parágrafo Segundo: O pagamento deverá ser realizado no prazo máximo de 30 (trinta) dias corridos contados do recebimento dos valores pela EDITORA.

Parágrafo Terceiro: O pagamento será feito diretamente à conta bancária da GRAVAN:
  Banco: {{gravan_banco}}
  Agência: {{gravan_agencia}}
  Conta: {{gravan_conta}}
  Titular: {{gravan_titular}}
  CNPJ: {{gravan_cnpj}}

Parágrafo Quarto: A EDITORA se compromete a manter registros financeiros e fornecer relatórios sempre que solicitado pela GRAVAN.

Parágrafo Quinto: O não pagamento dentro do prazo estipulado poderá resultar na suspensão da conta da EDITORA na plataforma e nas medidas legais cabíveis.

CLÁUSULA SEXTA — RESCISÃO
6.1 Este Contrato pode ser rescindido por qualquer das PARTES mediante notificação prévia de 90 (noventa) dias.

CLÁUSULA SÉTIMA — FORO
7.1 Fica eleito o foro da comarca da cidade do Rio de Janeiro/RJ.

ASSINATURAS ELETRÔNICAS
Este instrumento é firmado eletronicamente, com registro de data, hora, IP anonimizado (SHA-256) e hash de integridade. A aceitação eletrônica por cada parte configura assinatura válida e vinculante (MP 2.200-2/2001; Lei 14.063/2020).

Data de emissão: {{data_emissao}}
Hash SHA-256: {{conteudo_hash}}
'::text))
    on conflict (key) do nothing;

  end if;
end $$;


-- ════════════════════════════════════════════════════════════════
-- 8. RLS — Row Level Security
-- ════════════════════════════════════════════════════════════════

-- ─── obras_autores ──────────────────────────────────────────────
alter table public.obras_autores enable row level security;

drop policy if exists "obras_autores_sel" on public.obras_autores;
drop policy if exists "obras_autores_ins" on public.obras_autores;
drop policy if exists "obras_autores_upd" on public.obras_autores;
drop policy if exists "obras_autores_del" on public.obras_autores;

-- SELECT: autor da obra, coautor da obra, editora dona, ou admin
create policy "obras_autores_sel" on public.obras_autores for select
  using (
    auth.uid() = perfil_id
    or exists (select 1 from public.obras o where o.id = obras_autores.obra_id and o.compositor_id = auth.uid())
    or exists (select 1 from public.obras o where o.id = obras_autores.obra_id and o.publisher_id = auth.uid())
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

-- INSERT/UPDATE/DELETE: só dono da obra (compositor ou editora) ou admin
create policy "obras_autores_ins" on public.obras_autores for insert
  with check (
    exists (select 1 from public.obras o where o.id = obras_autores.obra_id and (o.compositor_id = auth.uid() or o.publisher_id = auth.uid()))
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

create policy "obras_autores_upd" on public.obras_autores for update
  using (
    exists (select 1 from public.obras o where o.id = obras_autores.obra_id and (o.compositor_id = auth.uid() or o.publisher_id = auth.uid()))
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

create policy "obras_autores_del" on public.obras_autores for delete
  using (
    exists (select 1 from public.obras o where o.id = obras_autores.obra_id and (o.compositor_id = auth.uid() or o.publisher_id = auth.uid()))
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );


-- ─── audit_logs ─────────────────────────────────────────────────
alter table public.audit_logs enable row level security;

drop policy if exists "audit_sel_self" on public.audit_logs;
drop policy if exists "audit_sel_admin" on public.audit_logs;
drop policy if exists "audit_ins_backend" on public.audit_logs;

-- Usuário vê os próprios logs
create policy "audit_sel_self" on public.audit_logs for select
  using (auth.uid() = user_id);

-- Admin vê tudo
create policy "audit_sel_admin" on public.audit_logs for select
  using (exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'));

-- INSERT só via service_role (backend) — RLS bloqueia anon/authenticated
revoke insert on public.audit_logs from anon, authenticated;


-- ─── contracts_edicao ───────────────────────────────────────────
alter table public.contracts_edicao enable row level security;

drop policy if exists "contracts_edicao_sel" on public.contracts_edicao;
drop policy if exists "contracts_edicao_upd" on public.contracts_edicao;

-- SELECT: autor, editora ou admin
create policy "contracts_edicao_sel" on public.contracts_edicao for select
  using (
    auth.uid() = autor_id
    or auth.uid() = publisher_id
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

-- UPDATE: só p/ assinar (autor ou editora)
create policy "contracts_edicao_upd" on public.contracts_edicao for update
  using (
    auth.uid() = autor_id
    or auth.uid() = publisher_id
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

-- INSERT só via backend (service_role)
revoke insert, delete on public.contracts_edicao from anon, authenticated;


-- ─── perfis: ajuste para editora poder ler perfis dos próprios agregados ──
do $$
begin
  if exists (select 1 from pg_policies where schemaname='public' and tablename='perfis' and policyname='perfis_publisher_sel_agregados') then
    drop policy "perfis_publisher_sel_agregados" on public.perfis;
  end if;
end $$;

create policy "perfis_publisher_sel_agregados" on public.perfis for select
  using (
    -- editora vê os perfis dos seus agregados
    publisher_id = auth.uid()
  );


-- ════════════════════════════════════════════════════════════════
-- 9. VERIFICAÇÃO FINAL
-- ════════════════════════════════════════════════════════════════
select 'enum publisher'        as item, exists (select 1 from pg_enum e join pg_type t on t.oid=e.enumtypid where t.typname='user_role' and e.enumlabel='publisher') as ok
union all select 'perfis.publisher_id',         exists (select 1 from information_schema.columns where table_schema='public' and table_name='perfis' and column_name='publisher_id')
union all select 'perfis.cnpj',                 exists (select 1 from information_schema.columns where table_schema='public' and table_name='perfis' and column_name='cnpj')
union all select 'perfis.is_ghost',             exists (select 1 from information_schema.columns where table_schema='public' and table_name='perfis' and column_name='is_ghost')
union all select 'obras.letra NOT NULL',        exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='letra' and is_nullable='NO')
union all select 'obras.managed_by_publisher',  exists (select 1 from information_schema.columns where table_schema='public' and table_name='obras' and column_name='managed_by_publisher')
union all select 'table obras_autores',         exists (select 1 from information_schema.tables  where table_schema='public' and table_name='obras_autores')
union all select 'table audit_logs',            exists (select 1 from information_schema.tables  where table_schema='public' and table_name='audit_logs')
union all select 'table contracts_edicao',      exists (select 1 from information_schema.tables  where table_schema='public' and table_name='contracts_edicao')
union all select 'seed gravan_dados_bancarios', exists (select 1 from public.landing_content where key='gravan_dados_bancarios')
union all select 'seed contrato_edicao_publisher_template', exists (select 1 from public.landing_content where key='contrato_edicao_publisher_template');


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 04/08  —  CONTRATOS DE LICENCIAMENTO                             ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: Contratos de Licenciamento + Assinatura digital
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


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 05/08  —  ASSINATURA / FAVORITOS / ANALYTICS                     ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: Sistema de Assinatura (STARTER / PRO) + Favoritos + Analytics
--
-- COMO EXECUTAR:
--   Cole TODO este arquivo no SQL Editor do Supabase e clique em RUN.
--   Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- ────────────────────────────────────────────────────────────────
-- 0. LIMPEZA LEGADA — remove policies/views/funções de migrações
-- antigas que referenciam "public.Admin" (tabela inexistente que
-- bloqueia novas alterações em `perfis`).
-- ────────────────────────────────────────────────────────────────
do $$
declare
  pol record;
  obj record;
begin
  -- Dropa TODAS as policies cujo definition menciona "Admin" (case-sensitive)
  for pol in
    select schemaname, tablename, policyname
      from pg_policies
     where qual like '%public.Admin%'
        or qual like '%"Admin"%'
        or with_check like '%public.Admin%'
        or with_check like '%"Admin"%'
  loop
    execute format('drop policy if exists %I on %I.%I',
                   pol.policyname, pol.schemaname, pol.tablename);
  end loop;

  -- Dropa views que mencionam Admin
  for obj in
    select schemaname, viewname
      from pg_views
     where definition like '%public.Admin%' or definition like '%"Admin"%'
  loop
    execute format('drop view if exists %I.%I cascade', obj.schemaname, obj.viewname);
  end loop;

  -- Dropa funções que mencionam Admin
  for obj in
    select n.nspname as schemaname, p.proname as funcname,
           pg_get_function_identity_arguments(p.oid) as args
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.prokind = 'f'                -- só funções normais, não aggregates/windows
       and (pg_get_functiondef(p.oid) like '%public.Admin%'
            or pg_get_functiondef(p.oid) like '%"Admin"%')
  loop
    execute format('drop function if exists %I.%I(%s) cascade',
                   obj.schemaname, obj.funcname, obj.args);
  end loop;
end $$;

-- ────────────────────────────────────────────────────────────────
-- 1. perfis — colunas de plano/assinatura
-- ────────────────────────────────────────────────────────────────
alter table public.perfis add column if not exists plano                  text    not null default 'STARTER';
alter table public.perfis add column if not exists status_assinatura      text    not null default 'inativa';
alter table public.perfis add column if not exists assinatura_inicio      timestamptz;
alter table public.perfis add column if not exists assinatura_fim         timestamptz;
alter table public.perfis add column if not exists stripe_customer_id     text;
alter table public.perfis add column if not exists stripe_subscription_id text;

-- Constraints (re-criam idempotentemente)
do $$ begin
  alter table public.perfis drop constraint if exists perfis_plano_check;
  alter table public.perfis add  constraint perfis_plano_check             check (plano in ('STARTER','PRO'));
  alter table public.perfis drop constraint if exists perfis_status_assinatura_check;
  alter table public.perfis add  constraint perfis_status_assinatura_check check (status_assinatura in ('ativa','inativa','cancelada','past_due'));
end $$;

create index if not exists idx_perfis_stripe_customer     on public.perfis (stripe_customer_id);
create index if not exists idx_perfis_stripe_subscription on public.perfis (stripe_subscription_id);

-- ────────────────────────────────────────────────────────────────
-- 2. favoritos (biblioteca pessoal)
-- ────────────────────────────────────────────────────────────────
create table if not exists public.favoritos (
  id          uuid primary key default gen_random_uuid(),
  perfil_id   uuid not null references public.perfis(id) on delete cascade,
  obra_id     uuid not null references public.obras(id)  on delete cascade,
  created_at  timestamptz not null default now(),
  unique (perfil_id, obra_id)
);

create index if not exists idx_favoritos_perfil on public.favoritos (perfil_id);
create index if not exists idx_favoritos_obra   on public.favoritos (obra_id);

-- ────────────────────────────────────────────────────────────────
-- 3. obra_analytics (agregado por obra) + play_events (cru)
-- ────────────────────────────────────────────────────────────────
create table if not exists public.obra_analytics (
  obra_id          uuid primary key references public.obras(id) on delete cascade,
  plays_count      int not null default 0,
  favorites_count  int not null default 0,
  last_played_at   timestamptz
);

create table if not exists public.play_events (
  id          uuid primary key default gen_random_uuid(),
  obra_id     uuid not null references public.obras(id) on delete cascade,
  perfil_id   uuid references public.perfis(id) on delete set null,
  ip_hash     text,
  created_at  timestamptz not null default now()
);

create index if not exists idx_play_events_obra on public.play_events (obra_id, created_at desc);

-- Triggers para manter obra_analytics atualizado
create or replace function public.fn_favoritos_inc()
returns trigger language plpgsql as $$
begin
  insert into public.obra_analytics (obra_id, favorites_count)
       values (new.obra_id, 1)
  on conflict (obra_id) do update set favorites_count = obra_analytics.favorites_count + 1;
  return new;
end $$;

create or replace function public.fn_favoritos_dec()
returns trigger language plpgsql as $$
begin
  update public.obra_analytics
     set favorites_count = greatest(favorites_count - 1, 0)
   where obra_id = old.obra_id;
  return old;
end $$;

drop trigger if exists trg_favoritos_inc on public.favoritos;
create trigger trg_favoritos_inc after insert on public.favoritos
  for each row execute function public.fn_favoritos_inc();

drop trigger if exists trg_favoritos_dec on public.favoritos;
create trigger trg_favoritos_dec after delete on public.favoritos
  for each row execute function public.fn_favoritos_dec();

create or replace function public.fn_play_events_inc()
returns trigger language plpgsql as $$
begin
  insert into public.obra_analytics (obra_id, plays_count, last_played_at)
       values (new.obra_id, 1, new.created_at)
  on conflict (obra_id) do update
     set plays_count    = obra_analytics.plays_count + 1,
         last_played_at = excluded.last_played_at;
  return new;
end $$;

drop trigger if exists trg_play_events_inc on public.play_events;
create trigger trg_play_events_inc after insert on public.play_events
  for each row execute function public.fn_play_events_inc();

-- ────────────────────────────────────────────────────────────────
-- 4. RLS nas novas tabelas
-- ────────────────────────────────────────────────────────────────
alter table public.favoritos      enable row level security;
alter table public.obra_analytics enable row level security;
alter table public.play_events    enable row level security;

-- favoritos: dono lê/escreve o próprio; admin vê tudo
drop policy if exists "favoritos_sel" on public.favoritos;
drop policy if exists "favoritos_ins" on public.favoritos;
drop policy if exists "favoritos_del" on public.favoritos;

create policy "favoritos_sel" on public.favoritos for select
  using (auth.uid() = perfil_id or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador'));
create policy "favoritos_ins" on public.favoritos for insert with check (auth.uid() = perfil_id);
create policy "favoritos_del" on public.favoritos for delete using (auth.uid() = perfil_id);

-- obra_analytics: dono da obra vê; público vê só contagens agregadas (via view)
drop policy if exists "analytics_sel_owner" on public.obra_analytics;
create policy "analytics_sel_owner" on public.obra_analytics for select
  using (
    exists (select 1 from public.obras o where o.id = obra_analytics.obra_id and o.titular_id = auth.uid())
    or exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );

-- play_events: ninguém lê via REST (apenas backend com service_role); insert liberado
drop policy if exists "play_events_ins" on public.play_events;
create policy "play_events_ins" on public.play_events for insert with check (true);

revoke all on public.play_events from anon, authenticated;
grant insert on public.play_events to anon, authenticated;

-- ────────────────────────────────────────────────────────────────
-- 5. VERIFICAÇÃO
-- ────────────────────────────────────────────────────────────────
select
  'perfis.plano'             as item, exists (select 1 from information_schema.columns where table_schema='public' and table_name='perfis' and column_name='plano')             as ok
union all select 'table favoritos',       exists (select 1 from information_schema.tables  where table_schema='public' and table_name='favoritos')
union all select 'table obra_analytics',  exists (select 1 from information_schema.tables  where table_schema='public' and table_name='obra_analytics')
union all select 'table play_events',     exists (select 1 from information_schema.tables  where table_schema='public' and table_name='play_events');


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 06/08  —  STRIPE CONNECT (payouts)                               ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
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


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 07/08  —  PATCH RLS PERFIS JOIN                                  ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — PATCH: ajusta RLS de `perfis` para permitir JOINs
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


  -- ╔══════════════════════════════════════════════════════════════════════╗
  -- ║  PASSO 08/08  —  SEED CONTRATO DE EDIÇÃO + DADOS BANCÁRIOS              ║
  -- ╚══════════════════════════════════════════════════════════════════════╝
  
  -- ── PRE-PATCH defensivo (agente) ─────────────────────────────────────
  -- Garante colunas (id, valor) usadas pelo seed abaixo.
  alter table public.landing_content add column if not exists id    text;
  alter table public.landing_content add column if not exists valor text;
  do $$
  begin
    if not exists (select 1 from pg_constraint where conname='landing_content_id_unique') then
      if not exists (select id from public.landing_content
                      where id is not null group by id having count(*) > 1) then
        alter table public.landing_content
          add constraint landing_content_id_unique unique (id);
      end if;
    end if;
  end $$;
  -- ─────────────────────────────────────────────────────────────────────
  -- ══════════════════════════════════════════════════════════════════
-- Gravan — Seed do template do "Contrato de Edição Musical"
--
-- COMO EXECUTAR:
--   1. Ajuste as variáveis abaixo (CNPJ, razão social, endereço da EDITORA)
--   2. Cole TODO este arquivo em https://app.supabase.com/project/SEU_PROJETO/sql/new
--   3. Clique em RUN.
--
-- Cria/atualiza 4 chaves em public.landing_content:
--   • contrato_edicao_template      — texto integral do contrato
--   • contrato_edicao_versao        — ex.: "v2.0 - Fev/2026"
--   • contrato_edicao_editora_dados — dados da EDITORA (CNPJ, endereço)
--   • contrato_edicao_foro          — foro (Comarca)
--
-- Placeholders substituídos em runtime (backend /api/obras POST):
--   {{nome_completo}} {{cpf}} {{rg}} {{endereco_completo}} {{email}}
--   {{data_assinatura}} {{obra_nome}} {{share_autor_pct}}
--   {{coautores_lista}} {{plataforma_razao_social}}
--   {{plataforma_cnpj}} {{plataforma_endereco}}
-- ══════════════════════════════════════════════════════════════════

create table if not exists public.landing_content (
  id    text primary key,
  valor text
);

-- 1. VERSÃO do contrato
insert into public.landing_content (id, valor) values
  ('contrato_edicao_versao', 'v2.0 - Fev/2026')
on conflict (id) do update set valor = excluded.valor;

-- 2. DADOS DA EDITORA (ajuste conforme seu CNPJ real)
insert into public.landing_content (id, valor) values
  ('contrato_edicao_editora_dados', 'GRAVAN EDITORA MUSICAL LTDA., inscrita no CNPJ/MF sob o nº 64.342.514/0001-08, com sede na Cidade do Rio de Janeiro, Estado do Rio de Janeiro')
on conflict (id) do update set valor = excluded.valor;

-- 3. FORO
insert into public.landing_content (id, valor) values
  ('contrato_edicao_foro', 'Comarca da Capital da Cidade do Rio de Janeiro, Estado do Rio de Janeiro')
on conflict (id) do update set valor = excluded.valor;

-- 4. TEMPLATE JURÍDICO COMPLETO
insert into public.landing_content (id, valor) values (
  'contrato_edicao_template',
$CT$CONTRATO DE EDIÇÃO DE OBRAS MUSICAIS E OUTRAS AVENÇAS

Pelo presente instrumento particular, de um lado:

AUTOR: {{nome_completo}}, portador do RG nº {{rg}}, inscrito no CPF/MF sob o nº {{cpf}}, residente e domiciliado em {{endereco_completo}}, e-mail {{email}}, doravante denominado "AUTOR";

e, de outro lado:

EDITORA: {{plataforma_razao_social}}, inscrita no CNPJ/MF sob o nº {{plataforma_cnpj}}, com sede em {{plataforma_endereco}}, doravante denominada "EDITORA";

AUTOR e EDITORA, doravante denominadas, em conjunto, "PARTES" e, individualmente, "PARTE", firmam entre si o presente Contrato de Edição de Obras Musicais e Outras Avenças, doravante denominado "Contrato", mediante as cláusulas e condições a seguir.

CONSIDERANDO QUE:
(i) o AUTOR é titular de {{share_autor_pct}}% (por cento) dos direitos autorais sobre a obra lítero-musical intitulada "{{obra_nome}}", doravante denominada "OBRA";
(ii) sendo os demais titulares/coautores: {{coautores_lista}};
(iii) a EDITORA, por meio da assinatura deste Contrato, tornar-se-á a editora musical e detentora dos direitos autorais patrimoniais sobre a parte do AUTOR na OBRA, observados os termos aqui previstos, nos moldes da Lei nº 9.610/1998 (Lei de Direitos Autorais).

CLÁUSULA PRIMEIRA — OBJETO

1.1 Por meio deste Contrato, o AUTOR (i) contrata com a EDITORA a edição musical de sua parte sobre a OBRA, com indicação do respectivo percentual de edição, em regime de absoluta exclusividade e sem qualquer limitação territorial; e (ii) outorga, desde logo, à EDITORA o direito único e exclusivo sobre o recebimento de qualquer valor decorrente das explorações comerciais havidas com a edição da OBRA pela EDITORA, na forma, extensão e aplicação em que os possui por força das Leis Brasileiras e Tratados Internacionais em vigor, e dos que vierem a vigorar no futuro, observadas as remunerações devidas ao AUTOR na forma da Cláusula Sexta.

1.2 O AUTOR desde já concorda e reconhece que a EDITORA poderá contratar com quaisquer outras editoras a administração das obras musicais e/ou lítero-musicais que integram ou venham a integrar o catálogo da EDITORA, incluindo a OBRA objeto deste Contrato, em relação ao que o AUTOR não se opõe.

CLÁUSULA SEGUNDA — DIREITOS

2.1 Pelo presente Contrato, ficam sob a égide da EDITORA, sem quaisquer limitações e durante todo o tempo de proteção legal dos direitos autorais e em todos os países do mundo, a totalidade dos direitos e faculdades que no seu conjunto constituem o direito autoral do AUTOR sobre a OBRA, em todos os seus aspectos, manifestações e aplicações diretas ou indiretas, processos de reprodução e divulgação ou extensões e ampliações, tais como, mas não limitados a: edição gráfica e fonomecânica em todas as suas formas, aplicações, sistemas e processos, quer atuais, quer os que venham a ser inventados ou aperfeiçoados no futuro; transcrição; adaptação; versões; variação; redução; execução; irradiação; distribuição física ou eletrônica, incluindo, mas não se limitando a download, streaming, ringtone, truetone, qualquer tipo de sincronização em suporte físico ou digital, existente ou que venha a existir, tais como televisão, VOD, adaptação e/ou inclusão cinematográfica, ou, ainda, em peças publicitárias, com a adaptação da letra e/ou melodia, em publicidade gráfica, sonora ou audiovisual, bem como qualquer forma de exploração, reprodução e divulgação da OBRA, incluindo sua execução pública, sem nenhuma exceção, mesmo que no futuro outras venham a ser as denominações da técnica ou da praxe, com todas as faculdades de exploração comercial e industrial necessárias para o exercício dos respectivos direitos, a exclusivo arbítrio da EDITORA. Serve o presente Contrato como título para que a EDITORA possa efetuar, onde lhe for útil ou conveniente, os registros e depósitos necessários para o irrestrito reconhecimento de seu direito, em todos os países do mundo, com faculdade de transferir os direitos ora adquiridos a terceiros, no todo ou em parte, a qualquer título.

2.2 Fica reservada ao AUTOR, na forma da lei, a integralidade dos direitos morais sobre sua parte na OBRA, nos termos do art. 24 da Lei nº 9.610/1998.

CLÁUSULA TERCEIRA — PROCURAÇÃO

3.1 Fica a EDITORA desde já constituída como bastante procuradora do AUTOR, com amplos e irrevogáveis poderes para que, em seu nome, possa defender e receber os direitos concernentes à OBRA.

CLÁUSULA QUARTA — ORIGINALIDADE

4.1 O AUTOR é exclusiva e pessoalmente responsável pela originalidade de sua parte sobre a OBRA, exonerando a EDITORA de toda e qualquer responsabilidade nesse sentido e obrigando-se a indenizá-la pelas perdas e danos que esta vier a sofrer em caso de contestação.

4.2 O AUTOR declara, sob as penas da lei, que a OBRA é de sua autoria (ou coautoria, conforme o caso), não constituindo plágio ou violação de direito autoral de terceiros, e que se encontra LIVRE e DESEMBARAÇADA de qualquer contrato de edição prévio com terceiros.

CLÁUSULA QUINTA — EDIÇÃO

5.1 A EDITORA, por este Contrato, obriga-se a editar, divulgar e expor à venda a OBRA, sendo certo que a tiragem de cada edição, o número de edições, a fixação da época, a determinação da forma e os detalhes de confecção artística, bem como o preço de venda ao público das edições, ficarão a exclusivo critério da EDITORA, que deverá envidar seus melhores esforços para consultar o AUTOR sobre valores das licenças, em especial na eventualidade de licenças sem ônus.

5.2 A EDITORA compromete-se a envidar seus melhores esforços para consultar o AUTOR sobre oportunidades de comercialização e uso da OBRA.

CLÁUSULA SEXTA — REMUNERAÇÃO

6.1 Pelo presente Contrato, a EDITORA obriga-se a pagar ao AUTOR os percentuais abaixo especificados, relativos às receitas líquidas efetivamente recebidas pela EDITORA pela exploração da OBRA, sempre incidentes sobre o percentual de direitos autorais do AUTOR sobre a OBRA, da seguinte forma:
  (a) Direitos de Sincronização e adaptação em produções audiovisuais, publicitárias ou não: 70% (setenta por cento) ao AUTOR e 30% (trinta por cento) à EDITORA;
  (b) Direitos de reprodução gráfica (edição); distribuição de direitos fonomecânicos; venda e locação de gravações sonoras; distribuição mediante meios óticos, cabo, satélites, redes de informação e rede local e/ou mundial de computadores que permitam ao usuário a seleção da obra ou que importe em pagamento pelo usuário; inclusão em base de dados ou qualquer forma de armazenamento; e demais modalidades previstas na Cláusula Segunda: 75% (setenta e cinco por cento) ao AUTOR e 25% (vinte e cinco por cento) à EDITORA;
  (c) Direitos de Execução Pública, observado o disposto na Cláusula 6.2: 75% (setenta e cinco por cento) ao AUTOR e 25% (vinte e cinco por cento) à EDITORA.

6.2 Os direitos de execução pública serão pagos ao AUTOR diretamente pela Sociedade de Autores a que este for filiado, sob sua exclusiva responsabilidade.

6.3 O AUTOR declara-se ciente e concorda expressamente que a EDITORA procederá à retenção proporcional do valor correspondente ao Imposto de Renda pago pela EDITORA sobre a remuneração recebida por esta pela exploração da OBRA, repassando ao AUTOR o montante líquido devido após a retenção.

CLÁUSULA SÉTIMA — DISPOSIÇÕES GERAIS

7.1 Este Contrato cancela e substitui qualquer acordo anterior firmado entre as PARTES, verbal ou escrito, referente ao mesmo objeto, obrigando as PARTES por si, seus herdeiros e sucessores.

7.2 Este Contrato poderá ser rescindido a qualquer tempo, por qualquer das PARTES, mediante notificação prévia e expressa com até 6 (seis) meses da efetiva rescisão. Toda e qualquer licença concedida durante a vigência, inclusive nos 6 (seis) meses seguintes à notificação, reputar-se-ão válidas e definitivas.

7.3 A EDITORA procederá trimestralmente, na conta bancária em nome do AUTOR indicada no cadastro da plataforma, à liquidação dos direitos eventualmente devidos ao AUTOR, mediante a transferência das receitas que lhe pertencem, acompanhada dos respectivos demonstrativos, mencionando a fonte pagadora, o período a que se refere o crédito, o título da OBRA e o valor de cada crédito, devendo efetuá-la dentro dos 60 (sessenta) dias posteriores ao fim de cada trimestre.

7.4 O AUTOR poderá, anualmente e em adição às prestações de contas descritas na Cláusula 7.3, requerer uma prestação de contas adicional, completa e consolidada referente ao exercício fiscal em curso.

7.5 O AUTOR assegura à EDITORA absoluta preferência, em igualdade de condições com propostas de terceiros, para a contratação de modalidades de exploração econômica da OBRA que, eventualmente, não tenham sido previstas neste Contrato, e para aquelas modalidades que venham a existir no futuro.

7.6 Este Contrato poderá ser cedido pela EDITORA a qualquer de suas associadas, coligadas ou filiadas, já existentes ou que venham a ser constituídas.

7.7 As PARTES elegem o foro da Comarca da Capital da Cidade do Rio de Janeiro, Estado do Rio de Janeiro, como único competente para dirimir eventuais controvérsias oriundas deste Contrato, com expressa renúncia a qualquer outro, por mais privilegiado que seja.

7.8 As PARTES declaram aceitar e reconhecer como válida, autêntica e verdadeira a comprovação da autoria e integridade deste documento realizada por meio eletrônico, nos termos da MP nº 2.200-2/2001, Lei nº 14.063/2020 e legislação correlata. A aceitação eletrônica do presente Contrato no ato do cadastro da OBRA na plataforma Gravan, com registro de data, hora, IP e hash SHA-256 do conteúdo, é considerada ASSINATURA VÁLIDA E VINCULANTE para todos os efeitos legais.

E, por estarem justas e acordadas, as PARTES firmam este instrumento eletronicamente na data abaixo:

Rio de Janeiro, {{data_assinatura}}.

___________________________________________
{{nome_completo}}
CPF: {{cpf}}
(AUTOR)

___________________________________________
{{plataforma_razao_social}}
CNPJ: {{plataforma_cnpj}}
(EDITORA)
$CT$
)
on conflict (id) do update set valor = excluded.valor;

-- Verificação
select id, length(valor) as tamanho from public.landing_content
where id like 'contrato_edicao%'
order by id;

