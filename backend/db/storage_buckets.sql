-- ══════════════════════════════════════════════════════════════════
-- Gravan — Storage: bucket de áudio das obras
--
-- COMO EXECUTAR:
--   Cole no SQL Editor do Supabase e clique RUN.
--   Idempotente — seguro rodar várias vezes.
-- ══════════════════════════════════════════════════════════════════

-- 1. Cria o bucket (privado). Tamanho máx por arquivo = 10 MB.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'obras-audio', 'obras-audio', false,
  10 * 1024 * 1024,
  array['audio/mpeg','audio/mp3']
)
on conflict (id) do update
  set public             = excluded.public,
      file_size_limit    = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- 2. Policies — só usuários autenticados podem upar/ler/deletar
--    seus próprios arquivos (path começa com o auth.uid()).

drop policy if exists "obras-audio insert auth"  on storage.objects;
drop policy if exists "obras-audio select auth"  on storage.objects;
drop policy if exists "obras-audio delete owner" on storage.objects;
drop policy if exists "obras-audio update owner" on storage.objects;

create policy "obras-audio insert auth"
on storage.objects for insert to authenticated
with check (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "obras-audio select auth"
on storage.objects for select to authenticated
using (bucket_id = 'obras-audio');

create policy "obras-audio update owner"
on storage.objects for update to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);

create policy "obras-audio delete owner"
on storage.objects for delete to authenticated
using (
  bucket_id = 'obras-audio'
  and (storage.foldername(name))[1] = auth.uid()::text
);
