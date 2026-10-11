"""Admin password authentication stored in the settings table."""

from __future__ import annotations

import hashlib
import hmac
import os

from database.db_manager import DatabaseManager

ADMIN_PASSWORD_KEY = "admin_password"
DEFAULT_PASSWORD = "admin"
PBKDF2_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return f"{PBKDF2_SCHEME}${iterations}${salt.hex()}${digest.hex()}"


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_stored_password(stored: str, password: str) -> tuple[bool, str | None]:
    """Return (accepted, upgraded_hash_or_None). Never returns the raw password."""
    if stored.startswith(f"{PBKDF2_SCHEME}$"):
        try:
            scheme, iter_text, salt_hex, digest_hex = stored.split("$", 3)
            iterations = int(iter_text)
            salt = bytes.fromhex(salt_hex)
        except ValueError:
            return False, None
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        if not hmac.compare_digest(candidate.hex(), digest_hex):
            return False, None
        if iterations < PBKDF2_ITERATIONS:
            return True, hash_password(password)
        return True, None
    if hmac.compare_digest(stored, _legacy_sha256(password)):
        return True, hash_password(password)
    if stored == password:
        return True, hash_password(password)
    return False, None


class AuthService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def verify_password(self, password: str) -> bool:
        password = password.strip()
        stored = self.db.get_setting(ADMIN_PASSWORD_KEY) or DEFAULT_PASSWORD
        ok, upgraded = verify_stored_password(stored, password)
        if ok and upgraded:
            self.db.set_setting(ADMIN_PASSWORD_KEY, upgraded)
        return ok

    def change_password(self, current_password: str, new_password: str) -> None:
        new_password = new_password.strip()
        if not new_password:
            raise ValueError("رمز جدید نمی‌تواند خالی باشد.")
        if len(new_password) < 4:
            raise ValueError("رمز جدید باید حداقل ۴ کاراکتر باشد.")
        if not self.verify_password(current_password):
            raise ValueError("رمز فعلی نادرست است.")
        self.db.set_setting(ADMIN_PASSWORD_KEY, hash_password(new_password))
