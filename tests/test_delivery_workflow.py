"""Drive the real form widgets through the daily workflow.

Windows stay withdrawn so the test does not block on dialogs. Button commands
are the same ones a click runs. This is not a claim of hands-on testing on a
clean PC.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from gui.style import apply_theme
from services.attendance_service import AttendanceService
from services.payroll_service import PayrollService
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


def _fill(entry, value: str) -> None:
    entry.delete(0, "end")
    entry.insert(0, value)


def _buttons(window):
    found = []

    def walk(widget) -> None:
        for child in widget.winfo_children():
            if type(child).__name__ == "CTkButton":
                found.append(child)
            walk(child)

    walk(window)
    return found


def _press_label(window, text: str) -> None:
    for button in _buttons(window):
        if button.cget("text") == text:
            button._mouse_inside = True
            button._on_release()
            return
    raise AssertionError(f"button not found: {text}")


@pytest.fixture
def db(tmp_path: Path) -> DatabaseManager:
    manager = DatabaseManager(tmp_path / "cafe.db")
    manager.initialize()
    apply_theme("light")
    return manager


def test_admin_kiosk_report_and_clean_exit(db: DatabaseManager, tmp_path: Path, monkeypatch) -> None:
    import tkinter as tk

    from gui.admin_window import AdminWindow
    from gui.kiosk_window import KioskWindow
    from gui.login_window import LoginWindow
    from gui.report_frame import ReportFrame
    from gui.role_window import RoleWindow

    monkeypatch.setattr(
        "gui.report_frame.filedialog.asksaveasfilename",
        lambda **_kwargs: str(tmp_path / "vibe coding" / "گزارش.xlsx"),
    )
    monkeypatch.setattr("gui.report_frame.messagebox.showinfo", lambda *_a, **_k: None)
    monkeypatch.setattr("gui.report_frame.messagebox.showerror", lambda *_a, **_k: None)
    (tmp_path / "vibe coding").mkdir()

    home = RoleWindow(db)
    home.withdraw()
    home.update()
    _press_label(home, "پنل مدیر")
    assert home.choice == "admin"
    with pytest.raises(tk.TclError):
        home.winfo_exists()

    login = LoginWindow(db)
    login.withdraw()
    login.update()
    _fill(login.password_entry, "wrong")
    login._login()
    assert login.authenticated is False
    assert login.winfo_exists()
    _fill(login.password_entry, "admin")
    login._login()
    assert login.authenticated is True

    admin = AdminWindow(db)
    admin.withdraw()
    admin.update()
    _fill(admin.first_name_entry, "نگار")
    _fill(admin.last_name_entry, "کریمی")
    _fill(admin.code_entry, "4404")
    _fill(admin.phone_entry, "09120000000")
    _fill(admin.rate_entry, "180000")
    _press_label(admin, "ذخیره کارمند")
    employee = StaffService(db).get_employee(admin.selected_employee_id)
    assert employee is not None
    assert employee.personnel_code == "4404"

    _fill(admin.start_entry, "22:00")
    _fill(admin.end_entry, "06:00")
    _fill(admin.tolerance_entry, "10")
    _press_label(admin, "ذخیره شیفت")
    stored = StaffService(db).get_employee(employee.id)
    assert stored.shift_start.startswith("22:00")
    assert stored.shift_end.startswith("06:00")

    metrics = AttendanceService(db).compute_metrics(employee.id, "21:50:00", "06:10:00")
    assert metrics.delay_minutes == 0

    today = JalaliHelper.today()
    summaries = PayrollService(db).month_summaries(today.year, today.month)
    row = next(item for item in summaries if item.employee_id == employee.id)
    assert row.absence_days >= 0

    admin.tabs.set("گزارش ماهانه تردد")
    admin.report_frame.refresh()
    assert isinstance(admin.report_frame, ReportFrame)
    labels = []

    def walk(widget) -> None:
        for child in widget.winfo_children():
            if type(child).__name__ == "CTkLabel":
                labels.append(child)
            walk(child)

    walk(admin.report_frame.list_frame)
    header = next(label for label in labels if label.cget("text") == "وضعیت روز")
    assert str(header.grid_info()["column"]) == "8"

    admin.report_frame._export_excel()
    workbook = tmp_path / "vibe coding" / "گزارش.xlsx"
    assert workbook.exists()
    assert workbook.stat().st_size > 0

    _press_label(admin, "خروج")
    assert admin.logout_requested is True

    kiosk_home = RoleWindow(db)
    kiosk_home.withdraw()
    kiosk_home.update()
    _press_label(kiosk_home, "کیوسک پرسنل")
    assert kiosk_home.choice == "kiosk"

    kiosk = KioskWindow(db)
    kiosk.withdraw()
    kiosk.update()
    kiosk._on_combo_select("نگار کریمی  |  4404")
    kiosk.check_in_button.invoke()
    assert kiosk.attendance.current_status(employee.id).is_inside is True
    kiosk.check_in_button.invoke()
    assert kiosk.attendance.current_status(employee.id).is_inside is True
    kiosk.check_out_button.invoke()
    assert kiosk.attendance.current_status(employee.id).is_inside is False
    kiosk._on_close()
    with pytest.raises(tk.TclError):
        kiosk.winfo_exists()

    closing = RoleWindow(db)
    closing.withdraw()
    closing.update()
    from gui.style import close_window

    close_window(closing)
    assert closing.choice is None
