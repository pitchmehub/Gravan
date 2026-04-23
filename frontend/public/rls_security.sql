-- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Row Level Security (versão simplificada, 100% idempotente)
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
