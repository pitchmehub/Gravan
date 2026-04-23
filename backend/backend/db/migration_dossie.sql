-- ═════════════════════════════════════════════════════════════════
-- Migration: tabela `dossies` + bucket de storage `dossies`
-- Pitch.me — Dossiê da Obra (Master Package)
--
-- IMPORTANTE
--   contrato_id referencia `contratos_edicao` (contrato assinado ao
--   cadastrar a obra — routes/obras.py).
--   NÃO confundir com `contracts_edicao` (editoras externas).
--
-- IDEMPOTENTE — pode rodar mais de uma vez sem quebrar.
-- ═════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────
-- 1. Tabela principal
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dossies (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    obra_id       UUID        NOT NULL REFERENCES obras(id)            ON DELETE CASCADE,
    contrato_id   UUID        REFERENCES contratos_edicao(id)          ON DELETE SET NULL,
    gerado_por    UUID        REFERENCES perfis(id)                    ON DELETE SET NULL,
    storage_path  TEXT        NOT NULL,
    hash_sha256   TEXT        NOT NULL,
    titulo_obra   TEXT        NOT NULL DEFAULT '',
    metadata      JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────
-- 2. Corrige FK antiga (contracts_edicao → contratos_edicao)
-- ─────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name      = 'dossies'
          AND constraint_name = 'dossies_contrato_id_fkey'
    ) THEN
        ALTER TABLE dossies DROP CONSTRAINT dossies_contrato_id_fkey;
        ALTER TABLE dossies ADD CONSTRAINT dossies_contrato_id_fkey
            FOREIGN KEY (contrato_id)
            REFERENCES contratos_edicao(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- ─────────────────────────────────────────────────────────────────
-- 3. Índices para consultas comuns + busca
-- ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS dossies_obra_id_idx     ON dossies(obra_id);
CREATE INDEX IF NOT EXISTS dossies_gerado_por_idx  ON dossies(gerado_por);
CREATE INDEX IF NOT EXISTS dossies_created_at_idx  ON dossies(created_at DESC);

-- Tenta habilitar pg_trgm para acelerar a busca por título.
-- Se a extensão não estiver disponível (ou se não houver permissão),
-- segue sem o índice — a busca funciona, só fica menos otimizada.
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;

    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    ) THEN
        EXECUTE
            'CREATE INDEX IF NOT EXISTS dossies_titulo_obra_idx '
            'ON dossies USING gin (titulo_obra gin_trgm_ops)';
    END IF;
END $$;

-- ═════════════════════════════════════════════════════════════════
-- 4. Row Level Security (RLS)
-- ═════════════════════════════════════════════════════════════════
ALTER TABLE dossies ENABLE ROW LEVEL SECURITY;

-- Reset idempotente
DROP POLICY IF EXISTS "admin_all_dossies"     ON dossies;
DROP POLICY IF EXISTS "titular_select_dossie" ON dossies;
DROP POLICY IF EXISTS "editora_select_dossie" ON dossies;

-- 4.1 Administrador → acesso total
CREATE POLICY "admin_all_dossies"
    ON dossies FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM perfis
            WHERE perfis.id = auth.uid()
              AND perfis.role = 'administrador'
        )
    );

-- 4.2 Titular da obra → SELECT
CREATE POLICY "titular_select_dossie"
    ON dossies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM obras
            WHERE obras.id         = dossies.obra_id
              AND obras.titular_id = auth.uid()
        )
    );

-- 4.3 Editora vinculada (via contracts_edicao) → SELECT
--     Usa um EXISTS condicional: se a tabela contracts_edicao não
--     existir nesta instalação, a policy simplesmente nunca casa
--     (não dá erro de catálogo).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'contracts_edicao'
    ) THEN
        EXECUTE $POL$
            CREATE POLICY "editora_select_dossie"
                ON dossies FOR SELECT
                USING (
                    EXISTS (
                        SELECT 1 FROM contracts_edicao
                        WHERE contracts_edicao.obra_id      = dossies.obra_id
                          AND contracts_edicao.publisher_id = auth.uid()
                    )
                )
        $POL$;
    END IF;
END $$;

-- ═════════════════════════════════════════════════════════════════
-- 5. Storage bucket "dossies"  (privado)
-- ═════════════════════════════════════════════════════════════════
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'dossies',
    'dossies',
    false,
    104857600,                                       -- 100 MB
    ARRAY['application/zip', 'application/octet-stream']
)
ON CONFLICT (id) DO UPDATE
    SET public          = EXCLUDED.public,
        file_size_limit = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Policies do bucket (privado — acesso somente via API autenticada)
DROP POLICY IF EXISTS "dossies storage insert" ON storage.objects;
DROP POLICY IF EXISTS "dossies storage select" ON storage.objects;
DROP POLICY IF EXISTS "dossies storage update" ON storage.objects;
DROP POLICY IF EXISTS "dossies storage delete" ON storage.objects;

CREATE POLICY "dossies storage insert"
    ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'dossies');

CREATE POLICY "dossies storage select"
    ON storage.objects FOR SELECT TO authenticated
    USING (bucket_id = 'dossies');

CREATE POLICY "dossies storage update"
    ON storage.objects FOR UPDATE TO authenticated
    USING (bucket_id = 'dossies')
    WITH CHECK (bucket_id = 'dossies');

CREATE POLICY "dossies storage delete"
    ON storage.objects FOR DELETE TO authenticated
    USING (bucket_id = 'dossies');
