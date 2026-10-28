import hashlib
import secrets
from typing import Tuple, Optional


class AuthManager:
    """Lightweight, standard-library authentication using PBKDF2-HMAC-SHA256."""

    HASH_NAME = "sha256"
    ITERATIONS = 100_000

    @classmethod
    def hash_password(cls, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash password with PBKDF2-HMAC-SHA256.

        Returns (hex_hash, hex_salt).
        """
        if salt is None:
            salt = secrets.token_hex(16)
        pwd_bytes = password.encode("utf-8")
        salt_bytes = salt.encode("utf-8")
        derived = hashlib.pbkdf2_hmac(cls.HASH_NAME, pwd_bytes, salt_bytes, cls.ITERATIONS)
        return derived.hex(), salt

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        """Verify password against stored string in format 'hash$salt'."""
        if not stored_hash or "$" not in stored_hash:
            return False
        expected_hash, salt = stored_hash.split("$", 1)
        computed_hash, _ = cls.hash_password(password, salt=salt)
        return secrets.compare_digest(expected_hash, computed_hash)

