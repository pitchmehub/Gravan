-- ════════════════════════════════════════════════════════════════
-- Gravan — Migrações pendentes (rodar TUDO de uma vez)
-- Cole este arquivo inteiro no SQL Editor do Supabase e clique Run.
-- Todos os blocos são idempotentes (seguro rodar mais de uma vez).
-- Ordem: notificações → realtime → push → convites de agregado
-- ════════════════════════════════════════════════════════════════

-- ╔══════════════════════════════════════════════════════════════╗
-- ║  1/4  sql/01_criar_tabela_notificacoes.sql                   ║
-- ╚══════════════════════════════════════════════════════════════╝
-- ============================================================
-- Gravan — Sistema de notificações
-- Rodar no SQL Editor do Supabase
-- ============================================================

create table if not exists public.notificacoes (
  id           uuid primary key default gen_random_uuid(),
  perfil_id    uuid not null references public.perfis(id) on delete cascade,
  tipo         text not null,
  titulo       text not null,
  mensagem     text,
  link         text,
  payload      jsonb default '{}'::jsonb,
  lida         boolean not null default false,
  criada_em    timestamptz not null default now(),
  lida_em      timestamptz
);

create index if not exists idx_notif_perfil_lida_data
  on public.notificacoes (perfil_id, lida, criada_em desc);

alter table public.notificacoes enable row level security;

drop policy if exists "ler_proprias" on public.notificacoes;
create policy "ler_proprias" on public.notificacoes
  for select using (auth.uid() = perfil_id);

drop policy if exists "marcar_proprias" on public.notificacoes;
create policy "marcar_proprias" on public.notificacoes
  for update using (auth.uid() = perfil_id) with check (auth.uid() = perfil_id);

grant select, update on public.notificacoes to authenticated;

-- ╔══════════════════════════════════════════════════════════════╗
-- ║  2/4  backend/db/migration_realtime_notificacoes.sql         ║
-- ╚══════════════════════════════════════════════════════════════╝
-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: REALTIME para a tabela `notificacoes`
--
-- Habilita o Supabase Realtime na tabela `notificacoes` para que o
-- sino de notificações receba inserções/atualizações em tempo real,
-- sem precisar ficar pulsando o servidor a cada 30s.
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1) Adiciona a tabela na publicação `supabase_realtime`
do $$
begin
  if not exists (
    select 1
    from   pg_publication_tables
    where  pubname = 'supabase_realtime'
      and  schemaname = 'public'
      and  tablename  = 'notificacoes'
  ) then
    execute 'alter publication supabase_realtime add table public.notificacoes';
  end if;
end$$;

-- 2) Garante REPLICA IDENTITY FULL (envia row completo nos UPDATEs)
alter table public.notificacoes replica identity full;

-- 3) Confirma RLS — usuário só vê suas próprias notificações
alter table public.notificacoes enable row level security;

drop policy if exists "notif_owner_select" on public.notificacoes;
create policy "notif_owner_select" on public.notificacoes
  for select using (perfil_id = auth.uid());

drop policy if exists "notif_owner_update" on public.notificacoes;
create policy "notif_owner_update" on public.notificacoes
  for update using (perfil_id = auth.uid())
  with check (perfil_id = auth.uid());

drop policy if exists "notif_owner_delete" on public.notificacoes;
create policy "notif_owner_delete" on public.notificacoes
  for delete using (perfil_id = auth.uid());

-- ╔══════════════════════════════════════════════════════════════╗
-- ║  3/4  backend/db/migration_push_subscriptions.sql            ║
-- ╚══════════════════════════════════════════════════════════════╝
-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: WEB PUSH (PWA)
--
-- Cria a tabela `push_subscriptions` que armazena as assinaturas
-- de notificação push do navegador (VAPID) por perfil + device.
--
-- Cada navegador/dispositivo gera um endpoint único; o usuário pode
-- ter várias assinaturas simultâneas (celular, desktop, etc).
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

create table if not exists public.push_subscriptions (
  id            uuid primary key default gen_random_uuid(),
  perfil_id     uuid not null references public.perfis(id) on delete cascade,
  endpoint      text not null unique,
  p256dh        text not null,
  auth_key      text not null,
  user_agent    text,
  created_at    timestamptz not null default now(),
  last_used_at  timestamptz not null default now()
);

create index if not exists idx_push_subs_perfil on public.push_subscriptions(perfil_id);

comment on table public.push_subscriptions is
  'Assinaturas de Web Push (VAPID) por perfil. Cada navegador/dispositivo registra uma entrada única (endpoint).';

-- ────────────────────────────────────────────────────────────────
-- RLS — usuário só lê/edita suas próprias assinaturas; o backend
-- usa service_role para enviar pushes.
-- ────────────────────────────────────────────────────────────────
alter table public.push_subscriptions enable row level security;

drop policy if exists "push_subs_owner_select" on public.push_subscriptions;
create policy "push_subs_owner_select" on public.push_subscriptions
  for select using (perfil_id = auth.uid());

drop policy if exists "push_subs_owner_insert" on public.push_subscriptions;
create policy "push_subs_owner_insert" on public.push_subscriptions
  for insert with check (perfil_id = auth.uid());

drop policy if exists "push_subs_owner_delete" on public.push_subscriptions;
create policy "push_subs_owner_delete" on public.push_subscriptions
  for delete using (perfil_id = auth.uid());

-- ╔══════════════════════════════════════════════════════════════╗
-- ║  4/4  backend/db/migration_agregado_convites.sql             ║
-- ╚══════════════════════════════════════════════════════════════╝
-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: CONVITES DE AGREGADO (editora ↔ artista)
--
-- Cria a tabela `agregado_convites` que armazena:
--   • Convites pendentes (editora → artista) com termo jurídico anexado
--   • Modos: 'cadastrar' (artista ainda não existe / ghost) ou
--                       'adicionar' (artista já tem perfil — precisa aceitar)
--   • Status: pendente | aceito | recusado | cancelado | expirado
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

create table if not exists public.agregado_convites (
  id            uuid primary key default gen_random_uuid(),
  editora_id    uuid not null references public.perfis(id) on delete cascade,
  artista_id    uuid          references public.perfis(id) on delete cascade,
  email_artista text not null,
  modo          text not null check (modo in ('cadastrar','adicionar')),
  status        text not null default 'pendente'
                check (status in ('pendente','aceito','recusado','cancelado','expirado')),
  token         text not null unique default encode(gen_random_bytes(24),'hex'),

  -- Termo jurídico
  termo_html                  text not null,
  termo_versao                text not null default 'v1',
  responsavel_editora_nome    text,
  responsavel_editora_cpf_mask text,    -- ex.: "***.***.***-12" (último bloco)
  editora_aceito_em           timestamptz not null default now(),
  editora_aceito_ip           text,

  -- Aceite do artista
  termo_aceito_pelo_artista_em timestamptz,
  termo_aceito_ip             text,
  assinatura_artista_nome     text,

  decided_at  timestamptz,
  expires_at  timestamptz not null default (now() + interval '30 days'),
  created_at  timestamptz not null default now()
);

create index if not exists idx_agconvites_editora  on public.agregado_convites(editora_id);
create index if not exists idx_agconvites_artista  on public.agregado_convites(artista_id);
create index if not exists idx_agconvites_email    on public.agregado_convites(lower(email_artista));
create index if not exists idx_agconvites_status   on public.agregado_convites(status);

-- Garante que não existam dois convites pendentes da mesma editora pro mesmo email
create unique index if not exists uq_agconvites_pendente_por_email
  on public.agregado_convites(editora_id, lower(email_artista))
  where status = 'pendente';

comment on table public.agregado_convites is
  'Convites de agregação editora→artista. Cada convite carrega um termo jurídico imutável que ambas partes assinam digitalmente.';

-- ────────────────────────────────────────────────────────────────
-- RLS
-- ────────────────────────────────────────────────────────────────
alter table public.agregado_convites enable row level security;

drop policy if exists "ag_convites_editora_select" on public.agregado_convites;
create policy "ag_convites_editora_select" on public.agregado_convites
  for select using (editora_id = auth.uid());

drop policy if exists "ag_convites_editora_insert" on public.agregado_convites;
create policy "ag_convites_editora_insert" on public.agregado_convites
  for insert with check (editora_id = auth.uid());

drop policy if exists "ag_convites_editora_cancelar" on public.agregado_convites;
create policy "ag_convites_editora_cancelar" on public.agregado_convites
  for update using (editora_id = auth.uid())
  with check (editora_id = auth.uid());

drop policy if exists "ag_convites_artista_select" on public.agregado_convites;
create policy "ag_convites_artista_select" on public.agregado_convites
  for select using (
    artista_id = auth.uid()
    or lower(email_artista) = (select lower(email) from public.perfis where id = auth.uid())
  );

drop policy if exists "ag_convites_artista_decidir" on public.agregado_convites;
create policy "ag_convites_artista_decidir" on public.agregado_convites
  for update using (
    artista_id = auth.uid()
    or lower(email_artista) = (select lower(email) from public.perfis where id = auth.uid())
  )
  with check (
    artista_id = auth.uid()
    or lower(email_artista) = (select lower(email) from public.perfis where id = auth.uid())
  );

-- Admin tem acesso total (RLS bypass via role)
drop policy if exists "ag_convites_admin_all" on public.agregado_convites;
create policy "ag_convites_admin_all" on public.agregado_convites
  for all using (
    exists (select 1 from public.perfis p where p.id = auth.uid() and p.role = 'administrador')
  );
