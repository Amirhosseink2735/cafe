"""Employment history, absence, backup, and database error tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from database.db_manager import CORE_TABLES, DatabaseManager
from services.auth_service import PBKDF2_SCHEME, hash_password
from services.backup_service import BackupService
from services.payroll_service import PayrollService, was_active_on
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


@pytest.fixture
def history_db(tmp_path: Path):
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    staff = StaffService(db)
    employee_id = staff.save_employee("علی", "محمدی", "1001", "", "150000")
    staff.save_shift(employee_id, "08:00", "16:00", "5")
    return db, staff, PayrollService(db), employee_id


def test_was_active_on_uses_latest_event_not_after_day() -> None:
    events = [("1403/07/01", True), ("1403/07/10", False), ("1403/07/20", True)]
    assert was_active_on("1403/07/05", events, "1403/07/01") is True
    assert was_active_on("1403/07/10", events, "1403/07/01") is False
    assert was_active_on("1403/07/15", events, "1403/07/01") is False
    assert was_active_on("1403/07/20", events, "1403/07/01") is True
    assert was_active_on("1403/06/20", events, "1403/07/01") is False


def test_inactive_span_is_not_absence(history_db) -> None:
    db, staff, payroll, employee_id = history_db
    with db.connect() as connection:
        connection.execute(
            "UPDATE employees SET created_at = ? WHERE id = ?",
            ("1403/07/01 08:00:00", employee_id),
        )
        connection.execute(
            "UPDATE employment_events SET jalali_date = ? WHERE employee_id = ?",
            ("1403/07/01", employee_id),
        )
        connection.commit()

    payroll.attendance.save_manual_entry(employee_id, "1403/07/05", "08:00", "16:00")
    staff.deactivate_employee(employee_id, jalali_date="1403/07/10")
    staff.activate_employee(employee_id, jalali_date="1403/07/20")

    summary = next(item for item in payroll.month_summaries(1403, 7) if item.employee_id == employee_id)
    start, end = JalaliHelper.month_bounds(1403, 7)
    days = list(JalaliHelper.iter_dates(start, end))
    events = [
        (row["jalali_date"], bool(row["is_active"]))
        for row in db.list_employment_events(employee_id)
    ]
    expected = sum(
        1
        for day in days
        if was_active_on(day, events, "1403/07/01")
        and day != "1403/07/05"
    )
    assert summary.completed_days == 1
    assert summary.absence_days == expected
    assert expected < len(days) - 1


def test_currently_inactive_employee_has_no_absence_after_deactivate(history_db) -> None:
    db, staff, payroll, employee_id = history_db
    with db.connect() as connection:
        connection.execute(
            "UPDATE employees SET created_at = ? WHERE id = ?",
            ("1403/07/01 08:00:00", employee_id),
        )
        connection.execute(
            "UPDATE employment_events SET jalali_date = ? WHERE employee_id = ?",
            ("1403/07/01", employee_id),
        )
        connection.commit()
    staff.deactivate_employee(employee_id, jalali_date="1403/07/01")
    summary = next(item for item in payroll.month_summaries(1403, 7) if item.employee_id == employee_id)
    assert summary.absence_days == 0


def test_staff_status_history_is_recorded(history_db) -> None:
    _db, staff, _payroll, employee_id = history_db
    staff.deactivate_employee(employee_id)
    staff.activate_employee(employee_id)
    events = _db.list_employment_events(employee_id)
    assert len(events) >= 3
    assert bool(events[-1]["is_active"]) is True
    assert bool(events[-2]["is_active"]) is False


def test_backup_restore_and_invalid_files(history_db, tmp_path: Path) -> None:
    db, staff, _payroll, _employee_id = history_db
    backups = BackupService(db)
    dest = tmp_path / "ok.db"
    backups.backup_to(dest)
    staff.save_employee("سارا", "کاظمی", "2002", "", "100000")
    backups.restore_from(dest)
    codes = {emp.personnel_code for emp in staff.list_employees()}
    assert "2002" not in codes
    assert "1001" in codes

    junk = tmp_path / "bad.db"
    junk.write_bytes(b"not a database")
    with pytest.raises(ValueError):
        backups.restore_from(junk)


def test_legacy_backup_without_employment_table_restores(tmp_path: Path) -> None:
    src_db = DatabaseManager(tmp_path / "legacy.db")
    src_db.initialize()
    src_db.insert_employee("علی محمدی", "1001", hourly_rate=150000, created_at="1403/07/01 08:00:00")
    with src_db.connect() as connection:
        connection.execute("DROP TABLE employment_events")
        connection.commit()
    tables = {
        row[0]
        for row in sqlite3.connect(src_db.db_path)
        .execute("SELECT name FROM sqlite_master WHERE type='table'")
        .fetchall()
    }
    assert "employment_events" not in tables
    assert set(CORE_TABLES).issubset(tables)

    live = DatabaseManager(tmp_path / "live.db")
    live.initialize()
    BackupService(live).restore_from(src_db.db_path)
    assert "employment_events" in live.table_names()
    names = {row["personnel_code"] for row in live.list_employees_with_shifts()}
    assert "1001" in names
    events = live.list_employment_events(1)
    assert events


def test_corrupt_database_initialize_fails(tmp_path: Path) -> None:
    path = tmp_path / "cafe.db"
    path.write_text("this is not sqlite", encoding="utf-8")
    db = DatabaseManager(path)
    with pytest.raises(sqlite3.Error):
        db.initialize()


def test_pbkdf2_hashes_are_unique() -> None:
    first = hash_password("admin")
    second = hash_password("admin")
    assert first != second
    assert first.startswith(f"{PBKDF2_SCHEME}$")
