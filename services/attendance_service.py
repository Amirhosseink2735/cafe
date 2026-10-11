"""Staff check-in / check-out, shift metrics, and missed-punch handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database.db_manager import DatabaseManager
from utils.jalali_helper import JalaliHelper
from utils.text_utils import (
    align_to_shift,
    normalize_clock,
    normalize_jalali_date,
    shift_length_minutes,
    time_to_minutes,
)

STATUS_OPEN = "open"
STATUS_COMPLETED = "completed"
STATUS_MISSED = "missed_checkout"


@dataclass
class ShiftMetrics:
    delay_minutes: int
    penalized_delay_minutes: int
    early_leave_minutes: int
    overtime_minutes: int
    tolerance_minutes: int


@dataclass
class AttendanceStatus:
    is_inside: bool
    label: str
    detail: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: Optional[str] = None


@dataclass
class IncompleteAttendance:
    id: int
    employee_id: int
    employee_name: str
    personnel_code: str
    jalali_date: str
    check_in: str
    status: str
    delay_minutes: int
    is_manual_entry: bool

    @property
    def status_label(self) -> str:
        if self.status == STATUS_MISSED:
            return "خروج ثبت نشده"
        return "ورود باز"


class AttendanceService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def mark_missed_checkouts(self, today: Optional[str] = None) -> int:
        today = today or JalaliHelper.today_str()
        yesterday = JalaliHelper.shift_date(today, -1)
        now_minutes = time_to_minutes(JalaliHelper.now_time_str())
        marked = 0
        for row in self.db.list_open_attendances():
            if row["jalali_date"] >= today:
                continue
            overnight = self._is_overnight(row["employee_id"])
            if overnight and row["jalali_date"] == yesterday:
                shift = self.db.get_employee_with_shift(row["employee_id"])
                start_minutes = (
                    time_to_minutes(shift["start_time"]) if shift and shift["start_time"] else 0
                )
                # Keep the punch open through morning overtime until the next shift starts.
                if now_minutes < start_minutes:
                    continue
            self.db.set_attendance_status(row["id"], STATUS_MISSED)
            marked += 1
        return marked

    def current_status(self, employee_id: int, jalali_date: Optional[str] = None) -> AttendanceStatus:
        self.mark_missed_checkouts()
        jalali_date = jalali_date or JalaliHelper.today_str()
        open_row = self._open_row(employee_id, jalali_date)
        if open_row is not None:
            when = "امروز" if open_row["jalali_date"] == jalali_date else "شیفت جاری"
            return AttendanceStatus(
                is_inside=True,
                label="داخل کافه",
                detail=f"ورود {when} ساعت {open_row['check_in']}",
                check_in=open_row["check_in"],
                status=open_row["status"],
            )

        latest = self._latest_relevant(employee_id, jalali_date)
        if latest is None:
            return AttendanceStatus(
                is_inside=False,
                label="خارج از کافه",
                detail="امروز هنوز ترددی ثبت نشده است.",
            )
        if latest["check_out"]:
            return AttendanceStatus(
                is_inside=False,
                label="خارج از کافه",
                detail=f"آخرین خروج ساعت {latest['check_out']}",
                check_in=latest["check_in"],
                check_out=latest["check_out"],
                status=latest["status"],
            )
        if latest["status"] == STATUS_MISSED:
            return AttendanceStatus(
                is_inside=False,
                label="خارج از کافه",
                detail="ورود بدون خروج مانده؛ مدیر باید آن را اصلاح کند.",
                check_in=latest["check_in"],
                status=latest["status"],
            )
        return AttendanceStatus(
            is_inside=False,
            label="خارج از کافه",
            detail="امروز هنوز ترددی ثبت نشده است.",
        )

    def check_in(
        self,
        employee_id: int,
        jalali_date: Optional[str] = None,
        check_in_time: Optional[str] = None,
    ) -> AttendanceStatus:
        self._require_active(employee_id, "پرسنل انتخاب‌شده معتبر نیست.")
        self.mark_missed_checkouts()
        check_in_time = normalize_clock(check_in_time or JalaliHelper.now_time_str())
        jalali_date = self._resolve_checkin_date(employee_id, jalali_date, check_in_time)
        if self._open_row(employee_id, jalali_date) is not None:
            raise ValueError("ورود این پرسنل قبلاً ثبت شده و هنوز خروج نخورده است.")
        if self.db.get_latest_attendance(employee_id, jalali_date) is not None:
            raise ValueError("برای این تاریخ قبلاً تردد ثبت شده است.")

        metrics = self.compute_metrics(employee_id, check_in_time)
        self.db.insert_attendance(
            employee_id=employee_id,
            jalali_date=jalali_date,
            check_in=check_in_time,
            delay_minutes=metrics.delay_minutes,
        )
        return self.current_status(employee_id, jalali_date)

    def check_out(
        self,
        employee_id: int,
        jalali_date: Optional[str] = None,
        check_out_time: Optional[str] = None,
    ) -> AttendanceStatus:
        row = self.db.get_employee_by_id(employee_id)
        if row is None:
            raise ValueError("پرسنل انتخاب‌شده معتبر نیست.")
        jalali_date = jalali_date or JalaliHelper.today_str()
        check_out_time = normalize_clock(check_out_time or JalaliHelper.now_time_str())
        open_row = self._open_row(employee_id, jalali_date)
        if open_row is None:
            raise ValueError("برای این پرسنل ورود بازی وجود ندارد.")

        metrics = self.compute_metrics(employee_id, open_row["check_in"], check_out_time)
        self.db.complete_attendance(
            attendance_id=open_row["id"],
            check_out=check_out_time,
            early_leave_minutes=metrics.early_leave_minutes,
            overtime_minutes=metrics.overtime_minutes,
        )
        return self.current_status(employee_id, jalali_date)

    def incomplete_count(self) -> int:
        return len(self.list_incomplete())

    def list_incomplete(self) -> list[IncompleteAttendance]:
        self.mark_missed_checkouts()
        rows = self.db.list_incomplete_attendances()
        return [
            IncompleteAttendance(
                id=row["id"],
                employee_id=row["employee_id"],
                employee_name=row["full_name"],
                personnel_code=row["personnel_code"],
                jalali_date=row["jalali_date"],
                check_in=row["check_in"],
                status=row["status"],
                delay_minutes=row["delay_minutes"] or 0,
                is_manual_entry=bool(row["is_manual_entry"]),
            )
            for row in rows
        ]

    def complete_missed_checkout(self, attendance_id: int, check_out_time: str) -> None:
        row = self.db.get_attendance_by_id(attendance_id)
        if row is None:
            raise ValueError("رکورد تردد پیدا نشد.")
        if row["check_out"]:
            raise ValueError("برای این رکورد قبلاً خروج ثبت شده است.")
        check_out = normalize_clock(check_out_time)
        if self._checkout_before_checkin(row["employee_id"], row["check_in"], check_out):
            raise ValueError("ساعت خروج نمی‌تواند قبل از ساعت ورود باشد.")
        metrics = self.compute_metrics(row["employee_id"], row["check_in"], check_out)
        self.db.complete_attendance(
            attendance_id=attendance_id,
            check_out=check_out,
            early_leave_minutes=metrics.early_leave_minutes,
            overtime_minutes=metrics.overtime_minutes,
            is_manual_entry=True,
        )

    def save_manual_entry(
        self,
        employee_id: int,
        jalali_date: str,
        check_in_time: str,
        check_out_time: str = "",
    ) -> int:
        self._require_active(employee_id, "پرسنل را انتخاب کنید.")
        date_value = normalize_jalali_date(jalali_date)
        check_in = normalize_clock(check_in_time)
        check_out = normalize_clock(check_out_time) if check_out_time.strip() else None
        if check_out and self._checkout_before_checkin(employee_id, check_in, check_out):
            raise ValueError("ساعت خروج نمی‌تواند قبل از ساعت ورود باشد.")

        if self._open_row(employee_id, date_value) is not None:
            raise ValueError("برای این پرسنل در این تاریخ ورود باز وجود دارد.")
        if self.db.get_latest_attendance(employee_id, date_value) is not None:
            raise ValueError("برای این تاریخ قبلاً تردد ثبت شده است.")

        metrics = self.compute_metrics(employee_id, check_in, check_out)
        if check_out:
            status = STATUS_COMPLETED
        elif date_value < JalaliHelper.today_str():
            status = STATUS_MISSED
        else:
            status = STATUS_OPEN
        return self.db.insert_manual_attendance(
            employee_id=employee_id,
            jalali_date=date_value,
            check_in=check_in,
            check_out=check_out,
            status=status,
            delay_minutes=metrics.delay_minutes,
            early_leave_minutes=metrics.early_leave_minutes,
            overtime_minutes=metrics.overtime_minutes,
        )

    def compute_metrics(
        self,
        employee_id: int,
        check_in_time: Optional[str],
        check_out_time: Optional[str] = None,
    ) -> ShiftMetrics:
        shift = self.db.get_employee_with_shift(employee_id)
        start = shift["start_time"] if shift else None
        end = shift["end_time"] if shift else None
        tolerance = int(shift["tolerance_minutes"] or 0) if shift else 0

        overnight = self._is_overnight(employee_id)
        delay = 0
        if check_in_time and start:
            delay = max(
                align_to_shift(check_in_time, start, overnight, end) - time_to_minutes(start),
                0,
            )
        penalized = max(delay - tolerance, 0)

        early = 0
        overtime = 0
        if check_out_time and end:
            end_aligned = time_to_minutes(end)
            if overnight:
                end_aligned += 24 * 60
            delta = (
                align_to_shift(
                    check_out_time, start or end, overnight, end, is_checkout=True
                )
                - end_aligned
            )
            if delta < 0:
                early = abs(delta)
            else:
                overtime = delta
        return ShiftMetrics(
            delay_minutes=delay,
            penalized_delay_minutes=penalized,
            early_leave_minutes=early,
            overtime_minutes=overtime,
            tolerance_minutes=tolerance,
        )

    def _is_overnight(self, employee_id: int) -> bool:
        shift = self.db.get_employee_with_shift(employee_id)
        if not shift or not shift["start_time"] or not shift["end_time"]:
            return False
        return time_to_minutes(shift["end_time"]) <= time_to_minutes(shift["start_time"])

    def _open_row(self, employee_id: int, jalali_date: Optional[str] = None):
        jalali_date = jalali_date or JalaliHelper.today_str()
        row = self.db.get_open_attendance(employee_id, jalali_date)
        if row is not None:
            return row
        yesterday = JalaliHelper.shift_date(jalali_date, -1)
        previous = self.db.get_open_attendance(employee_id, yesterday)
        if previous is not None and self._is_overnight(employee_id):
            return previous
        return None

    def _latest_relevant(self, employee_id: int, jalali_date: str):
        latest = self.db.get_latest_attendance(employee_id, jalali_date)
        if latest is not None:
            return latest
        if not self._is_overnight(employee_id):
            return None
        yesterday = JalaliHelper.shift_date(jalali_date, -1)
        return self.db.get_latest_attendance(employee_id, yesterday)

    def _checkout_before_checkin(self, employee_id: int, check_in: str, check_out: str) -> bool:
        overnight = self._is_overnight(employee_id)
        if not overnight:
            return time_to_minutes(check_out) < time_to_minutes(check_in)
        shift = self.db.get_employee_with_shift(employee_id)
        start = shift["start_time"] if shift and shift["start_time"] else check_in
        end = shift["end_time"] if shift and shift["end_time"] else None
        in_m = align_to_shift(check_in, start, True, end)
        out_m = align_to_shift(check_out, start, True, end, is_checkout=True)
        return out_m < in_m

    def _require_active(self, employee_id: int, missing_message: str) -> None:
        row = self.db.get_employee_by_id(employee_id)
        if row is None:
            raise ValueError(missing_message)
        if not row["is_active"]:
            raise ValueError("این پرسنل غیرفعال است.")

    def _resolve_checkin_date(
        self,
        employee_id: int,
        jalali_date: Optional[str],
        check_in_time: str,
    ) -> str:
        if jalali_date:
            return jalali_date
        today = JalaliHelper.today_str()
        if not self._is_overnight(employee_id):
            return today
        shift = self.db.get_employee_with_shift(employee_id)
        if not shift or not shift["start_time"]:
            return today
        clock_minutes = time_to_minutes(check_in_time)
        start_minutes = time_to_minutes(shift["start_time"])
        end_minutes = time_to_minutes(shift["end_time"]) if shift["end_time"] else 0
        # Morning leftover of last night's shift (e.g. 01:00). Early evening
        # arrival (e.g. 21:50 for 22:00 start) stays on today.
        if clock_minutes < start_minutes and clock_minutes <= end_minutes:
            return JalaliHelper.shift_date(today, -1)
        return today
