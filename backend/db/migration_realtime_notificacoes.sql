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
