"""SQLite connection, schema, and basic helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from utils.jalali_helper import JalaliHelper

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "cafe.db"

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        personnel_code TEXT NOT NULL UNIQUE,
        phone TEXT,
        hourly_rate REAL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        tolerance_minutes INTEGER NOT NULL DEFAULT 5,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        jalali_date TEXT NOT NULL,
        check_in TEXT,
        check_out TEXT,
        is_manual_entry INTEGER NOT NULL DEFAULT 0,
        status TEXT,
        delay_minutes INTEGER NOT NULL DEFAULT 0,
        early_leave_minutes INTEGER NOT NULL DEFAULT 0,
        overtime_minutes INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT,
        start_time TEXT,
        end_time TEXT,
        reason TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        jalali_date TEXT NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        reason TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """,
)

REQUIRED_TABLES = (
    "employees",
    "shifts",
    "attendances",
    "leave_requests",
    "adjustments",
    "settings",
)


def get_default_db_path() -> Path:
    return DEFAULT_DB_PATH


class DatabaseManager:
    """Manage the local SQLite database used by the cafe app."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA encoding = 'UTF-8'")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            for statement in SCHEMA_STATEMENTS:
                connection.execute(statement)
            self._seed_default_settings(connection)
            connection.commit()

    def table_names(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        return sorted(row["name"] for row in rows)

    def insert_employee(
        self,
        full_name: str,
        personnel_code: str,
        phone: Optional[str] = None,
        hourly_rate: Optional[float] = None,
        is_active: bool = True,
        created_at: Optional[str] = None,
    ) -> int:
        created_at = created_at or JalaliHelper.now_datetime_str()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO employees (
                    full_name, personnel_code, phone, hourly_rate, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    personnel_code,
                    phone,
                    hourly_rate,
                    1 if is_active else 0,
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_employee_by_code(self, personnel_code: str) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM employees WHERE personnel_code = ?",
                (personnel_code,),
            ).fetchone()

    def _seed_default_settings(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('admin_password', 'admin')
            """
        )
