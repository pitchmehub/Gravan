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
