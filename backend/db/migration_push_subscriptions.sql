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
