"""Jalali (Persian) calendar helpers based on jdatetime."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import jdatetime

DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"


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
