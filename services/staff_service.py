"""Employee and daily-shift management for the admin panel."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database.db_manager import DatabaseManager
from utils.text_utils import (
    join_full_name,
    normalize_time,
    parse_hourly_rate,
    parse_int,
    split_full_name,
    to_english_digits,
)


@dataclass
class EmployeeRecord:
    id: int
    first_name: str
    last_name: str
    full_name: str
    personnel_code: str
    phone: str
    hourly_rate: Optional[float]
    is_active: bool
    created_at: str
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    tolerance_minutes: Optional[int] = None

    @property
    def shift_label(self) -> str:
        if not self.shift_start or not self.shift_end:
            return "تعریف نشده"
        tolerance = self.tolerance_minutes if self.tolerance_minutes is not None else 5
        return f"{self.shift_start} تا {self.shift_end} (فرجه {tolerance} دقیقه)"


class StaffService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_employees(self, include_inactive: bool = True) -> list[EmployeeRecord]:
        rows = self.db.list_employees_with_shifts(include_inactive=include_inactive)
        return [self._to_record(row) for row in rows]

    def get_employee(self, employee_id: int) -> Optional[EmployeeRecord]:
        row = self.db.get_employee_with_shift(employee_id)
        return self._to_record(row) if row else None

    def save_employee(
        self,
        first_name: str,
        last_name: str,
        personnel_code: str,
        phone: str,
        hourly_rate: str,
        employee_id: Optional[int] = None,
    ) -> int:
        first_name = first_name.strip()
        last_name = last_name.strip()
        personnel_code = to_english_digits(personnel_code)
        phone = phone.strip()
        if not first_name:
            raise ValueError("نام را وارد کنید.")
        if not last_name:
            raise ValueError("نام خانوادگی را وارد کنید.")
        if not personnel_code:
            raise ValueError("کد پرسنلی را وارد کنید.")

        full_name = join_full_name(first_name, last_name)
        rate = parse_hourly_rate(hourly_rate)
        if rate < 0:
            raise ValueError("دستمزد ساعتی نمی‌تواند منفی باشد.")

        existing = self.db.get_employee_by_code(personnel_code)
        if existing and existing["id"] != employee_id:
            raise ValueError("این کد پرسنلی قبلاً ثبت شده است.")

        if employee_id is None:
            return self.db.insert_employee(
                full_name=full_name,
                personnel_code=personnel_code,
                phone=phone or None,
                hourly_rate=rate,
            )

        self.db.update_employee(
            employee_id=employee_id,
            full_name=full_name,
            personnel_code=personnel_code,
            phone=phone or None,
            hourly_rate=rate,
        )
        return employee_id

    def deactivate_employee(self, employee_id: int, jalali_date: str | None = None) -> None:
        self.db.set_employee_active(employee_id, False, jalali_date=jalali_date)

    def activate_employee(self, employee_id: int, jalali_date: str | None = None) -> None:
        self.db.set_employee_active(employee_id, True, jalali_date=jalali_date)

    def save_shift(
        self,
        employee_id: int,
        start_time: str,
        end_time: str,
        tolerance_minutes: str,
    ) -> None:
        if self.db.get_employee_by_id(employee_id) is None:
            raise ValueError("ابتدا کارمند را انتخاب یا ذخیره کنید.")
        start = normalize_time(start_time)
        end = normalize_time(end_time)
        if start == end:
            raise ValueError("ساعت شروع و پایان نمی‌تواند یکسان باشد.")
        tolerance = parse_int(tolerance_minutes, "زمان فرجه")
        if tolerance < 0:
            raise ValueError("فرجه تأخیر نمی‌تواند منفی باشد.")
        self.db.upsert_shift(employee_id, start, end, tolerance)

    def _to_record(self, row) -> EmployeeRecord:
        first_name, last_name = split_full_name(row["full_name"])
        return EmployeeRecord(
            id=row["id"],
            first_name=first_name,
            last_name=last_name,
            full_name=row["full_name"],
            personnel_code=row["personnel_code"],
            phone=row["phone"] or "",
            hourly_rate=row["hourly_rate"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            shift_start=row["start_time"] if "start_time" in row.keys() else None,
            shift_end=row["end_time"] if "end_time" in row.keys() else None,
            tolerance_minutes=row["tolerance_minutes"] if "tolerance_minutes" in row.keys() else None,
        )
