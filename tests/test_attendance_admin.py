"""Phase 5 delay, missed checkout, and manual attendance tests."""

from __future__ import annotations

import datetime
from pathlib import Path

import jdatetime
import pytest

from database.db_manager import DatabaseManager
from services.attendance_service import AttendanceService, STATUS_MISSED
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


def _yesterday() -> str:
    return (jdatetime.date.today() - datetime.timedelta(days=1)).strftime("%Y/%m/%d")


@pytest.fixture
def attendance_setup(tmp_path: Path) -> tuple[AttendanceService, int]:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    staff = StaffService(db)
    employee_id = staff.save_employee("علی", "محمدی", "1001", "", "150000")
    staff.save_shift(employee_id, "08:00", "16:00", "5")
    return AttendanceService(db), employee_id


def test_delay_early_leave_and_overtime(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    metrics_in = attendance.compute_metrics(employee_id, "08:20:00")
    assert metrics_in.delay_minutes == 20
    assert metrics_in.penalized_delay_minutes == 15

    metrics_early = attendance.compute_metrics(employee_id, "08:00:00", "15:40:00")
    assert metrics_early.early_leave_minutes == 20
    assert metrics_early.overtime_minutes == 0

    metrics_ot = attendance.compute_metrics(employee_id, "08:00:00", "16:45:00")
    assert metrics_ot.overtime_minutes == 45
    assert metrics_ot.early_leave_minutes == 0


def test_tolerance_does_not_erase_raw_delay(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    metrics = attendance.compute_metrics(employee_id, "08:04:00")
    assert metrics.delay_minutes == 4
    assert metrics.penalized_delay_minutes == 0


def test_open_record_from_previous_day_becomes_missed(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    yesterday = _yesterday()
    attendance.db.insert_attendance(
        employee_id=employee_id,
        jalali_date=yesterday,
        check_in="08:10:00",
        status="open",
    )
    marked = attendance.mark_missed_checkouts(JalaliHelper.today_str())
    assert marked == 1
    incomplete = attendance.list_incomplete()
    assert len(incomplete) == 1
    assert incomplete[0].status == STATUS_MISSED
    assert incomplete[0].check_in == "08:10:00"


def test_today_open_checkin_is_not_missed(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    today = JalaliHelper.today_str()
    attendance.check_in(employee_id, jalali_date=today, check_in_time="08:00:00")
    attendance.mark_missed_checkouts(today)
    row = attendance.db.get_open_attendance(employee_id, today)
    assert row is not None
    assert row["status"] == "open"
    assert attendance.list_incomplete()[0].status == "open"


def test_admin_completes_missed_checkout_as_manual(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    yesterday = _yesterday()
    attendance.check_in(employee_id, jalali_date=yesterday, check_in_time="08:00:00")
    attendance.mark_missed_checkouts()
    item = attendance.list_incomplete()[0]
    attendance.complete_missed_checkout(item.id, "16:10")
    row = attendance.db.get_attendance_by_id(item.id)
    assert row is not None
    assert row["status"] == "completed"
    assert row["check_out"] == "16:10:00"
    assert row["is_manual_entry"] == 1
    assert row["overtime_minutes"] == 10
    assert attendance.list_incomplete() == []


def test_manual_full_entry_sets_flag(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    today = JalaliHelper.today_str()
    attendance_id = attendance.save_manual_entry(
        employee_id=employee_id,
        jalali_date=today,
        check_in_time="09:00",
        check_out_time="17:00",
    )
    row = attendance.db.get_attendance_by_id(attendance_id)
    assert row is not None
    assert row["is_manual_entry"] == 1
    assert row["status"] == "completed"
    assert row["delay_minutes"] == 60
    assert row["overtime_minutes"] == 60
    assert row["check_in"] == "09:00:00"
    assert row["check_out"] == "17:00:00"


def test_day_shift_status_ignores_yesterday(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    yesterday = _yesterday()
    attendance.db.insert_attendance(
        employee_id=employee_id,
        jalali_date=yesterday,
        check_in="08:00:00",
        status="open",
    )
    attendance.db.complete_attendance(
        attendance_id=attendance.db.get_open_attendance(employee_id, yesterday)["id"],
        check_out="16:00:00",
        early_leave_minutes=0,
        overtime_minutes=0,
    )
    status = attendance.current_status(employee_id)
    assert status.is_inside is False
    assert "امروز هنوز" in status.detail


def test_overnight_checkout_after_midnight(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    StaffService(attendance.db).save_shift(employee_id, "22:00", "06:00", "10")
    yesterday = _yesterday()
    today = JalaliHelper.today_str()
    attendance.db.insert_attendance(
        employee_id=employee_id,
        jalali_date=yesterday,
        check_in="22:10:00",
        status="open",
    )
    status = attendance.check_out(employee_id, jalali_date=today, check_out_time="05:40:00")
    assert status.is_inside is False
    row = attendance.db.get_latest_attendance(employee_id, yesterday)
    assert row is not None
    assert row["check_out"] == "05:40:00"
    assert row["status"] == "completed"


def test_overnight_early_arrival_is_not_a_day_late(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    StaffService(attendance.db).save_shift(employee_id, "22:00", "06:00", "10")
    metrics = attendance.compute_metrics(employee_id, "21:50:00", "06:00:00")
    assert metrics.delay_minutes == 0
    assert metrics.early_leave_minutes == 0
    assert metrics.overtime_minutes == 0


def test_cannot_check_in_twice_after_checkout(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    today = JalaliHelper.today_str()
    attendance.check_in(employee_id, jalali_date=today, check_in_time="08:00:00")
    attendance.check_out(employee_id, jalali_date=today, check_out_time="16:00:00")
    with pytest.raises(ValueError, match="تردد"):
        attendance.check_in(employee_id, jalali_date=today, check_in_time="16:30:00")


def test_inactive_employee_cannot_punch(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    StaffService(attendance.db).deactivate_employee(employee_id)
    with pytest.raises(ValueError, match="غیرفعال"):
        attendance.check_in(employee_id, check_in_time="08:00:00")


def test_inactive_employee_can_check_out_open_shift(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    today = JalaliHelper.today_str()
    attendance.check_in(employee_id, jalali_date=today, check_in_time="08:00:00")
    StaffService(attendance.db).deactivate_employee(employee_id)
    status = attendance.check_out(employee_id, jalali_date=today, check_out_time="16:00:00")
    assert status.is_inside is False
    assert status.check_out == "16:00:00"


def test_overnight_early_arrival_uses_today(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    StaffService(attendance.db).save_shift(employee_id, "22:00", "06:00", "10")
    yesterday = _yesterday()
    attendance.db.insert_attendance(
        employee_id=employee_id,
        jalali_date=yesterday,
        check_in="22:00:00",
        status="open",
    )
    attendance.db.complete_attendance(
        attendance.db.get_open_attendance(employee_id, yesterday)["id"],
        "06:00:00",
    )
    status = attendance.check_in(employee_id, check_in_time="21:50:00")
    today = JalaliHelper.today_str()
    row = attendance.db.get_latest_attendance(employee_id, today)
    assert row is not None
    assert row["jalali_date"] == today
    assert status.is_inside is True


def test_overnight_manual_morning_checkout(attendance_setup) -> None:
    attendance, employee_id = attendance_setup
    StaffService(attendance.db).save_shift(employee_id, "22:00", "06:00", "10")
    yesterday = _yesterday()
    attendance_id = attendance.db.insert_attendance(
        employee_id=employee_id,
        jalali_date=yesterday,
        check_in="22:00:00",
        status="open",
    )
    attendance.complete_missed_checkout(attendance_id, "06:15")
    row = attendance.db.get_attendance_by_id(attendance_id)
    assert row is not None
    assert row["check_out"] == "06:15:00"
    assert row["is_manual_entry"] == 1
    assert row["overtime_minutes"] == 15
