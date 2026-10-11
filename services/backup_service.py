"""Copy the SQLite database to a backup file and restore from one."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from database.db_manager import CORE_TABLES, DatabaseManager


class BackupService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def backup_to(self, destination: str | Path) -> Path:
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(self.db.db_path) as source, sqlite3.connect(dest) as target:
                source.backup(target)
        except (OSError, sqlite3.Error) as exc:
            raise ValueError("ذخیره نسخه پشتیبان ممکن نشد.") from exc
        return dest

    def restore_from(self, source: str | Path) -> Path:
        src = Path(source)
        live = Path(self.db.db_path)
        if src.resolve() == live.resolve():
            raise ValueError("نمی‌توان فایل پایگاه داده در حال استفاده را به‌عنوان پشتیبان انتخاب کرد.")
        if not src.exists() or src.stat().st_size == 0:
            raise ValueError("فایل پشتیبان معتبر نیست.")
        self._assert_cafe_backup(src)
        try:
            incoming = sqlite3.connect(src)
            target = sqlite3.connect(live)
            try:
                incoming.backup(target)
                target.commit()
            finally:
                target.close()
                incoming.close()
        except (OSError, sqlite3.Error) as exc:
            raise ValueError("بازیابی ممکن نشد. فایل پشتیبان خراب است یا مسیر قابل نوشتن نیست.") from exc
        self.db.initialize()
        return live

    def _assert_cafe_backup(self, src: Path) -> None:
        try:
            with sqlite3.connect(src) as incoming:
                incoming.execute("SELECT 1 FROM sqlite_master LIMIT 1")
                tables = {
                    row[0]
                    for row in incoming.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    ).fetchall()
                }
        except sqlite3.Error as exc:
            raise ValueError("این فایل دیتابیس معتبر نیست.") from exc
        if not set(CORE_TABLES).issubset(tables):
            raise ValueError("این فایل دیتابیس برنامه نیست.")
