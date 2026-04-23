-- ══════════════════════════════════════════════════════════════
  -- Pitch.me — PERFORMANCE IMPROVEMENTS
  --
  -- O que este script faz:
  --   1. Índices faltantes em chaves estrangeiras e colunas de filtro
  --   2. Índices compostos para as queries mais frequentes
  --   3. Índice de busca full-text em obras (nome + gênero)
  --   4. Índice parcial para obras publicadas (catálogo)
  --   5. View materializada para o catálogo público
  --   6. Função para atualizar a view materializada
  --
  -- EXECUTE NO SQL EDITOR DO SUPABASE.
  -- Idempotente — seguro rodar múltiplas vezes.
  -- ══════════════════════════════════════════════════════════════


  -- ────────────────────────────────────────────────────────────────
  -- 1. ÍNDICES FALTANTES — chaves estrangeiras sem índice
  -- ────────────────────────────────────────────────────────────────

  -- transacoes.vendedor_id (royalties do compositor)
  CREATE INDEX IF NOT EXISTS idx_transacoes_vendedor
    ON public.transacoes (vendedor_id);

  -- transacoes.created_at (consultas por período)
  CREATE INDEX IF NOT EXISTS idx_transacoes_created_at
    ON public.transacoes (created_at DESC);

  -- saques.perfil_id + status (histórico de saques)
  CREATE INDEX IF NOT EXISTS idx_saques_perfil
    ON public.saques (perfil_id);

  CREATE INDEX IF NOT EXISTS idx_saques_status
    ON public.saques (status);

  -- play_events.perfil_id (histórico de plays por usuário)
  CREATE INDEX IF NOT EXISTS idx_play_events_perfil
    ON public.play_events (perfil_id)
    WHERE perfil_id IS NOT NULL;

  -- contracts.status (contratos por status)
  CREATE INDEX IF NOT EXISTS idx_contracts_status
    ON public.contracts (status);

  -- contracts_edicao.completed_at (contratos finalizados)
  CREATE INDEX IF NOT EXISTS idx_contracts_edicao_completed
    ON public.contracts_edicao (completed_at DESC)
    WHERE completed_at IS NOT NULL;

  -- obras.created_at (obras recentes)
  CREATE INDEX IF NOT EXISTS idx_obras_created_at
    ON public.obras (created_at DESC);

  -- perfis.plano + status_assinatura (filtro de planos)
  CREATE INDEX IF NOT EXISTS idx_perfis_plano
    ON public.perfis (plano);

  CREATE INDEX IF NOT EXISTS idx_perfis_status_assinatura
    ON public.perfis (status_assinatura)
    WHERE status_assinatura = 'ativa';

  -- obra_analytics.plays_count (ranking de mais ouvidas)
  CREATE INDEX IF NOT EXISTS idx_obra_analytics_plays
    ON public.obra_analytics (plays_count DESC);

  CREATE INDEX IF NOT EXISTS idx_obra_analytics_favorites
    ON public.obra_analytics (favorites_count DESC);


  -- ────────────────────────────────────────────────────────────────
  -- 2. ÍNDICES COMPOSTOS — queries mais frequentes
  -- ────────────────────────────────────────────────────────────────

  -- "Minhas obras publicadas" → compositor filtra por status
  CREATE INDEX IF NOT EXISTS idx_obras_compositor_status
    ON public.obras (compositor_id, status);

  -- "Catálogo por gênero" → filtros combinados no catálogo
  CREATE INDEX IF NOT EXISTS idx_obras_status_genero
    ON public.obras (status, genero)
    WHERE status = 'publicada';

  -- "Minhas vendas confirmadas" → vendedor + status
  CREATE INDEX IF NOT EXISTS idx_transacoes_vendedor_status
    ON public.transacoes (vendedor_id, status);

  -- "Minhas compras confirmadas" → comprador + status
  CREATE INDEX IF NOT EXISTS idx_transacoes_comprador_status
    ON public.transacoes (comprador_id, status);

  -- "Artistas de uma editora" → publisher + role para agrupamentos
  CREATE INDEX IF NOT EXISTS idx_perfis_publisher_role
    ON public.perfis (publisher_id, role)
    WHERE publisher_id IS NOT NULL;

  -- "Obras de uma editora" → publisher + status
  CREATE INDEX IF NOT EXISTS idx_obras_publisher_status
    ON public.obras (publisher_id, status)
    WHERE publisher_id IS NOT NULL;


  -- ────────────────────────────────────────────────────────────────
  -- 3. BUSCA FULL-TEXT em obras (português)
  --    Permite: SELECT * FROM obras WHERE fts @@ to_tsquery('portuguese','samba')
  -- ────────────────────────────────────────────────────────────────

  -- Coluna gerada para full-text search
  ALTER TABLE public.obras
    ADD COLUMN IF NOT EXISTS fts tsvector
    GENERATED ALWAYS AS (
      to_tsvector('portuguese',
        COALESCE(nome, '') || ' ' ||
        COALESCE(genero, '')
      )
    ) STORED;

  -- Índice GIN na coluna gerada
  CREATE INDEX IF NOT EXISTS idx_obras_fts
    ON public.obras USING GIN (fts);

  -- Como usar no backend (Flask/Supabase):
  --   SELECT * FROM obras
  --   WHERE fts @@ plainto_tsquery('portuguese', 'samba amor')
  --     AND status = 'publicada'
  --   ORDER BY plays_count DESC;


  -- ────────────────────────────────────────────────────────────────
  -- 4. ÍNDICE PARCIAL — catálogo público (obras publicadas)
  --    Cobre ~80% das queries de usuários finais
  -- ────────────────────────────────────────────────────────────────
  CREATE INDEX IF NOT EXISTS idx_obras_catalogo_publico
    ON public.obras (genero, created_at DESC)
    WHERE status = 'publicada';


  -- ────────────────────────────────────────────────────────────────
  -- 5. VIEW MATERIALIZADA — catálogo com analytics
  --    Evita JOINs repetidos na listagem do catálogo
  -- ────────────────────────────────────────────────────────────────
  CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_catalogo AS
  SELECT
    o.id,
    o.nome,
    o.genero,
    o.bpm,
    o.capa_url,
    o.preco_cents,
    o.created_at,
    o.compositor_id,
    o.publisher_id,
    p.nome           AS compositor_nome,
    p.nome_artistico AS compositor_artistico,
    COALESCE(a.plays_count, 0)     AS plays_count,
    COALESCE(a.favorites_count, 0) AS favorites_count,
    a.last_played_at
  FROM public.obras o
  LEFT JOIN public.perfis        p ON p.id = o.compositor_id
  LEFT JOIN public.obra_analytics a ON a.obra_id = o.id
  WHERE o.status = 'publicada';

  -- Índice na view materializada
  CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_catalogo_id
    ON public.mv_catalogo (id);

  CREATE INDEX IF NOT EXISTS idx_mv_catalogo_genero
    ON public.mv_catalogo (genero);

  CREATE INDEX IF NOT EXISTS idx_mv_catalogo_plays
    ON public.mv_catalogo (plays_count DESC);

  CREATE INDEX IF NOT EXISTS idx_mv_catalogo_favorites
    ON public.mv_catalogo (favorites_count DESC);


  -- ────────────────────────────────────────────────────────────────
  -- 6. FUNÇÃO PARA ATUALIZAR A VIEW MATERIALIZADA
  --    Chame via cron job no Supabase ou após inserir/atualizar obras
  -- ────────────────────────────────────────────────────────────────
  CREATE OR REPLACE FUNCTION public.refresh_mv_catalogo()
  RETURNS void
  LANGUAGE sql
  SECURITY DEFINER
  AS $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_catalogo;
  $$;

  -- Trigger para atualizar a view quando uma obra muda de status
  CREATE OR REPLACE FUNCTION public.fn_obra_status_changed()
  RETURNS trigger
  LANGUAGE plpgsql
  AS $$
  BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status OR
       OLD.nome   IS DISTINCT FROM NEW.nome   OR
       OLD.genero IS DISTINCT FROM NEW.genero THEN
      PERFORM public.refresh_mv_catalogo();
    END IF;
    RETURN NEW;
  END;
  $$;

  DROP TRIGGER IF EXISTS trg_obra_refresh_catalogo ON public.obras;
  CREATE TRIGGER trg_obra_refresh_catalogo
    AFTER UPDATE ON public.obras
    FOR EACH ROW EXECUTE FUNCTION public.fn_obra_status_changed();


  -- ────────────────────────────────────────────────────────────────
  -- 7. VERIFICAÇÃO FINAL
  -- ────────────────────────────────────────────────────────────────
  SELECT
    schemaname,
    relname      AS tabela,
    indexrelname AS indice,
    pg_size_pretty(pg_relation_size(indexrelid)) AS tamanho
  FROM pg_stat_user_indexes
  WHERE schemaname = 'public'
  ORDER BY relname, indexrelname;
  