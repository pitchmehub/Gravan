"""Helper para criar notificações na plataforma Gravan."""
from db.supabase_client import get_supabase


def notify(perfil_id: str, *, tipo: str, titulo: str,
           mensagem: str = "", link: str = "", payload: dict | None = None):
    """
    Cria uma notificação para o perfil indicado e dispara um Web Push
    para todos os dispositivos cadastrados.
    Nunca quebra o fluxo principal em caso de erro — só loga.
    """
    if not perfil_id:
        return
    try:
        get_supabase().table("notificacoes").insert({
            "perfil_id": perfil_id,
            "tipo":      tipo,
            "titulo":    titulo,
            "mensagem":  mensagem,
            "link":      link,
            "payload":   payload or {},
        }).execute()
    except Exception as e:
        print(f"[notify] falhou ({tipo} -> {perfil_id}): {e}")

    # Web Push (PWA) — silencioso, nunca derruba o fluxo
    try:
        from services.push_service import send_push
        send_push(perfil_id, title=titulo, body=mensagem or "",
                  url=link or "/dashboard", tag=tipo,
                  data={"tipo": tipo, "payload": payload or {}})
    except Exception as e:
        print(f"[notify] push falhou ({tipo} -> {perfil_id}): {e}")
