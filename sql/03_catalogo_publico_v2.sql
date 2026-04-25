-- =====================================================================
-- Migração: catalogo_publico v2
-- Data: 2026-04-25
-- =====================================================================
-- A view antiga só expunha capa_url (legacy) e não trazia cover_url
-- (gerado pela IA), audio_path nem letra. Por isso, na aba Descoberta
-- as capas geradas e a letra transcrita não apareciam, e o botão "play"
-- não aparecia mesmo havendo áudio.
--
-- Esta migração recria a view trazendo todas as colunas necessárias
-- pro front-end (Descoberta, busca, biblioteca, ficha técnica).
-- Também adiciona o alias titular_nome (compatibilidade com o front).
-- =====================================================================

DROP VIEW IF EXISTS public.catalogo_publico CASCADE;

CREATE VIEW public.catalogo_publico AS
SELECT
  o.id,
  o.nome,
  o.genero,
  o.bpm,
  o.preco_cents,
  o.capa_url,
  o.cover_url,
  o.audio_path,
  o.letra,
  o.letra_status,
  o.status,
  o.compositor_id,
  o.compositor_id            AS titular_id,
  p.nome_artistico           AS compositor_nome,
  COALESCE(p.nome_artistico, p.nome) AS titular_nome,
  p.nivel                    AS titular_nivel,
  p.avatar_url               AS titular_avatar_url,
  o.created_at
FROM public.obras o
LEFT JOIN public.perfis p ON p.id = o.compositor_id
WHERE o.status::text = 'publicada';

GRANT SELECT ON public.catalogo_publico TO anon, authenticated;
