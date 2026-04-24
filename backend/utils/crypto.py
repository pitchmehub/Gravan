"""
Utilitário de criptografia para dados sensíveis (CPF, RG, etc).
Correção de vulnerabilidade #9 (ALTA): CPF e RG em texto plano.
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv()

# Gera chave derivada da FLASK_SECRET_KEY
def _get_encryption_key() -> bytes:
    """Deriva chave de encryption da SECRET_KEY do Flask."""
    secret = os.environ.get("FLASK_SECRET_KEY", "").encode()
    if len(secret) < 16:
        raise ValueError("FLASK_SECRET_KEY muito curta para encryption segura")
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'gravan_salt_2024',  # Salt fixo (em prod usar variável de ambiente)
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))
    return key


_cipher = None

def get_cipher():
    """Retorna instância singleton do Fernet cipher."""
    global _cipher
    if _cipher is None:
        _cipher = Fernet(_get_encryption_key())
    return _cipher


def encrypt_pii(plaintext: str) -> str:
    """
    Encripta dados PII (CPF, RG, etc).
    Retorna string base64 do ciphertext.
    """
    if not plaintext:
        return ""
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(plaintext.encode('utf-8'))
    return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')


def decrypt_pii(ciphertext: str) -> str:
    """
    Decripta dados PII.
    Retorna plaintext original.
    """
    if not ciphertext:
        return ""
    try:
        cipher = get_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode('utf-8')
    except Exception:
        # Se falhar decrypt (chave mudou?), retorna vazio
        return ""


def hash_ip(ip_address: str) -> str:
    """
    Hash de IP para anonimização (LGPD compliance).
    Correção de vulnerabilidade #12 (MÉDIA): IP logging sem anonimização.
    """
    import hashlib
    salt = os.environ.get("FLASK_SECRET_KEY", "gravan").encode()
    return hashlib.sha256(salt + ip_address.encode()).hexdigest()[:16]
