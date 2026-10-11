"""Admin password authentication stored in the settings table."""

from __future__ import annotations

import hashlib

from database.db_manager import DatabaseManager

ADMIN_PASSWORD_KEY = "admin_password"
DEFAULT_PASSWORD = "admin"


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def verify_password(self, password: str) -> bool:
        password = password.strip()
        stored = self.db.get_setting(ADMIN_PASSWORD_KEY) or DEFAULT_PASSWORD
        if stored == hash_password(password):
            return True
        if stored == password:
            self.db.set_setting(ADMIN_PASSWORD_KEY, hash_password(password))
            return True
        return False

    def change_password(self, current_password: str, new_password: str) -> None:
        new_password = new_password.strip()
        if not new_password:
            raise ValueError("رمز جدید نمی‌تواند خالی باشد.")
        if len(new_password) < 4:
            raise ValueError("رمز جدید باید حداقل ۴ کاراکتر باشد.")
        if not self.verify_password(current_password):
            raise ValueError("رمز فعلی نادرست است.")
        self.db.set_setting(ADMIN_PASSWORD_KEY, hash_password(new_password))
