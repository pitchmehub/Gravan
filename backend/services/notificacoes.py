"""Helper para criar notificações na plataforma Gravan."""
from db.supabase_client import get_supabase


def notify(perfil_id: str, *, tipo: str, titulo: str,
           mensagem: str = "", link: str = "", payload: dict | None = None):
    """
    Cria uma notificação para o perfil indicado e dispara um Web Push
    para todos os dispositivos cadastrados.
    Nunca quebra o fluxo principal em caso de erro — só loga.

    O Web Push é enviado para `/notificacoes?abrir=<id>` para que o app
    sempre abra o modal com as informações e ações da notificação,
    em vez de redirecionar diretamente para outra rota.
    """
    if not perfil_id:
        return

    notif_id = None
    try:
        r = get_supabase().table("notificacoes").insert({
            "perfil_id": perfil_id,
            "tipo":      tipo,
            "titulo":    titulo,
            "mensagem":  mensagem,
            "link":      link,
            "payload":   payload or {},
        }).execute()
        try:
            notif_id = (r.data or [{}])[0].get("id")
        except Exception:
            notif_id = None
    except Exception as e:
        print(f"[notify] falhou ({tipo} -> {perfil_id}): {e}")

    # URL do push: sempre abre o modal na tela de notificações.
    # Fallback: link direto, se não conseguimos pegar o id.
    push_url = f"/notificacoes?abrir={notif_id}" if notif_id else (link or "/notificacoes")

    # Web Push (PWA) — silencioso, nunca derruba o fluxo
    try:
        from services.push_service import send_push
        send_push(perfil_id, title=titulo, body=mensagem or "",
                  url=push_url, tag=tipo,
                  data={"tipo": tipo, "notif_id": notif_id, "payload": payload or {}})
    except Exception as e:
        print(f"[notify] push falhou ({tipo} -> {perfil_id}): {e}")
