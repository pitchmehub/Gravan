"""
Geração de capas de obra via Pollinations.ai (gratuito, sem chave).

Estratégia MVP:
  • Constrói um prompt em inglês baseado no nome + gênero da obra
  • Gera URL determinística do Pollinations.ai (a própria URL é a imagem)
  • Salva a URL em obras.cover_url

Pollinations não exige chave nem cadastro. Para escala maior trocar
por Hugging Face / OpenAI sem alterar o resto da app.
"""
import logging
import urllib.parse
from db.supabase_client import get_supabase

log = logging.getLogger(__name__)

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"

# =====================================================================
# Estética obrigatória: NEO-MINIMALISMO
# =====================================================================
# Toda capa segue a mesma linguagem visual base — neo-minimalista —
# variando apenas o objeto/símbolo focal, paleta e textura por gênero.
# Princípios neo-min: muito espaço negativo, único sujeito focal,
# composição limpa, formas geométricas simples, paleta restrita
# (2-3 cores), sutileza, calma, elegância gráfica contemporânea.
# =====================================================================

NEO_MIN_BASE = (
    "neo-minimalism aesthetic, clean composition, generous negative space, "
    "single focal subject perfectly centered or rule-of-thirds, "
    "restrained palette of 2 to 3 colors, geometric simplicity, "
    "subtle paper-like or matte texture, soft directional light, "
    "calm contemplative mood, contemporary editorial art print quality"
)

# Cada gênero contribui apenas com: objeto/símbolo focal + paleta sugerida.
# A linguagem neo-min é mantida intacta em todos eles.
GENERO_STYLE = {
    "Sertanejo": "single distant horizon line with one small silhouette of a horse or "
                 "lone tree on a vast plain, warm sand and dusty terracotta palette with cream",
    "MPB":       "one stylized tropical leaf or simple bossa-style geometric wave shape "
                 "floating in negative space, muted sage green and warm cream palette",
    "Funk":      "one bold neon circle or single chrome sphere on a flat dark surface, "
                 "deep matte black with one electric magenta or cyan accent",
    "Samba":     "one single feather or one geometric round shape suggesting a tambourine, "
                 "warm cream background with one rich crimson and one mustard accent",
    "Rock":      "one cracked geometric shape or single broken circle on flat surface, "
                 "bone white background with deep charcoal and a single muted red accent",
    "Pop":       "one perfect glossy sphere or simple pastel arch on flat ground, "
                 "soft pastel pink or lilac palette with one vivid accent color",
    "Gospel":    "one slender vertical light beam or single arch shape in deep silence, "
                 "off-white and warm gold palette with very soft shadow",
    "Forró":     "one minimal sun disc above a single horizon line, "
                 "warm ochre and burnt sienna palette with cream background",
    "Pagode":    "one simple cavaquinho silhouette or single round drum shape, "
                 "warm wood tan and cream palette with deep brown accent",
    "RNB":       "one solitary moon shape or single curved line on dark plane, "
                 "deep midnight navy palette with one warm amber accent",
    "RAP":       "one single bold geometric shape or simple concrete block on flat ground, "
                 "raw concrete grey palette with one sharp neon accent",
    "OUTROS":    "one abstract geometric symbol or single organic shape in pure negative space, "
                 "warm neutral palette with one restrained accent color",
}


def _build_prompt(nome: str, genero: str) -> str:
    """
    Prompt obrigatoriamente neo-minimalista em inglês para Pollinations.
    O nome da música inspira sutilmente o sujeito focal, mas a estética
    neo-min é mandatória e prevalece sobre qualquer outra direção.
    """
    style = GENERO_STYLE.get(genero, GENERO_STYLE["OUTROS"])
    return (
        f"Album cover for the song titled '{nome}'. "
        f"MANDATORY STYLE — strict neo-minimalism: {NEO_MIN_BASE}. "
        f"Focal motif inspired by genre: {style}. "
        f"The neo-minimalist rules above are absolute and override any other "
        f"interpretation of the title. Square 1:1 format, art print quality, "
        f"flat or very subtle gradient background, no clutter, no busy details, "
        f"no realism, no photography, no people faces, no crowded scenes. "
        f"Strict negative rules: no text, no letters, no words, no numbers, "
        f"no logo, no watermark, no signature, no caption, no typography "
        f"of any kind anywhere in the image."
    )


def gerar_url_capa(nome: str, genero: str, seed: int | None = None) -> str:
    """
    Retorna URL pública e estável do Pollinations.ai pra capa da obra.
    A própria URL serve a imagem (CDN do Pollinations).
    """
    prompt = _build_prompt(nome or "Música", genero or "OUTROS")
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


def gerar_e_salvar_capa(obra_id: str, nome: str, genero: str,
                        seed: int | None = None) -> str | None:
    """
    Gera URL da capa e persiste em obras.cover_url.
    Retorna a URL ou None em caso de erro.
    """
    try:
        url = gerar_url_capa(nome, genero, seed=seed)
        sb = get_supabase()
        sb.table("obras").update({"cover_url": url}).eq("id", obra_id).execute()
        log.info("[ai_capa] capa gerada para obra %s", obra_id)
        return url
    except Exception as e:
        log.exception("[ai_capa] falha ao gerar capa para obra %s: %s", obra_id, e)
        return None
