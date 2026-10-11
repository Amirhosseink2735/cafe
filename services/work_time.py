"""Shared monthly work-time math used by payroll and attendance reports."""

from __future__ import annotations

from typing import Optional

from utils.text_utils import shift_length_minutes, time_to_minutes

STATUS_COMPLETED = "completed"
STATUS_OPEN = "open"
STATUS_MISSED = "missed_checkout"


def unique_latest_rows(rows) -> list:
    """Keep one attendance row per Jalali date (highest id wins)."""
    by_date: dict[str, object] = {}
    for row in rows:
        by_date[row["jalali_date"]] = row
    return list(by_date.values())


def completed_day_minutes(
    row,
    shift_start: Optional[str],
    shift_end: Optional[str],
    tolerance: int,
) -> Optional[int]:
    """Return payable minutes for a completed day, or None if incomplete."""
    if row["status"] != STATUS_COMPLETED or not row["check_in"] or not row["check_out"]:
        return None
    delay_value = int(row["delay_minutes"] or 0)
    early_value = int(row["early_leave_minutes"] or 0)
    ot_value = int(row["overtime_minutes"] or 0)
    if shift_start and shift_end:
        shift_len = shift_length_minutes(shift_start, shift_end)
        day_minutes = shift_len - max(delay_value - tolerance, 0) - early_value + ot_value
        return max(day_minutes, 0)
    in_m = time_to_minutes(row["check_in"])
    out_m = time_to_minutes(row["check_out"])
    if out_m < in_m:
        out_m += 24 * 60
    return max(out_m - in_m, 0)


def minutes_label(total: Optional[int]) -> str:
    if total is None:
        return "—"
    hours, minutes = divmod(int(total), 60)
    return f"{hours}:{minutes:02d}"


def record_status_label(row) -> str:
    has_in = bool(row["check_in"])
    has_out = bool(row["check_out"])
    if has_in and has_out and row["status"] == STATUS_COMPLETED:
        return "کامل"
    if has_in and not has_out:
        return "ناقص — ورود بدون خروج"
    if has_out and not has_in:
        return "ناقص — خروج بدون ورود"
    return "ناقص"


def day_presence_label(row) -> str:
    if row is None:
        return "عدم ثبت تردد"
    if record_status_label(row).startswith("ناقص"):
        return "تردد ناقص"
    return "حضور"
