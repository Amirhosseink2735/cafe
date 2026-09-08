"""Application entry point. GUI screens will be added in later phases."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager


def bootstrap() -> DatabaseManager:
    db = DatabaseManager()
    db.initialize()
    return db


def main() -> None:
    bootstrap()
    print("پایگاه داده کافه آماده است. رابط کاربری در فازهای بعدی اضافه می‌شود.")


if __name__ == "__main__":
    main()
