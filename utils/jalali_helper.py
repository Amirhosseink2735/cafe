"""Jalali (Persian) calendar helpers based on jdatetime."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import jdatetime

DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"
MONTH_NAMES = (
    "",
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)


class JalaliHelper:
    """Convert and format Jalali dates used across the cafe app."""

    @staticmethod
    def now() -> jdatetime.datetime:
        return jdatetime.datetime.now()

    @staticmethod
    def today() -> jdatetime.date:
        return jdatetime.date.today()

    @classmethod
    def today_str(cls) -> str:
        """Return today's Jalali date as YYYY/MM/DD."""
        return cls.today().strftime(DATE_FORMAT)

    @classmethod
    def shift_date(cls, jalali_date: str, days: int) -> str:
        return (cls.parse_date(jalali_date) + timedelta(days=days)).strftime(DATE_FORMAT)

    @classmethod
    def now_time_str(cls) -> str:
        """Return current local time as HH:MM:SS."""
        return cls.now().strftime(TIME_FORMAT)

    @classmethod
    def now_datetime_str(cls) -> str:
        """Return current Jalali datetime as YYYY/MM/DD HH:MM:SS."""
        return cls.now().strftime(DATETIME_FORMAT)

    @staticmethod
    def from_gregorian(value: date | datetime) -> jdatetime.datetime:
        if isinstance(value, datetime):
            return jdatetime.datetime.fromgregorian(datetime=value)
        return jdatetime.datetime.fromgregorian(date=value)

    @staticmethod
    def to_gregorian(value: jdatetime.date | jdatetime.datetime) -> datetime:
        gregorian = value.togregorian()
        if isinstance(gregorian, datetime):
            return gregorian
        return datetime(gregorian.year, gregorian.month, gregorian.day)

    @staticmethod
    def parse_date(jalali_date: str) -> jdatetime.date:
        year, month, day = (int(part) for part in jalali_date.split("/"))
        return jdatetime.date(year, month, day)

    @classmethod
    def format_date(
        cls,
        value: Optional[jdatetime.date | jdatetime.datetime | date | datetime] = None,
    ) -> str:
        if value is None:
            return cls.today_str()
        if isinstance(value, (date, datetime)) and not isinstance(
            value, jdatetime.date
        ):
            value = cls.from_gregorian(value)
        if isinstance(value, jdatetime.datetime):
            return value.strftime(DATE_FORMAT)
        return value.strftime(DATE_FORMAT)

    @classmethod
    def month_bounds(
        cls, year: Optional[int] = None, month: Optional[int] = None
    ) -> tuple[str, str]:
        today = cls.today()
        year = year or today.year
        month = month or today.month
        start = jdatetime.date(year, month, 1)
        if month == 12:
            next_month = jdatetime.date(year + 1, 1, 1)
        else:
            next_month = jdatetime.date(year, month + 1, 1)
        end = next_month - timedelta(days=1)
        return start.strftime(DATE_FORMAT), end.strftime(DATE_FORMAT)

    @classmethod
    def month_label(cls, year: Optional[int] = None, month: Optional[int] = None) -> str:
        today = cls.today()
        year = year or today.year
        month = month or today.month
        return f"{MONTH_NAMES[month]} {year}"

    @classmethod
    def iter_dates(cls, start: str, end: str):
        current = cls.parse_date(start)
        last = cls.parse_date(end)
        while current <= last:
            yield current.strftime(DATE_FORMAT)
            current = current + timedelta(days=1)
