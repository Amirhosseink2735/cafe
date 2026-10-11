"""Staff leave-request submission and admin review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database.db_manager import DatabaseManager
from utils.jalali_helper import JalaliHelper
from utils.text_utils import normalize_jalali_date, normalize_time, time_to_minutes

LEAVE_DAILY = "daily"
LEAVE_HOURLY = "hourly"
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

STATUS_LABELS = {
    STATUS_PENDING: "در انتظار بررسی",
    STATUS_APPROVED: "تایید شده",
    STATUS_REJECTED: "رد شده",
}
TYPE_LABELS = {
    LEAVE_DAILY: "روزانه",
    LEAVE_HOURLY: "ساعتی",
}
FILTER_ALL = "همه"
FILTER_MAP = {
    FILTER_ALL: None,
    STATUS_LABELS[STATUS_PENDING]: STATUS_PENDING,
    STATUS_LABELS[STATUS_APPROVED]: STATUS_APPROVED,
    STATUS_LABELS[STATUS_REJECTED]: STATUS_REJECTED,
}


@dataclass
class LeaveRequestRecord:
    id: int
    employee_id: int
    employee_name: str
    personnel_code: str
    leave_type: str
    start_date: str
    end_date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    reason: str
    status: str
    created_at: Optional[str]
    admin_comment: Optional[str]
    reviewed_at: Optional[str]

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def type_label(self) -> str:
        return TYPE_LABELS.get(self.leave_type, self.leave_type)

    @property
    def period_label(self) -> str:
        if self.leave_type == LEAVE_HOURLY:
            return f"{self.start_date}  |  {self.start_time or '—'} تا {self.end_time or '—'}"
        end = self.end_date or self.start_date
        if end == self.start_date:
            return self.start_date
        return f"{self.start_date} تا {end}"


class LeaveService:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def submit_request(
        self,
        employee_id: int,
        leave_type: str,
        reason: str,
        start_date: str,
        end_date: str = "",
        start_time: str = "",
        end_time: str = "",
    ) -> int:
        employee = self.db.get_employee_by_id(employee_id)
        if employee is None:
            raise ValueError("ابتدا پرسنل را انتخاب کنید.")
        if not employee["is_active"]:
            raise ValueError("این پرسنل غیرفعال است.")

        leave_type = leave_type.strip()
        if leave_type not in {LEAVE_DAILY, LEAVE_HOURLY}:
            raise ValueError("نوع مرخصی نامعتبر است.")

        reason = reason.strip()
        if not reason:
            raise ValueError("دلیل مرخصی را وارد کنید.")

        start = normalize_jalali_date(start_date)
        stored_end = None
        stored_start_time = None
        stored_end_time = None

        if leave_type == LEAVE_DAILY:
            stored_end = normalize_jalali_date(end_date or start_date)
            if JalaliHelper.parse_date(stored_end) < JalaliHelper.parse_date(start):
                raise ValueError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.")
        else:
            stored_start_time = normalize_time(start_time)
            stored_end_time = normalize_time(end_time)
            if stored_end_time <= stored_start_time:
                raise ValueError("ساعت پایان مرخصی باید بعد از ساعت شروع باشد.")
            stored_end = start

        self._assert_no_overlap(
            employee_id, leave_type, start, stored_end, stored_start_time, stored_end_time
        )

        return self.db.insert_leave_request(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start,
            end_date=stored_end,
            start_time=stored_start_time,
            end_time=stored_end_time,
            reason=reason,
            status=STATUS_PENDING,
        )

    def list_requests(self, status: Optional[str] = None) -> list[LeaveRequestRecord]:
        return [self._to_record(row) for row in self.db.list_leave_requests(status)]

    def pending_count(self) -> int:
        return self.db.count_leave_requests(STATUS_PENDING)

    def approve(self, request_id: int, admin_comment: str) -> None:
        self._decide(request_id, STATUS_APPROVED, admin_comment)

    def reject(self, request_id: int, admin_comment: str) -> None:
        self._decide(request_id, STATUS_REJECTED, admin_comment)

    def _decide(self, request_id: int, status: str, admin_comment: str) -> None:
        comment = admin_comment.strip()
        if not comment:
            raise ValueError("توضیحات مدیر را وارد کنید.")
        row = self.db.get_leave_request(request_id)
        if row is None:
            raise ValueError("درخواست مرخصی پیدا نشد.")
        if row["status"] != STATUS_PENDING:
            raise ValueError("این درخواست قبلاً بررسی شده است.")
        if status == STATUS_APPROVED:
            self._assert_no_overlap(
                row["employee_id"],
                row["leave_type"],
                row["start_date"],
                row["end_date"] or row["start_date"],
                row["start_time"],
                row["end_time"],
                ignore_id=request_id,
            )
        self.db.update_leave_status(
            request_id=request_id,
            status=status,
            admin_comment=comment,
            reviewed_at=JalaliHelper.now_datetime_str(),
        )

    def _assert_no_overlap(
        self,
        employee_id: int,
        leave_type: str,
        start: str,
        end: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str],
        ignore_id: Optional[int] = None,
    ) -> None:
        end = end or start
        for row in self.db.list_leave_requests():
            if row["employee_id"] != employee_id:
                continue
            if ignore_id is not None and row["id"] == ignore_id:
                continue
            if row["status"] not in {STATUS_PENDING, STATUS_APPROVED}:
                continue
            if leave_type == LEAVE_DAILY and row["leave_type"] == LEAVE_DAILY:
                other_end = row["end_date"] or row["start_date"]
                if start <= other_end and end >= row["start_date"]:
                    raise ValueError("برای این بازه قبلاً مرخصی روزانه ثبت شده است.")
            if leave_type == LEAVE_HOURLY and row["leave_type"] == LEAVE_HOURLY:
                if row["start_date"] != start or not start_time or not end_time:
                    continue
                if not row["start_time"] or not row["end_time"]:
                    continue
                a1, a2 = time_to_minutes(start_time), time_to_minutes(end_time)
                b1, b2 = time_to_minutes(row["start_time"]), time_to_minutes(row["end_time"])
                if a1 < b2 and b1 < a2:
                    raise ValueError("این ساعت با مرخصی ساعتی دیگری تداخل دارد.")

    def _to_record(self, row) -> LeaveRequestRecord:
        return LeaveRequestRecord(
            id=row["id"],
            employee_id=row["employee_id"],
            employee_name=row["full_name"],
            personnel_code=row["personnel_code"],
            leave_type=row["leave_type"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            reason=row["reason"] or "",
            status=row["status"],
            created_at=row["created_at"],
            admin_comment=row["admin_comment"] if "admin_comment" in row.keys() else None,
            reviewed_at=row["reviewed_at"] if "reviewed_at" in row.keys() else None,
        )
