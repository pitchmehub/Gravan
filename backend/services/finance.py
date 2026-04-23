"""
Motor Financeiro do Pitch.me.

Todos os calculos sao realizados EXCLUSIVAMENTE aqui, no servidor.

Estrutura de receita (fee varia com o plano do TITULAR da obra):
  Titular STARTER: 20% plataforma | 80% compositores
  Titular PRO:     15% plataforma | 85% compositores
"""
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass

PLATFORM_RATE_STARTER = Decimal("0.20")  # 20%
PLATFORM_RATE_PRO     = Decimal("0.15")  # 15%


def fee_rate_for_plano(plano: str | None) -> Decimal:
    return PLATFORM_RATE_PRO if (plano or "").upper() == "PRO" else PLATFORM_RATE_STARTER


@dataclass
class SplitResult:
    valor_cents:         int
    plataforma_cents:    int
    liquido_cents:       int
    intermediacao_cents: int
    edicao_cents:        int
    payouts: list


def calcular_split(valor_cents: int, coautorias: list, plano_titular: str = "STARTER") -> SplitResult:
    if valor_cents <= 0:
        raise ValueError("Valor da venda deve ser positivo.")

    total_pct = sum(Decimal(str(c["share_pct"])) for c in coautorias)
    if total_pct != Decimal("100"):
        raise ValueError(
            f"A soma dos splits deve ser exatamente 100%. Recebido: {total_pct}%"
        )

    platform_rate = fee_rate_for_plano(plano_titular)
    v = Decimal(str(valor_cents))
    plataforma = (v * platform_rate).to_integral_value(ROUND_DOWN)
    liquido    = v - plataforma

    payouts = []
    distribuido = Decimal("0")

    for i, coautoria in enumerate(coautorias):
        pct = Decimal(str(coautoria["share_pct"]))
        if i == len(coautorias) - 1:
            valor_compositor = int(liquido - distribuido)
        else:
            valor_compositor = int(
                (liquido * pct / Decimal("100")).to_integral_value(ROUND_DOWN)
            )
            distribuido += Decimal(str(valor_compositor))

        payouts.append({
            "perfil_id":   coautoria["perfil_id"],
            "valor_cents": valor_compositor,
            "share_pct":   float(pct),
        })

    return SplitResult(
        valor_cents=valor_cents,
        plataforma_cents=int(plataforma),
        liquido_cents=int(liquido),
        intermediacao_cents=int(plataforma),
        edicao_cents=0,
        payouts=payouts,
    )


def validar_preco(preco_cents: int) -> None:
    if not isinstance(preco_cents, int) or preco_cents < 100:
        raise ValueError("Preco minimo: R$ 1,00 (100 centavos).")
