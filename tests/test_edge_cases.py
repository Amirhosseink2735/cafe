"""Phase 7 edge cases: month boundary, overnight shifts, multiple leaves."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from services.leave_service import LEAVE_DAILY, LEAVE_HOURLY, LeaveService
from services.payroll_service import PayrollService
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


@pytest.fixture
def edge_services(tmp_path: Path):
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    staff = StaffService(db)
    employee_id = staff.save_employee("سارا", "کاظمی", "7007", "", "100000")
    payroll = PayrollService(db)
    leave = LeaveService(db)
    return staff, payroll, leave, employee_id


def test_month_change_keeps_payroll_in_the_correct_month(edge_services) -> None:
    _staff, payroll, _leave, employee_id = edge_services
    _start, esfand_last = JalaliHelper.month_bounds(1403, 12)
    farvardin_first, _end = JalaliHelper.month_bounds(1404, 1)

    payroll.attendance.save_manual_entry(employee_id, esfand_last, "08:00", "16:00")
    payroll.attendance.save_manual_entry(employee_id, farvardin_first, "08:00", "16:00")

    esfand = next(item for item in payroll.month_summaries(1403, 12) if item.employee_id == employee_id)
    farvardin = next(item for item in payroll.month_summaries(1404, 1) if item.employee_id == employee_id)
    assert esfand.completed_days == 1
    assert farvardin.completed_days == 1


def test_exact_shift_boundaries_have_zero_penalties(edge_services) -> None:
    staff, payroll, _leave, employee_id = edge_services
    staff.save_shift(employee_id, "08:00", "16:00", "5")
    metrics = payroll.attendance.compute_metrics(employee_id, "08:00:00", "16:00:00")
    assert metrics.delay_minutes == 0
    assert metrics.early_leave_minutes == 0
    assert metrics.overtime_minutes == 0

    at_tolerance = payroll.attendance.compute_metrics(employee_id, "08:05:00", "16:00:00")
    assert at_tolerance.delay_minutes == 5
    assert at_tolerance.penalized_delay_minutes == 0


def test_overnight_shift_metrics(edge_services) -> None:
    staff, payroll, _leave, employee_id = edge_services
    staff.save_shift(employee_id, "22:00", "06:00", "10")
    on_time = payroll.attendance.compute_metrics(employee_id, "22:00:00", "06:00:00")
    assert on_time.delay_minutes == 0
    assert on_time.early_leave_minutes == 0
    assert on_time.overtime_minutes == 0

    late = payroll.attendance.compute_metrics(employee_id, "22:20:00", "05:30:00")
    assert late.delay_minutes == 20
    assert late.penalized_delay_minutes == 10
    assert late.early_leave_minutes == 30

    overtime = payroll.attendance.compute_metrics(employee_id, "22:00:00", "06:15:00")
    assert overtime.overtime_minutes == 15

    early = payroll.attendance.compute_metrics(employee_id, "21:50:00", "06:00:00")
    assert early.delay_minutes == 0


def test_multiple_leave_requests_on_same_day(edge_services) -> None:
    _staff, _payroll, leave, employee_id = edge_services
    day = JalaliHelper.today_str()
    first = leave.submit_request(
        employee_id, LEAVE_HOURLY, "پزشک صبح", day, start_time="09:00", end_time="11:00"
    )
    second = leave.submit_request(
        employee_id, LEAVE_HOURLY, "اداره", day, start_time="13:00", end_time="15:00"
    )
    third = leave.submit_request(employee_id, LEAVE_DAILY, "کار شخصی", day, end_date=day)
    pending = leave.list_requests("pending")
    assert {item.id for item in pending} >= {first, second, third}
    leave.approve(first, "تایید ساعتی اول")
    leave.reject(second, "نیروی کافی نیست")
    statuses = {item.id: item.status for item in leave.list_requests()}
    assert statuses[first] == "approved"
    assert statuses[second] == "rejected"
    assert statuses[third] == "pending"
    with pytest.raises(ValueError, match="مرخصی روزانه"):
        leave.submit_request(employee_id, LEAVE_DAILY, "تکراری", day, end_date=day)
    with pytest.raises(ValueError, match="تداخل"):
        leave.submit_request(
            employee_id, LEAVE_HOURLY, "همپوشان", day, start_time="09:30", end_time="10:30"
        )
