"""Instantiate main CustomTkinter windows and destroy them cleanly."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from gui.style import apply_theme, close_window
from services.auth_service import AuthService
from services.staff_service import StaffService


@pytest.fixture
def db(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "cafe.db")
    manager.initialize()
    staff = StaffService(manager)
    staff.save_employee("علی", "محمدی", "1001", "", "150000")
    apply_theme("light")
    return manager


def _show_and_close(window) -> None:
    window.withdraw()
    window.update_idletasks()
    window.update()
    assert window.winfo_exists()
    close_window(window)
    window.update()


def test_role_login_admin_kiosk_windows(db: DatabaseManager) -> None:
    from gui.admin_window import AdminWindow
    from gui.kiosk_window import KioskWindow
    from gui.login_window import LoginWindow
    from gui.role_window import RoleWindow

    home = RoleWindow(db)
    home.update_idletasks()
    assert "کافه" in home.title()
    _show_and_close(home)

    login = LoginWindow(db)
    login.update_idletasks()
    login.password_entry.insert(0, "wrong")
    login._login()
    assert login.authenticated is False
    assert login.error_label.cget("text")
    login.password_entry.insert(0, "admin")
    login._login()
    assert login.authenticated is True

    admin = AdminWindow(db)
    admin.update_idletasks()
    assert "مدیریت" in admin.title()
    admin.refresh_list()
    admin.report_frame.refresh()
    admin.payroll_frame.refresh()
    admin.attendance_inbox.refresh()
    admin.leave_inbox.refresh()
    _show_and_close(admin)

    kiosk = KioskWindow(db)
    kiosk.update_idletasks()
    kiosk.refresh_staff()
    _show_and_close(kiosk)


def test_wrong_then_right_password(db: DatabaseManager) -> None:
    auth = AuthService(db)
    assert auth.verify_password("admin") is True
    assert auth.verify_password("nope") is False
