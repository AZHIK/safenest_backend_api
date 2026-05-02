from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


def get_fernet_key(key: str) -> bytes:
    """Generate Fernet key from string."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=settings.encryption_key[:16].encode(),
        iterations=100000,
    )
    key_bytes = base64.urlsafe_b64encode(kdf.derive(key.encode()))
    return key_bytes


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data using Fernet symmetric encryption.

    Note: This is for server-side data encryption only.
    Client-side encrypted data should NOT be decrypted on the server.
    """
    try:
        key = get_fernet_key(settings.encryption_key)
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        logger.error("encryption_failed", error=str(e))
        raise


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt server-side encrypted data."""
    try:
        key = get_fernet_key(settings.encryption_key)
        f = Fernet(key)
        decrypted = f.decrypt(base64.b64decode(encrypted_data))
        return decrypted.decode()
    except Exception as e:
        logger.error("decryption_failed", error=str(e))
        raise


def hash_sensitive_data(data: str) -> str:
    """One-way hash for sensitive data comparison (e.g., search)."""
    import hashlib
    return hashlib.sha256(
        (data + settings.encryption_key).encode()
    ).hexdigest()


def generate_data_encryption_key() -> bytes:
    """Generate a new Data Encryption Key (DEK) for client-side encryption."""
    return Fernet.generate_key()


def encrypt_dek_with_kek(dek: bytes, kek: str) -> str:
    """Encrypt DEK with Key Encryption Key (KEK) for secure storage."""
    key = get_fernet_key(kek)
    f = Fernet(key)
    encrypted = f.encrypt(dek)
    return base64.b64encode(encrypted).decode()


def decrypt_dek_with_kek(encrypted_dek: str, kek: str) -> bytes:
    """Decrypt DEK with KEK."""
    key = get_fernet_key(kek)
    f = Fernet(key)
    return f.decrypt(base64.b64decode(encrypted_dek))
