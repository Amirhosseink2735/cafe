"""Staff check-in / check-out for the kiosk."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database.db_manager import DatabaseManager
from utils.jalali_helper import JalaliHelper
from utils.text_utils import time_to_minutes


@dataclass
class AttendanceStatus:
    is_inside: bool
    label: str
    detail: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: Optional[str] = None


class AttendanceService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def current_status(self, employee_id: int, jalali_date: Optional[str] = None) -> AttendanceStatus:
        jalali_date = jalali_date or JalaliHelper.today_str()
        open_row = self.db.get_open_attendance(employee_id, jalali_date)
        if open_row is not None:
            return AttendanceStatus(
                is_inside=True,
                label="داخل کافه",
                detail=f"ورود امروز ساعت {open_row['check_in']}",
                check_in=open_row["check_in"],
                status=open_row["status"],
            )

        latest = self.db.get_latest_attendance(employee_id, jalali_date)
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
                detail=f"آخرین خروج امروز ساعت {latest['check_out']}",
                check_in=latest["check_in"],
                check_out=latest["check_out"],
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
        if self.db.get_employee_by_id(employee_id) is None:
            raise ValueError("پرسنل انتخاب‌شده معتبر نیست.")
        jalali_date = jalali_date or JalaliHelper.today_str()
        check_in_time = check_in_time or JalaliHelper.now_time_str()
        if self.db.get_open_attendance(employee_id, jalali_date) is not None:
            raise ValueError("ورود این پرسنل قبلاً ثبت شده و هنوز خروج نخورده است.")

        delay_minutes = self._delay_minutes(employee_id, check_in_time)
        self.db.insert_attendance(
            employee_id=employee_id,
            jalali_date=jalali_date,
            check_in=check_in_time,
            delay_minutes=delay_minutes,
        )
        return self.current_status(employee_id, jalali_date)

    def check_out(
        self,
        employee_id: int,
        jalali_date: Optional[str] = None,
        check_out_time: Optional[str] = None,
    ) -> AttendanceStatus:
        jalali_date = jalali_date or JalaliHelper.today_str()
        check_out_time = check_out_time or JalaliHelper.now_time_str()
        open_row = self.db.get_open_attendance(employee_id, jalali_date)
        if open_row is None:
            raise ValueError("برای این پرسنل ورود بازی وجود ندارد.")

        early, overtime = self._leave_metrics(employee_id, check_out_time)
        self.db.complete_attendance(
            attendance_id=open_row["id"],
            check_out=check_out_time,
            early_leave_minutes=early,
            overtime_minutes=overtime,
        )
        return self.current_status(employee_id, jalali_date)

    def _delay_minutes(self, employee_id: int, check_in_time: str) -> int:
        shift = self.db.get_employee_with_shift(employee_id)
        if shift is None or not shift["start_time"]:
            return 0
        delay = time_to_minutes(check_in_time) - time_to_minutes(shift["start_time"])
        return max(delay, 0)

    def _leave_metrics(self, employee_id: int, check_out_time: str) -> tuple[int, int]:
        shift = self.db.get_employee_with_shift(employee_id)
        if shift is None or not shift["end_time"]:
            return 0, 0
        delta = time_to_minutes(check_out_time) - time_to_minutes(shift["end_time"])
        if delta < 0:
            return abs(delta), 0
        return 0, delta
