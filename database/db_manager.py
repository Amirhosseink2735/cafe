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
        admin_comment TEXT,
        reviewed_at TEXT,
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
            self._migrate_schema(connection)
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
            return int(cursor.lastrowid or 0)

    def update_employee(
        self,
        employee_id: int,
        full_name: str,
        personnel_code: str,
        phone: Optional[str],
        hourly_rate: Optional[float],
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE employees
                SET full_name = ?, personnel_code = ?, phone = ?, hourly_rate = ?
                WHERE id = ?
                """,
                (full_name, personnel_code, phone, hourly_rate, employee_id),
            )
            connection.commit()

    def set_employee_active(self, employee_id: int, is_active: bool) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE employees SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, employee_id),
            )
            connection.commit()

    def get_employee_by_id(self, employee_id: int) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM employees WHERE id = ?",
                (employee_id,),
            ).fetchone()

    def get_employee_by_code(self, personnel_code: str) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM employees WHERE personnel_code = ?",
                (personnel_code,),
            ).fetchone()

    def list_employees_with_shifts(self, include_inactive: bool = True) -> list[sqlite3.Row]:
        query = """
            SELECT
                e.*,
                s.start_time,
                s.end_time,
                s.tolerance_minutes
            FROM employees e
            LEFT JOIN (
                SELECT employee_id, start_time, end_time, tolerance_minutes
                FROM shifts
                WHERE id IN (SELECT MAX(id) FROM shifts GROUP BY employee_id)
            ) s ON s.employee_id = e.id
            {where_clause}
            ORDER BY e.is_active DESC, e.id DESC
        """
        where_clause = "" if include_inactive else "WHERE e.is_active = 1"
        with self.connect() as connection:
            return connection.execute(query.format(where_clause=where_clause)).fetchall()

    def get_employee_with_shift(self, employee_id: int) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT
                    e.*,
                    s.start_time,
                    s.end_time,
                    s.tolerance_minutes
                FROM employees e
                LEFT JOIN (
                    SELECT employee_id, start_time, end_time, tolerance_minutes
                    FROM shifts
                    WHERE id IN (SELECT MAX(id) FROM shifts GROUP BY employee_id)
                ) s ON s.employee_id = e.id
                WHERE e.id = ?
                """,
                (employee_id,),
            ).fetchone()

    def upsert_shift(
        self,
        employee_id: int,
        start_time: str,
        end_time: str,
        tolerance_minutes: int,
    ) -> None:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM shifts WHERE employee_id = ? ORDER BY id DESC LIMIT 1",
                (employee_id,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE shifts
                    SET start_time = ?, end_time = ?, tolerance_minutes = ?
                    WHERE id = ?
                    """,
                    (start_time, end_time, tolerance_minutes, existing["id"]),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO shifts (employee_id, start_time, end_time, tolerance_minutes)
                    VALUES (?, ?, ?, ?)
                    """,
                    (employee_id, start_time, end_time, tolerance_minutes),
                )
            connection.commit()

    def get_setting(self, key: str) -> Optional[str]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        return None if row is None else row["value"]

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            connection.commit()

    def get_open_attendance(self, employee_id: int, jalali_date: str) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM attendances
                WHERE employee_id = ? AND jalali_date = ? AND status = 'open'
                ORDER BY id DESC
                LIMIT 1
                """,
                (employee_id, jalali_date),
            ).fetchone()

    def get_latest_attendance(self, employee_id: int, jalali_date: str) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM attendances
                WHERE employee_id = ? AND jalali_date = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (employee_id, jalali_date),
            ).fetchone()

    def insert_attendance(
        self,
        employee_id: int,
        jalali_date: str,
        check_in: str,
        status: str = "open",
        delay_minutes: int = 0,
        is_manual_entry: bool = False,
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO attendances (
                    employee_id, jalali_date, check_in, check_out,
                    is_manual_entry, status, delay_minutes,
                    early_leave_minutes, overtime_minutes
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, 0, 0)
                """,
                (
                    employee_id,
                    jalali_date,
                    check_in,
                    1 if is_manual_entry else 0,
                    status,
                    delay_minutes,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid or 0)

    def complete_attendance(
        self,
        attendance_id: int,
        check_out: str,
        early_leave_minutes: int = 0,
        overtime_minutes: int = 0,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE attendances
                SET check_out = ?, status = 'completed',
                    early_leave_minutes = ?, overtime_minutes = ?
                WHERE id = ?
                """,
                (check_out, early_leave_minutes, overtime_minutes, attendance_id),
            )
            connection.commit()

    def insert_leave_request(
        self,
        employee_id: int,
        leave_type: str,
        start_date: str,
        end_date: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str],
        reason: str,
        status: str = "pending",
        created_at: Optional[str] = None,
    ) -> int:
        created_at = created_at or JalaliHelper.now_datetime_str()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO leave_requests (
                    employee_id, leave_type, start_date, end_date,
                    start_time, end_time, reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    employee_id,
                    leave_type,
                    start_date,
                    end_date,
                    start_time,
                    end_time,
                    reason,
                    status,
                    created_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid or 0)

    def list_leave_requests(self, status: Optional[str] = None) -> list[sqlite3.Row]:
        query = """
            SELECT
                lr.*,
                e.full_name,
                e.personnel_code
            FROM leave_requests lr
            JOIN employees e ON e.id = lr.employee_id
        """
        params: list[str] = []
        if status:
            query += " WHERE lr.status = ?"
            params.append(status)
        query += """
            ORDER BY CASE lr.status WHEN 'pending' THEN 0 ELSE 1 END, lr.id DESC
        """
        with self.connect() as connection:
            return connection.execute(query, params).fetchall()

    def get_leave_request(self, request_id: int) -> Optional[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT lr.*, e.full_name, e.personnel_code
                FROM leave_requests lr
                JOIN employees e ON e.id = lr.employee_id
                WHERE lr.id = ?
                """,
                (request_id,),
            ).fetchone()

    def count_leave_requests(self, status: str) -> int:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM leave_requests WHERE status = ?",
                (status,),
            ).fetchone()
        return int(row["total"] if row else 0)

    def update_leave_status(
        self,
        request_id: int,
        status: str,
        admin_comment: str,
        reviewed_at: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE leave_requests
                SET status = ?, admin_comment = ?, reviewed_at = ?
                WHERE id = ?
                """,
                (status, admin_comment, reviewed_at, request_id),
            )
            connection.commit()

    def _column_names(self, connection: sqlite3.Connection, table: str) -> set[str]:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        return {row[1] for row in rows}

    def _migrate_schema(self, connection: sqlite3.Connection) -> None:
        columns = self._column_names(connection, "leave_requests")
        if "admin_comment" not in columns:
            connection.execute("ALTER TABLE leave_requests ADD COLUMN admin_comment TEXT")
        if "reviewed_at" not in columns:
            connection.execute("ALTER TABLE leave_requests ADD COLUMN reviewed_at TEXT")

    def _seed_default_settings(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('admin_password', 'admin')
            """
        )
