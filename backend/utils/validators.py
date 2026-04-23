"""
Validadores aprimorados para inputs.

CORREÇÕES:
- #15 (MÉDIA): Validação de email robusta
- #16 (MÉDIA): Validação de comprimento de inputs
"""
import re

# Email validation (RFC 5322 simplified)
EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# CPF: apenas dígitos
CPF_RE = re.compile(r"^\d{11}$")

# UUID v4 validation
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def validate_email(email: str) -> bool:
    """
    Validação robusta de email (vulnerabilidade #15).
    Rejeita emails inválidos que o regex antigo aceitaria.
    """
    if not email or len(email) > 254:  # RFC 5321
        return False
    
    if not EMAIL_RE.match(email):
        return False
    
    # Validações adicionais
    local, domain = email.rsplit('@', 1)
    if len(local) > 64:  # RFC 5321
        return False
    if len(domain) > 253:
        return False
    if domain.startswith('.') or domain.endswith('.'):
        return False
    if '..' in domain:
        return False
    
    return True


def validate_cpf(cpf: str) -> bool:
    """Validação completa dos 2 dígitos verificadores do CPF."""
    cpf = re.sub(r"\D", "", cpf or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        dv = (soma * 10) % 11
        if dv == 10:
            dv = 0
        if dv != int(cpf[i]):
            return False
    return True


def validate_uuid(value: str) -> bool:
    """Valida se é um UUID v4 válido (para path traversal protection)."""
    return bool(UUID_RE.match(str(value)))


def validate_string_length(value: str, min_len: int = 0, max_len: int = None) -> bool:
    """
    Validação de comprimento de string (vulnerabilidade #16).
    Previne DOS via payloads gigantes.
    """
    if not isinstance(value, str):
        return False
    length = len(value)
    if length < min_len:
        return False
    if max_len is not None and length > max_len:
        return False
    return True
