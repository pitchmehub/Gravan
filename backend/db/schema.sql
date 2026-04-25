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
