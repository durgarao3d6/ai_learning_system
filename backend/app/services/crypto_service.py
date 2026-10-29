"""Cryptography service for answer key and explanation encryption."""

from cryptography.fernet import Fernet

from app.config import Settings


def get_fernet(settings: Settings) -> Fernet:
    """Instantiate a Fernet symmetric cipher from application settings."""
    return Fernet(settings.FERNET_KEY.encode())


def encrypt_text(text: str, settings: Settings) -> str:
    """Encrypt a plaintext string using Fernet and return a base64 string."""
    f = get_fernet(settings)
    return f.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_text(token: str, settings: Settings) -> str:
    """Decrypt a Fernet token back into its plaintext string."""
    f = get_fernet(settings)
    return f.decrypt(token.encode("utf-8")).decode("utf-8")
