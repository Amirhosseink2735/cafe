"""Phase 6 bonus, deduction, and monthly payroll tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from services.leave_service import LEAVE_DAILY, LeaveService
from services.payroll_service import TYPE_BONUS, TYPE_DEDUCTION, PayrollService
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


@pytest.fixture
def payroll_setup(tmp_path: Path) -> tuple[PayrollService, StaffService, LeaveService, int]:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    staff = StaffService(db)
    employee_id = staff.save_employee("علی", "محمدی", "1001", "", "150000")
    staff.save_shift(employee_id, "08:00", "16:00", "5")
    return PayrollService(db), staff, LeaveService(db), employee_id


def test_bonus_and_deduction_roundtrip(payroll_setup) -> None:
    payroll, _staff, _leave, employee_id = payroll_setup
    today = JalaliHelper.today_str()
    payroll.add_adjustment(employee_id, TYPE_BONUS, "۲۰۰۰۰۰", "فروش خوب", today)
    payroll.add_adjustment(employee_id, TYPE_DEDUCTION, "50000", "کسری صندوق", today)
    items = payroll.list_adjustments()
    assert len(items) == 2
    bonus = next(item for item in items if item.type == TYPE_BONUS)
    deduction = next(item for item in items if item.type == TYPE_DEDUCTION)
    assert bonus.amount == 200000
    assert bonus.reason == "فروش خوب"
    assert deduction.amount == 50000


def test_monthly_hours_subtract_delay_and_add_overtime(payroll_setup) -> None:
    payroll, _staff, _leave, employee_id = payroll_setup
    today = JalaliHelper.today_str()
    payroll.attendance.check_in(employee_id, jalali_date=today, check_in_time="08:20:00")
    payroll.attendance.check_out(employee_id, jalali_date=today, check_out_time="16:30:00")
    payroll.add_adjustment(employee_id, TYPE_BONUS, "100000", "پاداش", today)
    payroll.add_adjustment(employee_id, TYPE_DEDUCTION, "25000", "کسورات", today)

    summary = payroll.month_summaries()[0]
    # 8h shift - 15 penalized delay + 30 overtime = 495 minutes
    assert summary.worked_minutes == 495
    assert summary.delay_minutes == 20
    assert summary.penalized_delay_minutes == 15
    assert summary.overtime_minutes == 30
    assert summary.bonus_total == 100000
    assert summary.deduction_total == 25000
    assert summary.base_pay == 495 / 60 * 150000
    assert summary.net_pay == summary.base_pay + 100000 - 25000


def test_approved_daily_leave_is_not_unauthorized_absence(payroll_setup) -> None:
    payroll, _staff, leave, employee_id = payroll_setup
    start, end = JalaliHelper.month_bounds()
    until = min(JalaliHelper.today_str(), end)
    days = list(JalaliHelper.iter_dates(start, until))
    work_day = days[-1]
    payroll.attendance.check_in(employee_id, jalali_date=work_day, check_in_time="08:00:00")
    payroll.attendance.check_out(employee_id, jalali_date=work_day, check_out_time="16:00:00")

    leave_day = days[0]
    request_id = leave.submit_request(
        employee_id=employee_id,
        leave_type=LEAVE_DAILY,
        reason="مرخصی",
        start_date=leave_day,
        end_date=leave_day,
    )
    leave.approve(request_id, "تایید شد")

    summary = payroll.month_summaries()[0]
    hire_date = JalaliHelper.today_str()
    expected_absence = sum(
        1
        for day in days
        if day != hire_date
        and day >= hire_date
        and day != work_day
        and day != leave_day
    )
    assert summary.completed_days == 1
    assert summary.absence_days == expected_absence


def test_adjustment_requires_reason_and_amount(payroll_setup) -> None:
    payroll, _staff, _leave, employee_id = payroll_setup
    with pytest.raises(ValueError, match="دلیل"):
        payroll.add_adjustment(employee_id, TYPE_BONUS, "1000", "  ")
    with pytest.raises(ValueError, match="مبلغ"):
        payroll.add_adjustment(employee_id, TYPE_DEDUCTION, "0", "دلیل")
