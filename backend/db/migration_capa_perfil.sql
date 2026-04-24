-- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Migration: foto de capa do perfil (estilo Spotify)
--
-- O QUE FAZ:
--   1. Adiciona coluna `capa_url` na tabela public.perfis
--   2. Cria o bucket público `capas` no Storage (capa de perfil)
--   3. Cria policies de RLS para upload/leitura/deleção da capa
--
-- COMO EXECUTAR:
--   Cole no SQL Editor do Supabase e clique RUN.
--   Idempotente — seguro rodar várias vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1. Coluna capa_url ------------------------------------------------
alter table public.perfis
  add column if not exists capa_url text;

-- 2. Bucket público `capas` ----------------------------------------
--    Limite por arquivo = 5 MB. Conteúdo é capa de perfil.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'capas', 'capas', true,
  5 * 1024 * 1024,
  array['image/jpeg','image/png','image/webp']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- 3. Policies do bucket capas --------------------------------------
drop policy if exists "capas insert auth"   on storage.objects;
drop policy if exists "capas select public" on storage.objects;
drop policy if exists "capas update owner"  on storage.objects;
drop policy if exists "capas delete owner"  on storage.objects;

-- Insert: usuário autenticado, path começa com seu auth.uid()
create policy "capas insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- Select: público (qualquer pessoa pode ver capa de perfil)
create policy "capas select public"
on storage.objects for select to public
using (bucket_id = 'capas');

-- Update: dono do arquivo
create policy "capas update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- Delete: dono do arquivo
create policy "capas delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- ══════════════════════════════════════════════════════════════════
-- ✅ Pronto. Agora a edição de perfil aceita upload de foto de capa
--    e a página pública /perfil/:id mostra o layout estilo Spotify.
-- ══════════════════════════════════════════════════════════════════
