-- ══════════════════════════════════════════════════════════════════
-- Gravan — Migração: HISTÓRICO DE BUSCAS (global)
--
-- Registra cada termo buscado por qualquer usuário para que a barra
-- de busca da Descoberta possa sugerir as buscas mais recentes
-- feitas por todos os perfis.
--
-- Idempotente — seguro rodar múltiplas vezes.
-- ══════════════════════════════════════════════════════════════════

create table if not exists public.historico_buscas (
  id          uuid        primary key default gen_random_uuid(),
  perfil_id   uuid        references public.perfis(id) on delete set null,
  query       text        not null check (length(trim(query)) between 1 and 120),
  criada_em   timestamptz not null default now()
);

create index if not exists idx_historico_buscas_criada_em
  on public.historico_buscas (criada_em desc);

create index if not exists idx_historico_buscas_query_lower
  on public.historico_buscas (lower(query));

alter table public.historico_buscas enable row level security;

-- Qualquer usuário autenticado pode ler todo o histórico (é global).
drop policy if exists "hb_auth_select" on public.historico_buscas;
create policy "hb_auth_select" on public.historico_buscas
  for select to authenticated
  using (true);

-- Usuário só pode inserir registro vinculado ao próprio perfil_id
-- (ou nulo, p/ casos de buscas anônimas).
drop policy if exists "hb_auth_insert" on public.historico_buscas;
create policy "hb_auth_insert" on public.historico_buscas
  for insert to authenticated
  with check (perfil_id is null or perfil_id = auth.uid());
