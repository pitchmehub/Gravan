-- ══════════════════════════════════════════════════════════════════
-- Pitch.me — Migration: Storage de avatar e capa do perfil
--
-- O QUE FAZ:
--   1. Garante a coluna `capa_url` na tabela public.perfis
--   2. (Re)Cria buckets `avatares` e `capas` com config correta
--   3. (Re)Cria todas as policies de RLS para upload/leitura/edição/
--      remoção pelo dono do arquivo (path = <auth.uid()>/qualquercoisa)
--
-- POR QUE PRECISA RODAR:
--   - A política antiga do bucket `avatares` não permitia UPDATE,
--     então atualizar uma foto já enviada quebrava com:
--     "new row violates row-level security policy"
--   - O bucket `capas` ainda não existia.
--
-- COMO EXECUTAR:
--   Cole no SQL Editor do Supabase e clique RUN.
--   Idempotente — seguro rodar várias vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1. Coluna capa_url ------------------------------------------------
alter table public.perfis
  add column if not exists capa_url text;

-- 2. Buckets --------------------------------------------------------
-- 2a. avatares (público, foto de perfil, máx 2 MB)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'avatares', 'avatares', true,
  2 * 1024 * 1024,
  array['image/jpeg','image/png','image/webp']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- 2b. capas (público, foto de capa estilo Spotify, máx 5 MB)
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

-- 3. Policies do bucket `avatares` ---------------------------------
drop policy if exists "avatares insert auth"   on storage.objects;
drop policy if exists "avatares select public" on storage.objects;
drop policy if exists "avatares update owner"  on storage.objects;
drop policy if exists "avatares delete owner"  on storage.objects;

create policy "avatares insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "avatares select public"
on storage.objects for select to public
using (bucket_id = 'avatares');

create policy "avatares update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "avatares delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'avatares'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- 4. Policies do bucket `capas` ------------------------------------
drop policy if exists "capas insert auth"   on storage.objects;
drop policy if exists "capas select public" on storage.objects;
drop policy if exists "capas update owner"  on storage.objects;
drop policy if exists "capas delete owner"  on storage.objects;

create policy "capas insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "capas select public"
on storage.objects for select to public
using (bucket_id = 'capas');

create policy "capas update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "capas delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'capas'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- ══════════════════════════════════════════════════════════════════
-- ✅ Pronto. Agora dá pra subir e atualizar avatar e capa do perfil.
-- ══════════════════════════════════════════════════════════════════
