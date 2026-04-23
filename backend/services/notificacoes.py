"""Helper para criar notificações na plataforma Pitch.me."""
from db.supabase_client import get_supabase


def notify(perfil_id: str, *, tipo: str, titulo: str,
           mensagem: str = "", link: str = "", payload: dict | None = None):
    """
    Cria uma notificação para o perfil indicado.
    Nunca quebra o fluxo principal em caso de erro — só loga.

    tipos suportados:
      - 'obra_cadastrada'
      - 'contrato_gerado'
      - 'contrato_assinado'
      - 'licenciamento'
      - 'oferta'
      - 'dossie_download'
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
