-- ══════════════════════════════════════════════════════════════════════
-- Gravan — HEALTHCHECK.SQL
--
-- Cole no SQL Editor do Supabase e clique RUN.
-- Retorna uma única tabela com o status de cada item esperado.
-- Coluna `ok` = true → tudo certo.  false → falta algo.
-- ══════════════════════════════════════════════════════════════════════

with checks as (

  -- ─── 1. Tabelas obrigatórias ────────────────────────────────────────
  select 'tabela: perfis'                  as item,
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='perfis') as ok
  union all select 'tabela: obras',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='obras')
  union all select 'tabela: obras_autores',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='obras_autores')
  union all select 'tabela: transacoes',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='transacoes')
  union all select 'tabela: contratos_edicao',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='contratos_edicao')
  union all select 'tabela: contratos_licenciamento',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='contratos_licenciamento')
  union all select 'tabela: assinaturas',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='assinaturas')
  union all select 'tabela: favoritos',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='favoritos')
  union all select 'tabela: stripe_connect_accounts',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='stripe_connect_accounts')
  union all select 'tabela: audit_logs',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='audit_logs')
  union all select 'tabela: landing_content',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='landing_content')
  union all select 'tabela: contato_mensagens',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='contato_mensagens')
  union all select 'tabela: coautorias',
         exists(select 1 from information_schema.tables
                 where table_schema='public' and table_name='coautorias')

  -- ─── 2. Colunas-chave ───────────────────────────────────────────────
  union all select 'coluna: landing_content.key',
         exists(select 1 from information_schema.columns
                 where table_schema='public' and table_name='landing_content' and column_name='key')
  union all select 'coluna: landing_content.value',
         exists(select 1 from information_schema.columns
                 where table_schema='public' and table_name='landing_content' and column_name='value')
  union all select 'coluna: obras.status',
         exists(select 1 from information_schema.columns
                 where table_schema='public' and table_name='obras' and column_name='status')
  union all select 'coluna: transacoes.provedor',
         exists(select 1 from information_schema.columns
                 where table_schema='public' and table_name='transacoes' and column_name='provedor')
  union all select 'coluna: transacoes.status',
         exists(select 1 from information_schema.columns
                 where table_schema='public' and table_name='transacoes' and column_name='status')

  -- ─── 3. Views ───────────────────────────────────────────────────────
  union all select 'view: catalogo_publico',
         exists(select 1 from information_schema.views
                 where table_schema='public' and table_name='catalogo_publico')
  union all select 'view: bi_volume_transacional',
         exists(select 1 from information_schema.views
                 where table_schema='public' and table_name='bi_volume_transacional')
  union all select 'view: bi_generos_populares',
         exists(select 1 from information_schema.views
                 where table_schema='public' and table_name='bi_generos_populares')
  union all select 'view: bi_auditoria_splits',
         exists(select 1 from information_schema.views
                 where table_schema='public' and table_name='bi_auditoria_splits')

  -- ─── 4. RLS habilitado ──────────────────────────────────────────────
  union all select 'rls: perfis',
         coalesce((select relrowsecurity from pg_class
                    where oid = 'public.perfis'::regclass), false)
  union all select 'rls: obras',
         coalesce((select relrowsecurity from pg_class
                    where oid = 'public.obras'::regclass), false)
  union all select 'rls: transacoes',
         coalesce((select relrowsecurity from pg_class
                    where oid = 'public.transacoes'::regclass), false)
  union all select 'rls: landing_content',
         coalesce((select relrowsecurity from pg_class
                    where oid = 'public.landing_content'::regclass), false)

  -- ─── 5. Seeds (landing_content) ─────────────────────────────────────
  union all select 'seed: gravan_dados_bancarios',
         exists(select 1 from public.landing_content where key='gravan_dados_bancarios')
  union all select 'seed: contrato_edicao_publisher_template',
         exists(select 1 from public.landing_content where key='contrato_edicao_publisher_template')
  union all select 'seed: contrato_edicao_template (legado)',
         exists(select 1 from public.landing_content
                 where key='contrato_edicao_template' or id='contrato_edicao_template')
  union all select 'seed: contrato_edicao_versao',
         exists(select 1 from public.landing_content
                 where key='contrato_edicao_versao' or id='contrato_edicao_versao')

  -- ─── 6. Storage bucket ──────────────────────────────────────────────
  union all select 'storage bucket: obras-audio',
         exists(select 1 from storage.buckets where id='obras-audio')
  union all select 'storage policies: obras-audio (>=4)',
         (select count(*) from pg_policies
           where schemaname='storage' and tablename='objects'
             and qual like '%obras-audio%') >= 4

  -- ─── 7. Pendências de preenchimento manual ──────────────────────────
  union all select 'dados bancários preenchidos (sem [PREENCHER])',
         not exists(
           select 1 from public.landing_content
            where key='gravan_dados_bancarios'
              and value::text like '%[PREENCHER]%'
         )
)
select
  case when ok then '✅ OK' else '❌ FALTA' end as status,
  item
from checks
order by ok asc, item asc;
