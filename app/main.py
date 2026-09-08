"""Application entry point for the cafe personnel desktop app."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db_manager import DatabaseManager
from gui.admin_window import AdminWindow
from gui.kiosk_window import KioskWindow
from gui.login_window import LoginWindow
from gui.role_window import RoleWindow
from gui.style import apply_theme


def bootstrap() -> DatabaseManager:
    db = DatabaseManager()
    db.initialize()
    return db


def run_gui(db: DatabaseManager) -> None:
    apply_theme()
    while True:
        home = RoleWindow(db)
        home.mainloop()
        choice = getattr(home, "choice", None)
        if choice == "kiosk":
            kiosk = KioskWindow(db)
            kiosk.mainloop()
        elif choice == "admin":
            login = LoginWindow(db)
            login.mainloop()
            if not getattr(login, "authenticated", False):
                continue
            admin = AdminWindow(db)
            admin.mainloop()
        else:
            return


def main() -> None:
    db = bootstrap()
    run_gui(db)


if __name__ == "__main__":
    main()
