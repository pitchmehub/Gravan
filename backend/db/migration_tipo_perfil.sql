-- ══════════════════════════════════════════════════════════
  -- Gravan — MIGRATION: Torna role nullable (sem default)
  --
  -- OBJETIVO: Garantir que novos usuários tenham role = NULL
  -- até escolherem explicitamente ARTISTA ou EDITORA na tela
  -- EscolherTipoPerfil, após o primeiro login.
  --
  -- EXECUTE NO SQL EDITOR DO SUPABASE antes de fazer deploy.
  -- ══════════════════════════════════════════════════════════

  -- 1. Remove o default automático 'compositor'
  ALTER TABLE public.perfis
    ALTER COLUMN role DROP DEFAULT;

  -- 2. Remove a restrição NOT NULL (permite role = NULL para novos usuários)
  ALTER TABLE public.perfis
    ALTER COLUMN role DROP NOT NULL;

  -- 3. Garante que o tipo user_role aceita os valores necessários
  --    (publisher já deve existir via migration_editora_agregados)
  DO $$
  BEGIN
    IF NOT EXISTS (
      SELECT 1 FROM pg_enum e
      JOIN pg_type t ON t.oid = e.enumtypid
      WHERE t.typname = 'user_role' AND e.enumlabel = 'publisher'
    ) THEN
      ALTER TYPE public.user_role ADD VALUE IF NOT EXISTS 'publisher';
    END IF;
  END $$;

  -- 4. Recria (ou substitui) o trigger que cria o perfil no primeiro login.
  --    NÃO seta role automaticamente — deixa NULL para a tela de seleção.
  CREATE OR REPLACE FUNCTION public.handle_new_user()
  RETURNS trigger
  LANGUAGE plpgsql
  SECURITY DEFINER SET search_path = public
  AS $$
  BEGIN
    INSERT INTO public.perfis (id, email, nome, role)
    VALUES (
      NEW.id,
      NEW.email,
      COALESCE(
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'name',
        split_part(NEW.email, '@', 1)
      ),
      NULL   -- role sempre NULL: o usuário escolhe em EscolherTipoPerfil
    )
    ON CONFLICT (id) DO NOTHING;

    -- Cria wallet zerada
    INSERT INTO public.wallets (perfil_id, saldo_cents)
    VALUES (NEW.id, 0)
    ON CONFLICT (perfil_id) DO NOTHING;

    RETURN NEW;
  END;
  $$;

  -- Garante que o trigger está ativo em auth.users
  DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
  CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
  