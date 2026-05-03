-- Gravan — Corrige mínimo de preço de R$ 500 para R$ 50
-- Aplique via Supabase SQL Editor se precisar recriar.
-- Já aplicado em produção em Mai/2026.

CREATE OR REPLACE FUNCTION public.validar_preco_por_nivel()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_plano text;
  v_status text;
BEGIN
  SELECT plano, status_assinatura
    INTO v_plano, v_status
    FROM public.perfis
   WHERE id = NEW.titular_id
   LIMIT 1;

  IF NEW.preco_cents < 50000 THEN
    RAISE EXCEPTION 'Valor minimo de licenciamento: R$ 500,00';
  END IF;

  IF v_plano = 'PRO' AND v_status IN ('ativa', 'cancelada', 'past_due') THEN
    IF NEW.preco_cents > 1000000 THEN
      RAISE EXCEPTION 'Valor maximo (PRO): R$ 10.000,00';
    END IF;
  ELSE
    IF NEW.preco_cents > 100000 THEN
      RAISE EXCEPTION 'Plano PRO necessario para precos acima de R$ 1.000,00';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;
