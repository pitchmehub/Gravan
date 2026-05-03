-- ============================================================
-- MIGRATION: débito atômico de wallet + constraint saldo >= 0
-- Executar no Supabase SQL Editor (uma vez)
-- ============================================================

-- 1. Garante que saldo_cents nunca fique negativo no banco.
--    Isso é a última linha de defesa independente de qualquer código.
ALTER TABLE public.wallets
  ADD CONSTRAINT wallets_saldo_nao_negativo
  CHECK (saldo_cents >= 0);

-- 2. Função atômica para DEBITAR a wallet.
--    Usa SELECT ... FOR UPDATE para garantir exclusão mútua por linha:
--    se dois saques do mesmo perfil rodarem em paralelo, o segundo
--    ficará bloqueado até o primeiro terminar (e então verá o saldo
--    já decrementado, falhando corretamente).
--
--    Retorna: { ok: true, novo_saldo: N }
--          ou { ok: false, erro: "mensagem" }
CREATE OR REPLACE FUNCTION public.debitar_wallet(
  p_perfil_id   uuid,
  p_valor_cents bigint,
  p_saque_id    uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_saldo bigint;
BEGIN
  -- Bloqueia a linha da wallet para este perfil (exclusão mútua real).
  -- Qualquer outra transação que tente debitar o mesmo perfil
  -- ficará esperando aqui até esta transação terminar.
  SELECT saldo_cents
    INTO v_saldo
    FROM public.wallets
   WHERE perfil_id = p_perfil_id
     FOR UPDATE;

  IF NOT FOUND THEN
    RETURN jsonb_build_object(
      'ok',   false,
      'erro', 'Carteira não encontrada para este perfil.'
    );
  END IF;

  IF v_saldo < p_valor_cents THEN
    RETURN jsonb_build_object(
      'ok',   false,
      'erro', format(
        'Saldo insuficiente: %s centavos disponíveis, %s solicitados.',
        v_saldo, p_valor_cents
      )
    );
  END IF;

  -- Decrementa atomicamente.
  UPDATE public.wallets
     SET saldo_cents = saldo_cents - p_valor_cents,
         updated_at  = now()
   WHERE perfil_id = p_perfil_id;

  RETURN jsonb_build_object(
    'ok',         true,
    'novo_saldo', v_saldo - p_valor_cents
  );
END;
$$;

-- 3. Garante que creditar_wallet também é atômica (upsert seguro).
--    Se já existir → incrementa. Se não existir → cria com o valor.
CREATE OR REPLACE FUNCTION public.creditar_wallet(
  p_perfil_id    uuid,
  p_valor_cents  bigint,
  p_transacao_id uuid DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_novo bigint;
BEGIN
  INSERT INTO public.wallets (perfil_id, saldo_cents)
  VALUES (p_perfil_id, p_valor_cents)
  ON CONFLICT (perfil_id)
  DO UPDATE SET
    saldo_cents = wallets.saldo_cents + EXCLUDED.saldo_cents,
    updated_at  = now()
  RETURNING saldo_cents INTO v_novo;

  RETURN jsonb_build_object('ok', true, 'novo_saldo', v_novo);
END;
$$;

-- 4. Revoga acesso público às funções (só SECURITY DEFINER via service_role).
REVOKE ALL ON FUNCTION public.debitar_wallet(uuid, bigint, uuid)  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.creditar_wallet(uuid, bigint, uuid) FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON FUNCTION public.debitar_wallet(uuid, bigint, uuid)  TO service_role;
GRANT  EXECUTE ON FUNCTION public.creditar_wallet(uuid, bigint, uuid) TO service_role;
