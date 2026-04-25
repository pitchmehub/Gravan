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

# Mapa de gênero → estilo visual (em inglês p/ melhor resultado do modelo)
# Estilos pensados pra capas de álbum reais — cinematográficas, com forte
# identidade visual, contraste alto e estética premium.
GENERO_STYLE = {
    "Sertanejo": "wide cinematic countryside at golden hour, lone figure silhouette, "
                 "dust in the air, lens flare, anamorphic look, deep amber and teal palette",
    "MPB":       "rich brazilian modernism poster, tropical foliage, bossa nova mood, "
                 "muted ochre and emerald palette, grainy film texture, hand-painted feel",
    "Funk":      "neon-lit favela alley at night, holographic chrome lettering objects, "
                 "magenta and electric blue glow, motion blur, futuristic baile aesthetic",
    "Samba":     "carnival in rio at dusk, sequins and feathers, dynamic motion, "
                 "rich gold and crimson palette, deep contrast, editorial photo vibe",
    "Rock":      "high contrast black and white portrait energy, smoke and stage lights, "
                 "electric blood-red accent, gritty 35mm grain, raw editorial mood",
    "Pop":       "ultra modern minimalist studio scene, bold geometric color blocking, "
                 "iridescent highlights, glossy 3d render, fashion magazine cover vibe",
    "Gospel":    "majestic cathedral light rays through stained glass, cinematic mist, "
                 "deep indigo and warm gold palette, painterly oil texture, sacred mood",
    "Forró":     "vast northeastern brazilian sertão landscape, accordion and rabeca, "
                 "burnt orange sky, dramatic clouds, heroic cinematic composition",
    "Pagode":    "intimate roda de samba at dusk in a vintage botequim, warm tungsten light, "
                 "wooden textures, golden brass instruments, rich film grain",
    "RNB":       "moody late night rooftop scene, neon city skyline reflections, "
                 "deep navy and amber palette, cinematic bokeh, sensual editorial photo",
    "RAP":       "bold contemporary street portrait energy, oversized typography shapes, "
                 "concrete textures, dramatic spotlight, monochrome with single neon accent",
    "OUTROS":    "striking modern poster art, dramatic lighting, bold color contrast, "
                 "cinematic composition, editorial design quality",
}


def _build_prompt(nome: str, genero: str) -> str:
    """Monta um prompt rico em inglês p/ Pollinations gerar capa cinematográfica."""
    style = GENERO_STYLE.get(genero, GENERO_STYLE["OUTROS"])
    return (
        f"album cover artwork inspired by the song titled '{nome}'. "
        f"Style: {style}. "
        f"Cinematic composition, editorial album art, premium music cover, "
        f"strong focal subject, dramatic lighting, rich contrast, "
        f"depth and atmosphere, ultra detailed, 4k, square 1:1 format. "
        f"Strict rules: no text, no letters, no words, no logo, no watermark, "
        f"no signature, no caption, no typography of any kind."
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
