"""
Web Push (PWA) — envia notificações push para os dispositivos cadastrados
de um perfil. Usa VAPID via `pywebpush`.

Configuração via variáveis de ambiente (Replit Secrets):
  - VAPID_PUBLIC_KEY   (Base64URL — entregue ao navegador)
  - VAPID_PRIVATE_KEY  (Base64URL — secreto, fica só no servidor)
  - VAPID_SUBJECT      (mailto: ou https: — contato do app)
"""
import json
import logging
import os
from typing import Optional

from db.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def vapid_public_key() -> str:
    return (os.environ.get("VAPID_PUBLIC_KEY") or "").strip()


def _vapid_claims() -> dict:
    return {"sub": os.environ.get("VAPID_SUBJECT", "mailto:contato@gravan.app")}


def is_configured() -> bool:
    return bool(vapid_public_key()) and bool((os.environ.get("VAPID_PRIVATE_KEY") or "").strip())


def send_push(perfil_id: str, *,
              title: str, body: str = "",
              url: str = "/", tag: Optional[str] = None,
              data: Optional[dict] = None) -> int:
    """
    Envia um push para todos os dispositivos cadastrados do perfil.
    Retorna o número de envios bem-sucedidos. Nunca lança — só loga.
    """
    if not perfil_id:
        return 0
    if not is_configured():
        logger.info("[push] VAPID não configurado — pulando push para %s", perfil_id)
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except Exception as e:
        logger.warning("[push] pywebpush indisponível: %s", e)
        return 0

    sb = get_supabase()
    try:
        r = sb.table("push_subscriptions").select("*").eq("perfil_id", perfil_id).execute()
        subs = r.data or []
    except Exception as e:
        logger.warning("[push] falha buscando assinaturas: %s", e)
        return 0

    if not subs:
        return 0

    payload = json.dumps({
        "title": title,
        "body":  body,
        "url":   url,
        "tag":   tag or "gravan",
        "data":  data or {},
    })

    private_key = os.environ["VAPID_PRIVATE_KEY"].strip()
    enviados = 0
    a_remover: list[str] = []

    for s in subs:
        sub_info = {
            "endpoint": s["endpoint"],
            "keys": {"p256dh": s["p256dh"], "auth": s["auth_key"]},
        }
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims=_vapid_claims(),
            )
            enviados += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None) if getattr(e, "response", None) else None
            if status in (404, 410):
                a_remover.append(s["id"])
                logger.info("[push] endpoint inválido (%s) — removendo assinatura %s", status, s["id"])
            else:
                logger.warning("[push] falha (%s): %s", status, e)
        except Exception as e:
            logger.warning("[push] erro inesperado: %s", e)

    if a_remover:
        try:
            sb.table("push_subscriptions").delete().in_("id", a_remover).execute()
        except Exception as e:
            logger.warning("[push] falha removendo assinaturas inválidas: %s", e)

    if enviados:
        try:
            sb.table("push_subscriptions").update({"last_used_at": "now()"}) \
              .eq("perfil_id", perfil_id).execute()
        except Exception:
            pass

    return enviados
