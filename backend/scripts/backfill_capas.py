"""
Reprocessa as capas das obras existentes, persistindo no Supabase Storage.

Estratégia anti rate-limit:
  • UMA obra por vez
  • pausa de 8s entre obras
  • em caso de 429, espera 60s e tenta a obra inteira de novo
  • só atualiza obras.cover_url quando o upload no Storage der certo
    (assim, se falhar, a obra mantém a URL antiga e roda de novo na próxima)

Uso:  cd backend && python scripts/backfill_capas.py
"""
import sys, os, secrets, time, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.supabase_client import get_supabase
from services.ai_capa import gerar_url_capa, _upload_supabase

PAUSA_ENTRE_OBRAS_S = 8
ESPERA_RATE_LIMIT_S = 60
MAX_TENTATIVAS = 3
DOWNLOAD_TIMEOUT_S = 90

def baixar_uma_vez(url: str):
    """Faz UM GET. Retorna (status, bytes|None)."""
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT_S)
        return r.status_code, (r.content if r.status_code == 200 else None)
    except Exception as e:
        return -1, None

def processar(obra, sb) -> str:
    """Tenta persistir a capa. Retorna 'ok', 'fail' ou 'rate'."""
    seed = secrets.randbelow(10_000_000)
    poll_url = gerar_url_capa(obra.get("nome") or "Música",
                              obra.get("genero") or "OUTROS", seed=seed)
    status, img = baixar_uma_vez(poll_url)
    if status == 429:
        return "rate"
    if not img or len(img) < 1024:
        return "fail"
    final = _upload_supabase(obra["id"], img)
    if not final:
        return "fail"
    sb.table("obras").update({"cover_url": final}).eq("id", obra["id"]).execute()
    return "ok"

def main():
    sb = get_supabase()
    obras = sb.table("obras").select("id, nome, genero, cover_url").execute().data or []
    pendentes = [o for o in obras
                 if "supabase.co/storage" not in (o.get("cover_url") or "")]

    print(f"Total obras: {len(obras)}  |  pendentes: {len(pendentes)}", flush=True)
    ok = fail = 0
    for i, o in enumerate(pendentes, 1):
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            res = processar(o, sb)
            if res == "ok":
                ok += 1
                print(f"  [{i:>2}/{len(pendentes)}] OK   {o['nome'][:35]}", flush=True)
                break
            if res == "rate":
                print(f"  [{i:>2}/{len(pendentes)}] 429  {o['nome'][:35]}  — esperando {ESPERA_RATE_LIMIT_S}s (tent {tentativa})", flush=True)
                time.sleep(ESPERA_RATE_LIMIT_S)
                continue
            print(f"  [{i:>2}/{len(pendentes)}] FAIL {o['nome'][:35]}  (tent {tentativa})", flush=True)
            time.sleep(5)
        else:
            fail += 1
        time.sleep(PAUSA_ENTRE_OBRAS_S)
    print(f"\n--- Resultado final: OK={ok}  FAIL={fail} ---", flush=True)

if __name__ == "__main__":
    main()
