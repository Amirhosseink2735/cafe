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


def test_role_buttons_destroy_window_and_keep_choice(db: DatabaseManager) -> None:
    """Button release must actually close the home window so main() can open the next one."""
    import tkinter as tk

    from gui.role_window import RoleWindow

    home = RoleWindow(db)
    home.withdraw()
    home.update()
    buttons = []

    def walk(widget) -> None:
        for child in widget.winfo_children():
            if type(child).__name__ == "CTkButton":
                buttons.append(child)
            walk(child)

    walk(home)
    assert len(buttons) >= 2
    try:
        buttons[0]._mouse_inside = True
        buttons[0]._on_release()
        assert home.choice == "kiosk"
        with pytest.raises(tk.TclError):
            home.winfo_exists()
    finally:
        try:
            if home.winfo_exists():
                home.destroy()
        except tk.TclError:
            pass

    home = RoleWindow(db)
    home.withdraw()
    home.update()
    buttons.clear()
    walk(home)
    try:
        buttons[1]._mouse_inside = True
        buttons[1]._on_release()
        assert home.choice == "admin"
        with pytest.raises(tk.TclError):
            home.winfo_exists()
    finally:
        try:
            if home.winfo_exists():
                home.destroy()
        except tk.TclError:
            pass


def test_packaged_self_test_runner(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CAFE_USER_DATA", str(tmp_path / "install data"))
    from app.self_test import run_self_test

    assert run_self_test() == 0
    log = (tmp_path / "install data" / "self_test_result.txt").read_text(encoding="utf-8")
    assert log.startswith("OK")
    assert "excel=" in log
    assert (tmp_path / "install data" / "self_test_report.xlsx").exists()


def test_wrong_then_right_password(db: DatabaseManager) -> None:
    auth = AuthService(db)
    assert auth.verify_password("admin") is True
    assert auth.verify_password("nope") is False
