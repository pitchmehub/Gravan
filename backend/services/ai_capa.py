"""
Geração de capas de obra via Pollinations.ai (gratuito, sem chave).

Estratégia MVP:
  • Constrói um prompt em inglês baseado no nome + gênero + um conceito
    contemporâneo de arte (sorteado entre vários movimentos) e uma paleta
    de cores variada — mantendo neo-minimalismo + minimalismo como base
    sempre presente, e mesclando UM conceito contemporâneo extra para
    dar variedade real entre as capas.
  • Gera URL determinística do Pollinations.ai
  • Baixa a imagem e PERSISTE no Supabase Storage (bucket "capas")
  • Salva a URL pública do Supabase em obras.cover_url

Persistência local é necessária porque Pollinations.ai é lento/instável
(timeouts e respostas vazias frequentes), o que fazia as capas não
aparecerem no front quando o navegador carregava muitas ao mesmo tempo.
"""
import hashlib
import logging
import urllib.parse
import requests
from db.supabase_client import get_supabase

log = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
COVERS_BUCKET = "capas"
POLLINATIONS_TIMEOUT_S = 60
POLLINATIONS_RETRIES = 3

# =====================================================================
# BASE: neo-minimalismo + minimalismo (sempre presente)
# =====================================================================
BASE_AESTHETIC = (
    "neo-minimalism fused with classic minimalism, clean composition, "
    "generous negative space, single focal subject, geometric clarity, "
    "subtle paper-like or matte texture, soft directional light, "
    "calm contemplative mood, contemporary editorial art print quality"
)

# =====================================================================
# CONCEITOS CONTEMPORÂNEOS — sorteados por capa para dar variedade.
# Cada item descreve a "tempera" extra que vai junto da base neo-min.
# =====================================================================
CONTEMPORARY_CONCEPTS = [
    "Bauhaus design influence with primary geometric shapes (circles, squares, triangles)",
    "Suprematist composition with floating geometric planes and dynamic tension",
    "Color Field abstraction with large flat planes of pure saturated color",
    "Hard Edge abstraction with crisp boundaries between flat color zones",
    "Op Art subtle linework, precise repetition, gentle visual rhythm",
    "Memphis Group inspired playful pattern accents and bold geometric motifs",
    "Brutalist concrete texture mood, raw and architectural",
    "Constructivist diagonal composition, strong asymmetry, modernist energy",
    "Mid-century modern Scandinavian print aesthetic, organic restraint",
    "Geometric abstraction with overlapping translucent planes",
    "Risograph print look with grainy duotone overlay and slight misregistration",
    "Modernist poster style inspired by Swiss design, clean grid structure",
    "Postmodern playful collage of one or two simple shapes",
    "Cubist fragmented planes interpreted in flat minimalist palette",
    "Concrete art (Arte Concreta) with mathematical proportions and pure forms",
    "Abstract expressionist single calm gesture in vast empty space",
    "Japanese Mingei influence, handmade simplicity, wabi-sabi imperfection",
    "Ukiyo-e inspired flat composition with negative-space horizon",
    "Op-Pop fusion with one bold optical motif on neutral ground",
    "De Stijl inspired pure rectangles with restrained primary accent",
]

# =====================================================================
# PALETAS DE CORES — sorteadas por capa para evitar a sensação de capas
# todas iguais. Misturam quentes, frios, monocromos e contrastes.
# =====================================================================
COLOR_PALETTES = [
    "warm terracotta and dusty cream with a single deep ochre accent",
    "deep midnight navy and ivory with a single warm amber accent",
    "muted sage green and bone white with a single rust accent",
    "soft pastel pink and lilac with a single vivid magenta accent",
    "raw concrete grey and off-white with a single sharp neon-yellow accent",
    "burnt sienna and warm sand with a single forest green accent",
    "deep matte black and cream with a single electric cyan accent",
    "warm wood tan and ivory with a single deep brown accent",
    "cobalt blue and pale sand with a single white accent",
    "olive green and mustard yellow with a single off-white accent",
    "lavender and dusty rose with a single eggplant accent",
    "charcoal grey and bone white with a single muted crimson accent",
    "ochre yellow and warm white with a single carbon black accent",
    "teal blue and cream with a single warm coral accent",
    "indigo and pearl with a single soft gold accent",
    "moss green and chalk white with a single burnt orange accent",
    "burgundy and pale peach with a single ink black accent",
    "stone beige and ash grey with a single saffron accent",
    "deep forest green and bone with a single brick red accent",
    "warm taupe and ivory with a single cobalt accent",
    "monochrome scale of greys with a single lipstick red accent",
    "monochrome scale of warm browns with a single buttercream accent",
    "monochrome blues from pale sky to navy",
    "duotone palette of dusty plum and pale sand",
    "duotone palette of soft mint and powder pink",
]

# =====================================================================
# MOTIVO FOCAL POR GÊNERO — apenas o objeto/símbolo central. A linguagem
# visual e a paleta vêm das listas acima (variando por obra).
# =====================================================================
GENERO_FOCAL = {
    "Sertanejo": "single distant horizon line with one small silhouette of a horse, lone tree or rural fence",
    "MPB":       "one stylized tropical leaf or simple bossa-style geometric wave shape floating in space",
    "Funk":      "one bold neon circle, single chrome sphere or simple speaker silhouette on flat ground",
    "Samba":     "one single feather or one geometric round shape suggesting a tambourine",
    "Rock":      "one cracked geometric shape, single broken circle or minimal lightning bolt",
    "Pop":       "one perfect glossy sphere, simple pastel arch or balloon silhouette",
    "Gospel":    "one slender vertical light beam, single arch shape or minimal dove silhouette",
    "Forró":     "one minimal sun disc above a single horizon line, or one stylized accordion bellows shape",
    "Pagode":    "one simple cavaquinho silhouette or single round drum shape",
    "RNB":       "one solitary moon shape, single curved line or minimal vinyl record on dark plane",
    "RAP":       "one single bold geometric shape, minimal microphone silhouette or simple concrete block",
    "OUTROS":    "one abstract geometric symbol, single organic shape or minimal circle in pure space",
}


def _rng_index(seed_str: str, n: int) -> int:
    """Índice determinístico baseado em hash da seed_str — varia por obra."""
    h = hashlib.sha1(seed_str.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "big") % max(1, n)


def _build_prompt(nome: str, genero: str, seed: int | None) -> str:
    """
    Prompt em inglês para Pollinations: base neo-min + minimalismo SEMPRE,
    combinada com UM movimento contemporâneo + UMA paleta sorteada
    deterministicamente a partir da seed/nome — para dar real variedade
    entre as capas mantendo a identidade Gravan.
    """
    seed_str = f"{seed or 0}-{nome}-{genero}"
    concept = CONTEMPORARY_CONCEPTS[_rng_index(seed_str + "-c", len(CONTEMPORARY_CONCEPTS))]
    palette = COLOR_PALETTES[_rng_index(seed_str + "-p", len(COLOR_PALETTES))]
    focal   = GENERO_FOCAL.get(genero, GENERO_FOCAL["OUTROS"])

    return (
        f"Album cover for the song titled '{nome}'. "
        f"MANDATORY BASE STYLE: {BASE_AESTHETIC}. "
        f"Combine the base with this contemporary art concept: {concept}. "
        f"Focal motif inspired by genre: {focal}. "
        f"Color palette (strict, only these colors): {palette}. "
        f"Square 1:1 format, art print quality, flat or very subtle gradient "
        f"background, no clutter, no busy details, no realism, no photography, "
        f"no people faces, no crowded scenes. "
        f"Strict negative rules: no text, no letters, no words, no numbers, "
        f"no logo, no watermark, no signature, no caption, no typography "
        f"of any kind anywhere in the image."
    )


def gerar_url_capa(nome: str, genero: str, seed: int | None = None) -> str:
    """
    Retorna URL pública e estável do Pollinations.ai pra capa da obra.
    A própria URL serve a imagem (CDN do Pollinations).
    """
    prompt = _build_prompt(nome or "Música", genero or "OUTROS", seed)
    encoded = urllib.parse.quote(prompt, safe="")
    params = {
        "width":   "768",
        "height":  "768",
        "nologo":  "true",
        "enhance": "true",
        "model":   "flux",
    }
    if seed is not None:
        params["seed"] = str(seed)

    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{POLLINATIONS_BASE}/{encoded}?{qs}"


def _baixar_imagem_pollinations(url: str) -> bytes | None:
    """Baixa imagem com retry — Pollinations às vezes responde vazio/timeout."""
    for tentativa in range(1, POLLINATIONS_RETRIES + 1):
        try:
            r = requests.get(url, timeout=POLLINATIONS_TIMEOUT_S)
            if r.status_code == 200 and r.content and len(r.content) > 1024:
                return r.content
            log.warning(
                "[ai_capa] tentativa %d falhou: status=%s bytes=%s",
                tentativa, r.status_code, len(r.content) if r.content else 0,
            )
        except Exception as e:
            log.warning("[ai_capa] tentativa %d erro: %s", tentativa, e)
    return None


def _upload_supabase(obra_id: str, image_bytes: bytes) -> str | None:
    """Faz upload da imagem no bucket público 'capas' e retorna a URL pública."""
    try:
        sb = get_supabase()
        path = f"{obra_id}.jpg"
        sb.storage.from_(COVERS_BUCKET).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "true"},
        )
        public_url = sb.storage.from_(COVERS_BUCKET).get_public_url(path)
        return public_url.rstrip("?")
    except Exception as e:
        log.exception("[ai_capa] upload pra Storage falhou (obra %s): %s", obra_id, e)
        return None


def gerar_e_salvar_capa(obra_id: str, nome: str, genero: str,
                        seed: int | None = None) -> str | None:
    """
    Gera capa via Pollinations.ai, persiste no Supabase Storage e
    grava a URL pública em obras.cover_url.

    Se o download/upload falhar, salva a URL direta do Pollinations
    como fallback (a imagem ainda funciona, só fica mais lenta).

    Retorna a URL final ou None em caso de erro total.
    """
    try:
        sb = get_supabase()
        # Garante uma seed estável por obra para variar entre obras mas
        # ser determinística para a mesma obra — usa o próprio obra_id
        # quando a seed não é fornecida pelo chamador.
        seed_efetiva = seed
        if seed_efetiva is None and obra_id:
            seed_efetiva = int.from_bytes(
                hashlib.sha1(obra_id.encode("utf-8")).digest()[:4], "big"
            )

        poll_url = gerar_url_capa(nome, genero, seed=seed_efetiva)

        # 1) Baixa do Pollinations e tenta persistir no Storage
        img_bytes = _baixar_imagem_pollinations(poll_url)
        final_url: str | None = None
        if img_bytes:
            final_url = _upload_supabase(obra_id, img_bytes)
            if final_url:
                log.info("[ai_capa] capa persistida no Storage para obra %s", obra_id)

        # 2) Fallback: usa a URL direta do Pollinations
        if not final_url:
            final_url = poll_url
            log.warning("[ai_capa] usando URL direta do Pollinations para obra %s (fallback)", obra_id)

        sb.table("obras").update({"cover_url": final_url}).eq("id", obra_id).execute()
        return final_url
    except Exception as e:
        log.exception("[ai_capa] falha ao gerar capa para obra %s: %s", obra_id, e)
        return None
