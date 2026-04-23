"""
Sanitizacao de inputs — defesa contra XSS, injection, path traversal.
"""
import re
import bleach

ALLOWED_TAGS = []
ALLOWED_ATTRIBUTES = {}

# Rejeita caracteres que podem ser usados em path traversal
PATH_TRAVERSAL = re.compile(r"(\.\./|\.\.\\|/\.\.|\\\.\.|\x00)")

# Caracteres de controle (ctrl+chars) — removidos exceto \n, \t
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(value: str, max_length: int = None) -> str:
    """Remove HTML/JS, caracteres de controle, tentativas de path traversal."""
    if not isinstance(value, str):
        raise ValueError("Esperado string.")

    # Remove caracteres de controle primeiro
    cleaned = CONTROL_CHARS.sub("", value)

    # Rejeita path traversal (log + erro)
    if PATH_TRAVERSAL.search(cleaned):
        raise ValueError("Caracteres invalidos detectados.")

    # Limpa HTML/JS
    cleaned = bleach.clean(
        cleaned,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    ).strip()

    if max_length and len(cleaned) > max_length:
        raise ValueError(f"Texto excede o limite de {max_length} caracteres.")

    return cleaned


def sanitize_obra_fields(data: dict) -> dict:
    """Sanitiza campos de texto de uma obra."""
    return {
        "nome":  sanitize_text(data.get("nome", ""),  max_length=200),
        "letra": sanitize_text(data.get("letra", ""), max_length=50_000),
        "genero": sanitize_text(data.get("genero", ""), max_length=80)
            if data.get("genero") else None,
    }
