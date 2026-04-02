"""Encryption utilities for credential storage at rest."""
import base64
import hashlib
import os
from cryptography.fernet import Fernet


def _derive_key() -> bytes:
    """Derive a Fernet-compatible key from JWT_SECRET."""
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        # Auto-generate fallback (same logic as auth.py)
        import secrets as _s
        secret = _s.token_hex(32)
    # Fernet requires 32 url-safe base64 bytes
    raw = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def _get_fernet() -> Fernet:
    return Fernet(_derive_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a string, return base64-encoded ciphertext."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext back to string."""
    if not ciphertext:
        return ""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def encrypt_dict(data: dict, fields: list[str]) -> dict:
    """Return a copy of data with specified fields encrypted."""
    result = dict(data)
    for f in fields:
        if f in result and result[f]:
            result[f] = encrypt(str(result[f]))
    return result


def decrypt_dict(data: dict, fields: list[str]) -> dict:
    """Return a copy of data with specified fields decrypted."""
    result = dict(data)
    for f in fields:
        if f in result and result[f]:
            try:
                result[f] = decrypt(result[f])
            except Exception:
                pass  # Field may not be encrypted (legacy data)
    return result
