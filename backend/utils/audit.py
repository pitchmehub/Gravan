"""
Sistema de auditoria global. Registra eventos críticos em audit_logs.

Uso:
    from utils.audit import log_event
    log_event("obra.criada", entity_type="obra", entity_id=obra_id, metadata={"titulo": "X"})
"""
import hashlib
import logging
from typing import Any, Optional
from flask import g, request, has_request_context

from db.supabase_client import get_supabase

log = logging.getLogger(__name__)


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()[:32]


def log_event(
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Grava um evento na tabela audit_logs. Falhas são silenciosas (não derrubam a request).

    Eventos sugeridos:
        obra.criada, obra.editada, obra.removida
        contrato.gerado, contrato.assinado, contrato.cancelado
        pagamento.recebido, pagamento.repassado
        usuario.cadastrado, usuario.editado, usuario.ghost_criado
        agregado.vinculado, agregado.removido
        admin.acao
    """
    try:
        sb = get_supabase()
        uid = user_id
        ip = None
        ua = None
        if has_request_context():
            uid = uid or getattr(g, "user_id", None)
            ip = request.headers.get("X-Forwarded-For", request.remote_addr)
            ua = (request.headers.get("User-Agent") or "")[:500]

        sb.table("audit_logs").insert({
            "user_id":     uid,
            "action":      action,
            "entity_type": entity_type,
            "entity_id":   entity_id,
            "metadata":    metadata or {},
            "ip_hash":     _hash_ip(ip),
            "user_agent":  ua,
        }).execute()
    except Exception as e:
        log.warning("audit log failed: action=%s entity=%s err=%s", action, entity_type, e)


def list_events(
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Lista eventos. Use com filtros pra evitar trazer tudo."""
    sb = get_supabase()
    q = sb.table("audit_logs").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        q = q.eq("user_id", user_id)
    if entity_type:
        q = q.eq("entity_type", entity_type)
    if entity_id:
        q = q.eq("entity_id", entity_id)
    r = q.execute()
    return r.data or []

class AuditLogger:
    """
    Wrapper de classe para log_event, com métodos prontos para os eventos
    mais usados no sistema. Todos os métodos são estáticos.
    """

    @staticmethod
    def log_obra_criada(obra_id, nome):
        log_event(
            "obra.criada",
            entity_type="obra",
            entity_id=str(obra_id) if obra_id is not None else None,
            metadata={"nome": nome},
        )

    @staticmethod
    def log_compra(transacao_id, obra_id, valor_cents):
        log_event(
            "pagamento.recebido",
            entity_type="transacao",
            entity_id=str(transacao_id) if transacao_id is not None else None,
            metadata={
                "obra_id": str(obra_id) if obra_id is not None else None,
                "valor_cents": valor_cents,
            },
        )

    @staticmethod
    def log_saque(saque_id, valor_cents):
        log_event(
            "pagamento.repassado",
            entity_type="saque",
            entity_id=str(saque_id) if saque_id is not None else None,
            metadata={"valor_cents": valor_cents},
        )

    @staticmethod
    def log(action, entity_type, entity_id=None, metadata=None, user_id=None):
        log_event(
            action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            metadata=metadata,
            user_id=user_id,
        )
