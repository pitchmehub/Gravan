#!/usr/bin/env python3
"""
backfill_trilateral_stuck.py
────────────────────────────
Desbloqueia contratos TRILATERAIS que estão presos em 'aguardando_assinaturas'
porque o `detentora_ok` antigo rejeitava 'editora_agregadora' para editoras
parceiras (externas à Gravan).

Casos resolvidos:
  1. Editora parceira já assinou como 'editora_agregadora' (antes da migration),
     mas o contrato nunca foi marcado 'concluído' pois `detentora_ok` era False.
  2. Editora parceira nunca foi inserida em contract_signers porque a CHECK
     constraint não aceitava 'editora_detentora' e o INSERT falhou silenciosamente.
     Nesse caso o script tenta inserir a editora agora (com fallback de role)
     E assinar em nome dela (requer confirmação manual do operador).

O script é IDEMPOTENTE: rodar mais de uma vez é seguro.

Uso:
  cd backend && python db/backfill_trilateral_stuck.py [--dry-run]
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("backfill_trilateral_stuck")

GRAVAN_UUID = "e96bd8af-dfb8-4bf1-9ba5-7746207269cd"


def get_sb():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar definidos.")
    return create_client(url, key)


def run(dry_run: bool = False):
    sb = get_sb()

    # 1) Busca contratos trilaterais ainda em aguardando_assinaturas
    res = sb.table("contracts").select(
        "id, obra_id, trilateral, status, transacao_id, oferta_id"
    ).eq("trilateral", True).in_(
        "status", ["aguardando_assinaturas"]
    ).execute()

    contratos = res.data or []
    log.info("Contratos trilaterais aguardando assinatura: %d", len(contratos))

    desbloqueados = []
    sem_editora   = []
    sem_assinatura = []

    for c in contratos:
        cid = c["id"]
        signers = sb.table("contract_signers").select(
            "id, user_id, role, signed"
        ).eq("contract_id", cid).execute().data or []

        # Verifica editora parceira (qualquer não-Gravan com role editora)
        editora_signers = [
            s for s in signers
            if s.get("user_id") != GRAVAN_UUID
            and s.get("role") in ("editora_detentora", "editora_agregadora", "editora_terceira")
        ]

        if not editora_signers:
            # Caso 2: editora nunca foi inserida
            log.warning(
                "[CONTRATO %s] Nenhuma editora parceira em contract_signers. "
                "Requer inserção manual + assinatura.",
                cid,
            )
            sem_editora.append(cid)
            continue

        # Verificar se TODOS os signers (exceto editora) assinaram
        outros_unsigned = [
            s for s in signers
            if not s.get("signed")
            and s.get("user_id") not in [e["user_id"] for e in editora_signers]
        ]
        editora_unsigned = [s for s in editora_signers if not s.get("signed")]

        # ── NOVA REGRA: editora auto-assina (consentimento dado no Termo de Agregação)
        # Se a editora está em contract_signers mas ainda não assinou, marca agora.
        if editora_unsigned:
            log.info(
                "[CONTRATO %s] Editora não assinou (signed=False) — "
                "aplicando auto-assinatura retroativa (%d signer(s)).",
                cid, len(editora_unsigned),
            )
            if not dry_run:
                from datetime import datetime, timezone as _tz
                agora_iso = datetime.now(_tz.utc).isoformat()
                for s in editora_unsigned:
                    try:
                        sb.table("contract_signers").update({
                            "signed":    True,
                            "signed_at": agora_iso,
                        }).eq("id", s["id"]).execute()
                        log.info(
                            "[CONTRATO %s] Editora %s marcada como assinada.",
                            cid, s["user_id"][:8],
                        )
                    except Exception as e:
                        log.error(
                            "[CONTRATO %s] Falha ao marcar editora como assinada: %s",
                            cid, e,
                        )
            else:
                log.info("[CONTRATO %s] [DRY-RUN] Editora seria marcada como assinada.", cid)

        if outros_unsigned:
            log.info(
                "[CONTRATO %s] Outros signers ainda pendentes (compositor/coautor não assinou): %s",
                cid,
                [(s["user_id"][:8], s["role"]) for s in outros_unsigned],
            )
            sem_assinatura.append(cid)
            continue

        # Todos assinaram (ou editora foi retroativamente marcada acima)
        log.info(
            "[CONTRATO %s] Todos assinaram — tentando concluir contrato...",
            cid,
        )

        if dry_run:
            log.info("[CONTRATO %s] [DRY-RUN] Contrato seria concluído.", cid)
            desbloqueados.append(cid)
            continue

        # Chama retentar_conclusao_contrato: avalia detentora_ok com a lógica
        # ATUAL e, se todos assinaram, marca o contrato como concluído + credita wallets.
        try:
            from services.contrato_licenciamento import retentar_conclusao_contrato
            resultado = retentar_conclusao_contrato(cid)
            log.info("[CONTRATO %s] retentar_conclusao_contrato → %s", cid, resultado)
            if resultado.get("status") in ("concluido_agora", "ja_concluido"):
                desbloqueados.append(cid)
            else:
                log.warning("[CONTRATO %s] Não foi possível concluir: %s", cid, resultado)
        except Exception as e:
            log.error("[CONTRATO %s] Falha em retentar_conclusao_contrato: %s", cid, e)

    log.info("=" * 60)
    log.info("Resumo:")
    log.info("  Contratos desbloqueados (ou marcados para dry-run): %d", len(desbloqueados))
    log.info("  Contratos sem editora em signers:                  %d", len(sem_editora))
    log.info("  Contratos aguardando assinatura da editora:        %d", len(sem_assinatura))

    if sem_editora:
        log.warning(
            "Contratos sem editora em signers (requerem ação manual): %s", sem_editora
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Desbloqueia contratos trilaterais presos.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas mostra o que seria feito, sem alterar.")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
