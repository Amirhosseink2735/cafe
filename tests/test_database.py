"""Schema creation and Persian text persistence tests."""

from __future__ import annotations

from pathlib import Path

from database.db_manager import REQUIRED_TABLES, DatabaseManager
from utils.jalali_helper import JalaliHelper


def test_initialize_creates_all_tables(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()

    names = db.table_names()
    for table in REQUIRED_TABLES:
        assert table in names


def test_persian_employee_name_roundtrip(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()

    persian_name = "علی رضایی"
    personnel_code = "۱۴۰۳۰۱"
    created_at = JalaliHelper.now_datetime_str()

    employee_id = db.insert_employee(
        full_name=persian_name,
        personnel_code=personnel_code,
        phone="۰۹۱۲۳۴۵۶۷۸۹",
        hourly_rate=85000,
        created_at=created_at,
    )
    assert employee_id > 0

    row = db.get_employee_by_code(personnel_code)
    assert row is not None
    assert row["full_name"] == persian_name
    assert row["personnel_code"] == personnel_code
    assert row["phone"] == "۰۹۱۲۳۴۵۶۷۸۹"
    assert row["created_at"] == created_at


def test_duplicate_attendance_same_day_rejected(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    employee_id = db.insert_employee("علی محمدی", "1001")
    db.insert_attendance(employee_id, JalaliHelper.today_str(), "08:00:00")
    try:
        db.insert_attendance(employee_id, JalaliHelper.today_str(), "09:00:00")
        raise AssertionError("expected duplicate attendance to fail")
    except ValueError as exc:
        assert "تردد" in str(exc)


def test_jalali_today_format() -> None:
    today = JalaliHelper.today_str()
    parts = today.split("/")
    assert len(parts) == 3
    year, month, day = (int(part) for part in parts)
    assert year >= 1400
    assert 1 <= month <= 12
    assert 1 <= day <= 31
