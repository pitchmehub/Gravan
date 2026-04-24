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