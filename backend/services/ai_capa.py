"""
Geração de capas de obra via Pollinations.ai (gratuito, sem chave).

Estratégia MVP:
  • Constrói um prompt em inglês baseado no nome + gênero + um estilo
    de arte contemporânea sorteado entre dezenas de movimentos
    (expressivos, abstratos, figurativos, gestuais, pop, etc.) e uma
    paleta de cores variada — para dar variedade artística real entre
    as capas, sem amarrar o visual a um único estilo.
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
# ESTILOS DE ARTE CONTEMPORÂNEA — UM é OBRIGATÓRIO em cada capa.
# Sorteado deterministicamente por obra para dar variedade artística
# real, do gestual ao geométrico, do figurativo ao expressivo, sem
# amarrar tudo num único visual.
# =====================================================================
CONTEMPORARY_ART_STYLES = [
    "Abstract Expressionism with bold gestural brushstrokes, dripped paint and raw emotional energy",
    "Neo-Expressionism with thick impasto, distorted figures and intense saturated color",
    "Action painting with splashes, drips and dynamic spontaneous marks",
    "Color Field painting with vast flat planes of pure saturated color and atmospheric softness",
    "Hard Edge abstraction with crisp boundaries between flat geometric color zones",
    "Lyrical Abstraction with soft fluid washes, organic shapes and poetic atmosphere",
    "Pop Art aesthetic with bold flat colors, halftone dots and screenprint texture",
    "Neo-Pop with playful iconography, vivid contrast and contemporary irony",
    "Surrealism with dreamlike imagery, impossible composition and mysterious atmosphere",
    "Cubist fragmented planes with multiple perspectives and angular geometry",
    "Futurist composition with dynamic motion lines, speed and modernist energy",
    "Constructivist diagonal composition with strong asymmetry and bold geometry",
    "Suprematist floating geometric planes with dynamic tension on neutral ground",
    "De Stijl inspired pure rectangles with primary color accents",
    "Bauhaus design with primary geometric shapes, circles, squares and triangles",
    "Op Art with precise repetition, optical illusion and rhythmic linework",
    "Kinetic art suggestion with shapes that imply movement and visual vibration",
    "Memphis Group postmodernism with playful patterns, bold motifs and squiggle accents",
    "Brutalist concrete texture mood, raw architectural surfaces and heavy materiality",
    "Risograph print look with grainy duotone overlay and slight misregistration",
    "Silkscreen poster aesthetic with layered flat color and rough edges",
    "Collage and mixed-media composition with torn paper, layered textures and analog feel",
    "Photomontage with cut-out fragments arranged in surreal symbolic composition",
    "Art Brut / Outsider Art with raw naive figuration, childlike marks and unfiltered expression",
    "Street art and graffiti aesthetic with spray paint texture, stencil shapes and urban energy",
    "Stencil art with sharp silhouettes, layered spray and political-poster feel",
    "Glitch art with digital distortion, pixel sorting and analog artifacts",
    "Vaporwave aesthetic with pastel gradients, classical motifs and retro-digital feel",
    "Cyberpunk neon aesthetic with electric color and high-tech atmosphere",
    "Lowbrow / pop surrealism with stylized characters and storybook strangeness",
    "Magical realism with figurative scene infused with dreamlike symbolism",
    "Contemporary figurative painting with stylized human or natural forms and atmospheric color",
    "Botanical contemporary illustration with stylized plants, organic curves and natural palette",
    "Contemporary woodcut and linocut style with carved bold lines and hand-printed texture",
    "Japanese Sumi-e ink wash with expressive black brushwork and breathing negative space",
    "Ukiyo-e inspired flat composition with stylized waves, mountains or natural motifs",
    "Mingei wabi-sabi aesthetic with handmade simplicity and quiet imperfection",
    "Fauvism with wildly non-naturalistic vivid color and bold expressive brushwork",
    "Symbolism with rich allegorical imagery and mystical atmospheric color",
    "Land art aesthetic with raw natural materials, earth pigments and organic geometry",
    "Process art with visible material gestures, drips, folds and traces of making",
    "Arte Povera with humble organic materials, raw textures and quiet poetry",
    "Tropicália visual aesthetic with lush tropical motifs, vivid Brazilian color and modernist edge",
    "Neoconcretism with sensual geometric forms, soft color and Brazilian modernist heritage",
    "Contemporary editorial illustration with stylized figures and bold flat color",
    "Painterly abstraction with visible brushwork, layered color and atmospheric depth",
    "Maximalist composition with rich layered patterns, ornament and saturated color",
    "Photorealist-inspired stylization with crisp detail isolated on flat field",
    "Dada-inspired absurd assemblage with unexpected juxtapositions",
    "Mid-century modern poster aesthetic with stylized figures and warm retro palette",
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


NEGATIVE_PROMPT = (
    "face, faces, human, person, people, man, woman, child, body, portrait, "
    "silhouette, mannequin, anatomy, skin, eyes, mouth, nose, head, hair, hands, "
    "fingers, crowd, figure, figurative, character, selfie, photography of person, "
    "text, typography, letters, alphabet, numbers, digits, words, logo, watermark, "
    "signature, calligraphy, font, label, caption, title, inscription, symbol, icon"
)


def _build_prompt(nome: str, genero: str, seed: int | None) -> str:
    """
    Prompt puramente positivo — descreve SÓ o que queremos.
    Proibições ficam no negative_prompt separado, que é mais eficaz.
    """
    return (
        "Create a neo-minimalist cover artwork with an ultra-refined, contemporary and premium aesthetic. "
        "CORE STYLE — NEO MINIMALISM: "
        "Extreme reduction of elements: only 1 to 3 main visual elements maximum. "
        "Large use of negative space (empty space as a primary design feature). "
        "Focus on subtlety, restraint, and precision. "
        "Clean, intentional composition with no visual noise. "
        "VISUAL DIRECTION: "
        "Use simple geometric or organic forms with soft edges or precise contours. "
        "Emphasize micro-details: texture, light gradients, soft reflections, and material realism. "
        "Materials can include matte surfaces, frosted glass, polished metal, smooth plastic, or soft fabric. "
        "Lighting should be soft, controlled, and cinematic, creating depth without complexity. "
        "COLOR: "
        "Use a very limited color palette (monochromatic or 2–3 tones max). "
        "Prefer neutral tones: black, white, grey, beige, or muted colors. "
        "Subtle gradients are allowed, but must remain minimal and refined. "
        "COMPOSITION: "
        "Strong focus on balance and spacing. "
        "Centered or slightly off-centered composition with intentional asymmetry. "
        "One clear focal point, with surrounding empty space enhancing it. "
        "MOOD: "
        "Calm, elegant, introspective, and sophisticated. "
        "Feels like high-end editorial design or luxury brand identity. "
        "OUTPUT: "
        "Square format (1:1), high resolution. "
        "No borders, no frames, no overlays. "
        "Ultra-clean final result with a premium, gallery-like presence. "
        "The final artwork must feel like a high-fashion, luxury-grade neo-minimalist cover used in global music or art platforms."
    )


def gerar_url_capa(nome: str, genero: str, seed: int | None = None) -> str:
    """
    Retorna URL pública e estável do Pollinations.ai pra capa da obra.
    A própria URL serve a imagem (CDN do Pollinations).
    """
    prompt = _build_prompt(nome or "Música", genero or "OUTROS", seed)
    encoded = urllib.parse.quote(prompt, safe="")
    params = {
        "width":    "768",
        "height":   "768",
        "nologo":   "true",
        "enhance":  "true",
        "model":    "flux",
        "negative": urllib.parse.quote(NEGATIVE_PROMPT, safe=""),
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
