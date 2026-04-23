"""
Validação de segurança para uploads de áudio.

Defense in Depth para arquivos:
  1. Extensão verificada no frontend (primeira barreira)
  2. MIME type via python-magic (Magic Number) verificado aqui
  3. Tamanho máximo validado antes de qualquer leitura

Magic Numbers válidos para MP3:
  - ID3 header:  49 44 33 (b'ID3')
  - MPEG frame:  FF FB, FF FA, FF F3, FF F2 (com variações de bitrate)
  - MPEG frame:  FF E0-FF (MPEG 2.5)
"""
import logging

try:
    import magic
    _MAGIC_AVAILABLE = True
except (ImportError, OSError) as _e:
    # libmagic não instalada (comum em Windows sem python-magic-bin).
    # O app segue funcionando; a validação de MIME vira um no-op com log de aviso.
    logging.getLogger(__name__).warning(
        "python-magic indisponível (%s). Validação de MIME desativada; "
        "apenas magic-bytes serão verificados.", _e
    )
    magic = None
    _MAGIC_AVAILABLE = False

MP3_MAGIC_BYTES = [
    b"\x49\x44\x33",  # ID3v2
    b"\xff\xfb",      # MPEG1 Layer3, no padding, no CRC
    b"\xff\xfa",      # MPEG1 Layer3, no padding, CRC
    b"\xff\xf3",      # MPEG2 Layer3, no padding
    b"\xff\xf2",      # MPEG2 Layer3, no padding, CRC
]

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_mp3(file_bytes: bytes) -> tuple[bool, str]:
    """
    Valida que os bytes correspondem a um arquivo MP3 legítimo.
    Retorna (is_valid, mensagem_de_erro).
    """
    # 1. Tamanho
    if len(file_bytes) > MAX_AUDIO_BYTES:
        return False, f"Arquivo excede o limite de 10 MB ({len(file_bytes)} bytes recebidos)."

    # 2. Magic Number (primeiros bytes)
    header = file_bytes[:3]
    is_mp3_magic = any(file_bytes[:len(sig)] == sig for sig in MP3_MAGIC_BYTES)
    if not is_mp3_magic:
        return False, "Arquivo inválido: assinatura MP3 não reconhecida."

    # 3. MIME type via libmagic (camada extra — só se disponível)
    if _MAGIC_AVAILABLE:
        try:
            mime = magic.from_buffer(file_bytes[:2048], mime=True)
            if mime not in ("audio/mpeg", "audio/mp3", "audio/x-mpeg"):
                return False, f"Tipo MIME inválido: '{mime}'. Apenas audio/mpeg é aceito."
        except Exception:
            return False, "Não foi possível determinar o tipo do arquivo."

    return True, ""
