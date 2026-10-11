"""Bonuses, deductions, and Jalali monthly payroll summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database.db_manager import DatabaseManager
from services.attendance_service import AttendanceService
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper
from services.work_time import completed_day_minutes, unique_latest_rows
from utils.text_utils import normalize_jalali_date, parse_amount, shift_length_minutes

TYPE_BONUS = "bonus"
TYPE_DEDUCTION = "deduction"
TYPE_LABELS = {TYPE_BONUS: "پاداش", TYPE_DEDUCTION: "کسورات"}


@dataclass
class AdjustmentRecord:
    id: int
    employee_id: int
    employee_name: str
    personnel_code: str
    jalali_date: str
    type: str
    amount: float
    reason: str

    @property
    def type_label(self) -> str:
        return TYPE_LABELS.get(self.type, self.type)


@dataclass
class PayrollSummary:
    employee_id: int
    employee_name: str
    personnel_code: str
    hourly_rate: float
    worked_minutes: int
    delay_minutes: int
    penalized_delay_minutes: int
    early_leave_minutes: int
    overtime_minutes: int
    completed_days: int
    absence_days: int
    bonus_total: float
    deduction_total: float
    base_pay: float
    net_pay: float

    @property
    def worked_hours_label(self) -> str:
        hours, minutes = divmod(self.worked_minutes, 60)
        return f"{hours} ساعت و {minutes} دقیقه"


class PayrollService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self.staff = StaffService(db)
        self.attendance = AttendanceService(db)

    def add_adjustment(
        self,
        employee_id: int,
        adjustment_type: str,
        amount: str,
        reason: str,
        jalali_date: Optional[str] = None,
    ) -> int:
        if self.db.get_employee_by_id(employee_id) is None:
            raise ValueError("پرسنل را انتخاب کنید.")
        kind = adjustment_type.strip()
        if kind not in {TYPE_BONUS, TYPE_DEDUCTION}:
            raise ValueError("نوع باید پاداش یا کسورات باشد.")
        note = reason.strip()
        if not note:
            raise ValueError("دلیل را وارد کنید.")
        date_value = normalize_jalali_date(jalali_date or JalaliHelper.today_str())
        money = parse_amount(amount)
        return self.db.insert_adjustment(employee_id, date_value, kind, money, note)

    def list_adjustments(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        employee_id: Optional[int] = None,
    ) -> list[AdjustmentRecord]:
        start, end = start_date, end_date
        if not start or not end:
            start, end = JalaliHelper.month_bounds()
        rows = self.db.list_adjustments(start, end, employee_id)
        return [
            AdjustmentRecord(
                id=row["id"],
                employee_id=row["employee_id"],
                employee_name=row["full_name"],
                personnel_code=row["personnel_code"],
                jalali_date=row["jalali_date"],
                type=row["type"],
                amount=float(row["amount"]),
                reason=row["reason"],
            )
            for row in rows
        ]

    def month_summaries(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> list[PayrollSummary]:
        start, end = JalaliHelper.month_bounds(year, month)
        today = JalaliHelper.today_str()
        until = min(today, end)
        employees = self.staff.list_employees(include_inactive=True)
        attendances = self.db.list_attendances_in_range(start, end)
        adjustments = self.db.list_adjustments(start, end)
        leaves = self.db.list_approved_daily_leaves(start, until)

        by_employee_att: dict[int, list] = {}
        for row in attendances:
            by_employee_att.setdefault(row["employee_id"], []).append(row)
        by_employee_adj: dict[int, list] = {}
        for row in adjustments:
            by_employee_adj.setdefault(row["employee_id"], []).append(row)
        leave_days: dict[int, set[str]] = {}
        for row in leaves:
            covered_start = max(row["start_date"], start)
            covered_end = min(row["end_date"] or row["start_date"], until)
            days = set(JalaliHelper.iter_dates(covered_start, covered_end))
            leave_days.setdefault(row["employee_id"], set()).update(days)

        month_days = list(JalaliHelper.iter_dates(start, until))
        summaries: list[PayrollSummary] = []
        for employee in employees:
            rows = by_employee_att.get(employee.id, [])
            worked = 0
            delay = 0
            penalized = 0
            early = 0
            overtime = 0
            worked_dates: set[str] = set()
            completed_dates: set[str] = set()
            tolerance = employee.tolerance_minutes or 0
            shift_len = 0
            if employee.shift_start and employee.shift_end:
                shift_len = shift_length_minutes(employee.shift_start, employee.shift_end)
            for row in unique_latest_rows(rows):
                worked_dates.add(row["jalali_date"])
                day_minutes = completed_day_minutes(
                    row, employee.shift_start, employee.shift_end, tolerance
                )
                if day_minutes is None:
                    continue
                completed_dates.add(row["jalali_date"])
                delay_value = int(row["delay_minutes"] or 0)
                early_value = int(row["early_leave_minutes"] or 0)
                ot_value = int(row["overtime_minutes"] or 0)
                delay += delay_value
                penalized += max(delay_value - tolerance, 0)
                early += early_value
                overtime += ot_value
                worked += day_minutes

            approved = leave_days.get(employee.id, set())
            hire_date = (employee.created_at or "")[:10]
            absence = 0
            if employee.is_active and shift_len:
                absence = sum(
                    1
                    for day in month_days
                    if day != today
                    and (not hire_date or day >= hire_date)
                    and day not in worked_dates
                    and day not in approved
                )

            bonus = sum(
                float(row["amount"])
                for row in by_employee_adj.get(employee.id, [])
                if row["type"] == TYPE_BONUS
            )
            deduction = sum(
                float(row["amount"])
                for row in by_employee_adj.get(employee.id, [])
                if row["type"] == TYPE_DEDUCTION
            )
            rate = float(employee.hourly_rate or 0)
            base_pay = (worked / 60) * rate
            summaries.append(
                PayrollSummary(
                    employee_id=employee.id,
                    employee_name=employee.full_name,
                    personnel_code=employee.personnel_code,
                    hourly_rate=rate,
                    worked_minutes=worked,
                    delay_minutes=delay,
                    penalized_delay_minutes=penalized,
                    early_leave_minutes=early,
                    overtime_minutes=overtime,
                    completed_days=len(completed_dates),
                    absence_days=absence,
                    bonus_total=bonus,
                    deduction_total=deduction,
                    base_pay=base_pay,
                    net_pay=base_pay + bonus - deduction,
                )
            )
        summaries.sort(key=lambda item: item.employee_name)
        return summaries
