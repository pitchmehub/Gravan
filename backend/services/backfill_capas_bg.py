"""
Backfill em background das capas das obras antigas.

Roda em uma thread daemon que sobe junto com o backend. UMA obra por vez,
com pausa entre requisições para não estourar o rate-limit da Pollinations.
Usa um file lock para garantir que só um worker do gunicorn execute.
"""
import os
import time
import fcntl
import secrets
import logging
import threading
import requests

log = logging.getLogger(__name__)

LOCK_PATH = "/tmp/gravan_backfill_capas.lock"
PAUSA_ENTRE_OBRAS_S = 8
ESPERA_RATE_LIMIT_S = 60
MAX_TENTATIVAS = 4
DOWNLOAD_TIMEOUT_S = 90
ATRASO_INICIAL_S = 30  # deixa o servidor estabilizar antes de começar


def _baixar_uma_vez(url: str):
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT_S)
        if r.status_code == 200 and r.content and len(r.content) > 1024:
            return "ok", r.content
        if r.status_code == 429:
            return "rate", None
        return "fail", None
    except Exception as e:
        log.warning("[backfill_bg] erro de rede: %s", e)
        return "fail", None


def _processar_obra(obra, sb):
    from services.ai_capa import gerar_url_capa, _upload_supabase
    seed = secrets.randbelow(10_000_000)
    poll_url = gerar_url_capa(
        obra.get("nome") or "Música",
        obra.get("genero") or "OUTROS",
        seed=seed,
    )
    status, img = _baixar_uma_vez(poll_url)
    if status == "rate":
        return "rate"
    if status != "ok":
        return "fail"
    final = _upload_supabase(obra["id"], img)
    if not final:
        return "fail"
    sb.table("obras").update({"cover_url": final}).eq("id", obra["id"]).execute()
    return "ok"


def _loop():
    from db.supabase_client import get_supabase
    time.sleep(ATRASO_INICIAL_S)
    try:
        sb = get_supabase()
        obras = sb.table("obras").select("id, nome, genero, cover_url").execute().data or []
        pendentes = [o for o in obras
                     if "supabase.co/storage" not in (o.get("cover_url") or "")]
        if not pendentes:
            log.info("[backfill_bg] nada a fazer — todas as capas já estão no Storage.")
            return
        log.info("[backfill_bg] iniciando: %d obras pendentes", len(pendentes))
        ok = fail = 0
        for i, o in enumerate(pendentes, 1):
            for tent in range(1, MAX_TENTATIVAS + 1):
                res = _processar_obra(o, sb)
                if res == "ok":
                    ok += 1
                    log.info("[backfill_bg] [%d/%d] OK   %s", i, len(pendentes), o["nome"][:40])
                    break
                if res == "rate":
                    log.warning("[backfill_bg] [%d/%d] 429  %s — aguardando %ds (tent %d)",
                                i, len(pendentes), o["nome"][:40], ESPERA_RATE_LIMIT_S, tent)
                    time.sleep(ESPERA_RATE_LIMIT_S)
                    continue
                log.warning("[backfill_bg] [%d/%d] FAIL %s (tent %d)",
                            i, len(pendentes), o["nome"][:40], tent)
                time.sleep(5)
            else:
                fail += 1
            time.sleep(PAUSA_ENTRE_OBRAS_S)
        log.info("[backfill_bg] FIM. OK=%d FAIL=%d", ok, fail)
    except Exception as e:
        log.exception("[backfill_bg] crash no loop: %s", e)


def start_backfill_capas_bg():
    """
    Inicia a thread só em UM worker (file lock não bloqueante).
    No-op se outro worker já adquiriu o lock.
    """
    try:
        f = open(LOCK_PATH, "w")
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        log.info("[backfill_bg] outro worker já está cuidando do backfill.")
        return

    # mantém o handle vivo amarrado à thread para preservar o lock
    def _run():
        try:
            _loop()
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                f.close()
            except Exception:
                pass

    t = threading.Thread(target=_run, daemon=True, name="backfill-capas")
    t.start()
    log.info("[backfill_bg] thread agendada (atraso inicial %ds).", ATRASO_INICIAL_S)
