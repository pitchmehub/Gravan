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
