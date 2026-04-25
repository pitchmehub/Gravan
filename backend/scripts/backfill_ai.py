"""
One-shot backfill:
  • Gera capa (Pollinations.ai) pra TODA obra sem cover_url
  • Transcreve letra (Whisper) pra TODA obra com letra vazia/nula

Uso:  python scripts/backfill_ai.py [--no-letras] [--no-capas]

Capas são instantâneas (URL Pollinations).
Letras dependem do Whisper local (~30s–2min por obra).
"""
import os
import sys
import secrets
import argparse
import time

# Permitir rodar a partir de backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.supabase_client import get_supabase
from services.ai_capa import gerar_url_capa
from services.ai_letra import transcrever_audio_bytes


def backfill_capas(sb, force_all=False):
    print("\n=== CAPAS ===")
    q = sb.table("obras").select("id, nome, genero, cover_url")
    if not force_all:
        q = q.is_("cover_url", "null")
    r = q.execute()
    obras = r.data or []
    label = "TODAS as obras (regenerando)" if force_all else "Obras sem capa"
    print(f"{label}: {len(obras)}")
    feitas = 0
    for o in obras:
        try:
            url = gerar_url_capa(
                o.get("nome") or "Música",
                o.get("genero") or "OUTROS",
                seed=secrets.randbelow(10_000_000),
            )
            sb.table("obras").update({"cover_url": url}).eq("id", o["id"]).execute()
            feitas += 1
            print(f"  ✓ [{feitas}/{len(obras)}] {o.get('nome')[:50]}")
        except Exception as e:
            print(f"  ✗ {o['id']}: {e}")
    print(f"Capas geradas: {feitas}/{len(obras)}")


def _obra_sem_letra(sb):
    # "letra vazia" = NULL ou string com <10 caracteres
    r = (sb.table("obras")
           .select("id, nome, letra, audio_path")
           .execute())
    todas = r.data or []
    return [o for o in todas
            if o.get("audio_path") and (not o.get("letra") or len(o["letra"].strip()) < 10)]


def backfill_letras(sb):
    print("\n=== LETRAS ===")
    obras = _obra_sem_letra(sb)
    print(f"Obras sem letra: {len(obras)}")
    if not obras:
        return

    print("(Whisper pode levar dezenas de segundos por obra. Aguarde...)")
    feitas = 0
    erros = 0
    t0 = time.time()
    for i, o in enumerate(obras, 1):
        oid = o["id"]
        nome = o.get("nome") or oid
        try:
            print(f"\n[{i}/{len(obras)}] '{nome[:50]}'", flush=True)
            sb.table("obras").update({"letra_status": "transcrevendo"}).eq("id", oid).execute()

            print("   ↓ baixando áudio...", flush=True)
            try:
                audio_bytes = sb.storage.from_("obras-audio").download(o["audio_path"])
            except Exception as down_err:
                msg = str(down_err)
                if "not found" in msg.lower() or "404" in msg or "400" in msg:
                    sb.table("obras").update({"letra_status": "erro"}).eq("id", oid).execute()
                    erros += 1
                    print(f"   ⚠ áudio não existe no storage — pulando", flush=True)
                    continue
                raise

            print(f"   ✎ transcrevendo ({len(audio_bytes)//1024} KB)...", flush=True)
            t1 = time.time()
            texto = transcrever_audio_bytes(audio_bytes, language="pt")
            dur = time.time() - t1

            if texto:
                sb.table("obras").update({
                    "letra": texto,
                    "letra_status": "pronta",
                }).eq("id", oid).execute()
                feitas += 1
                print(f"   ✓ {len(texto)} chars em {dur:.0f}s", flush=True)
            else:
                sb.table("obras").update({"letra_status": "erro"}).eq("id", oid).execute()
                erros += 1
                print(f"   ⚠ texto vazio", flush=True)
        except Exception as e:
            erros += 1
            try:
                sb.table("obras").update({"letra_status": "erro"}).eq("id", oid).execute()
            except Exception:
                pass
            print(f"   ✗ erro: {e}", flush=True)

    total = time.time() - t0
    print(f"\nLetras: {feitas} ok / {erros} erro / {len(obras)} total — {total:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-capas", action="store_true")
    ap.add_argument("--no-letras", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="Regenera capas de TODAS as obras (não só as sem capa)")
    args = ap.parse_args()

    sb = get_supabase()
    if not args.no_capas:
        backfill_capas(sb, force_all=args.all)
    if not args.no_letras:
        backfill_letras(sb)
    print("\nFeito.")


if __name__ == "__main__":
    main()
