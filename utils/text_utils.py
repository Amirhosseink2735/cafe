"""Persian digit and name helpers used by forms and services."""

from __future__ import annotations

import re

_DIGIT_TABLE = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def to_english_digits(value: str) -> str:
    return value.translate(_DIGIT_TABLE).strip()


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def join_full_name(first_name: str, last_name: str) -> str:
    return " ".join(part.strip() for part in (first_name, last_name) if part.strip())


def parse_hourly_rate(value: str) -> float:
    normalized = to_english_digits(value).replace(",", "")
    if not normalized:
        raise ValueError("دستمزد ساعتی را وارد کنید.")
    return float(normalized)


def parse_int(value: str, field_name: str) -> int:
    normalized = to_english_digits(value)
    if not normalized:
        raise ValueError(f"{field_name} را وارد کنید.")
    return int(normalized)


def normalize_time(value: str) -> str:
    normalized = to_english_digits(value)
    if len(normalized) == 4 and ":" not in normalized:
        normalized = f"{normalized[:2]}:{normalized[2:]}"
    if not _TIME_PATTERN.match(normalized):
        raise ValueError("ساعت باید به صورت HH:MM باشد؛ مثلاً 08:00.")
    return normalized
