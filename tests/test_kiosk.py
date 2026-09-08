"""Phase 3 kiosk attendance and leave-request tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from services.attendance_service import AttendanceService
from services.leave_service import LEAVE_DAILY, LEAVE_HOURLY, LeaveService
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


@pytest.fixture
def services(tmp_path: Path) -> tuple[StaffService, AttendanceService, LeaveService, int]:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    staff = StaffService(db)
    employee_id = staff.save_employee("علی", "محمدی", "1001", "", "150000")
    staff.save_shift(employee_id, "08:00", "16:00", "5")
    return staff, AttendanceService(db), LeaveService(db), employee_id


def test_check_in_then_check_out_status(services) -> None:
    _staff, attendance, _leave, employee_id = services
    today = JalaliHelper.today_str()

    after_in = attendance.check_in(employee_id, jalali_date=today, check_in_time="08:10:00")
    assert after_in.is_inside is True
    assert after_in.label == "داخل کافه"

    after_out = attendance.check_out(employee_id, jalali_date=today, check_out_time="16:05:00")
    assert after_out.is_inside is False
    assert after_out.check_out == "16:05:00"


def test_cannot_check_out_without_check_in(services) -> None:
    _staff, attendance, _leave, employee_id = services
    with pytest.raises(ValueError, match="ورود"):
        attendance.check_out(employee_id, check_out_time="16:00:00")


def test_cannot_double_check_in(services) -> None:
    _staff, attendance, _leave, employee_id = services
    attendance.check_in(employee_id, check_in_time="08:00:00")
    with pytest.raises(ValueError, match="ورود"):
        attendance.check_in(employee_id, check_in_time="08:05:00")


def test_delay_and_overtime_are_stored(services) -> None:
    _staff, attendance, _leave, employee_id = services
    today = JalaliHelper.today_str()
    attendance.check_in(employee_id, jalali_date=today, check_in_time="08:20:00")
    attendance.check_out(employee_id, jalali_date=today, check_out_time="16:30:00")
    row = attendance.db.get_latest_attendance(employee_id, today)
    assert row is not None
    assert row["delay_minutes"] == 20
    assert row["overtime_minutes"] == 30
    assert row["status"] == "completed"


def test_daily_leave_is_pending(services) -> None:
    _staff, _attendance, leave, employee_id = services
    request_id = leave.submit_request(
        employee_id=employee_id,
        leave_type=LEAVE_DAILY,
        reason="کار شخصی",
        start_date=JalaliHelper.today_str(),
        end_date=JalaliHelper.today_str(),
    )
    assert request_id > 0
    with leave.db.connect() as connection:
        row = connection.execute(
            "SELECT * FROM leave_requests WHERE id = ?",
            (request_id,),
        ).fetchone()
    assert row["status"] == "pending"
    assert row["leave_type"] == LEAVE_DAILY
    assert row["reason"] == "کار شخصی"


def test_hourly_leave_requires_times(services) -> None:
    _staff, _attendance, leave, employee_id = services
    with pytest.raises(ValueError):
        leave.submit_request(
            employee_id=employee_id,
            leave_type=LEAVE_HOURLY,
            reason="پزشک",
            start_date=JalaliHelper.today_str(),
        )
