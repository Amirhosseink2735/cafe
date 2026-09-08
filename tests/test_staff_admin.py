"""Phase 2 admin staff, shift, and password tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from services.auth_service import AuthService, hash_password
from services.staff_service import StaffService


@pytest.fixture
def staff_service(tmp_path: Path) -> StaffService:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    return StaffService(db)


@pytest.fixture
def auth_service(tmp_path: Path) -> AuthService:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    return AuthService(db)


def test_default_admin_password(auth_service: AuthService) -> None:
    assert auth_service.verify_password("admin")
    assert not auth_service.verify_password("wrong")


def test_change_admin_password(auth_service: AuthService) -> None:
    auth_service.change_password("admin", "cafe1234")
    assert auth_service.verify_password("cafe1234")
    assert not auth_service.verify_password("admin")
    stored = auth_service.db.get_setting("admin_password")
    assert stored == hash_password("cafe1234")


def test_create_employee_and_shift(staff_service: StaffService) -> None:
    employee_id = staff_service.save_employee(
        first_name="علی",
        last_name="محمدی",
        personnel_code="1001",
        phone="09120000000",
        hourly_rate="۱۵۰۰۰۰",
    )
    staff_service.save_shift(employee_id, "08:00", "16:00", "10")

    employee = staff_service.get_employee(employee_id)
    assert employee is not None
    assert employee.full_name == "علی محمدی"
    assert employee.first_name == "علی"
    assert employee.last_name == "محمدی"
    assert employee.hourly_rate == 150000
    assert employee.shift_start == "08:00"
    assert employee.shift_end == "16:00"
    assert employee.tolerance_minutes == 10


def test_edit_employee_and_soft_delete(staff_service: StaffService) -> None:
    employee_id = staff_service.save_employee(
        first_name="سارا",
        last_name="احمدی",
        personnel_code="2002",
        phone="09121111111",
        hourly_rate="120000",
    )
    staff_service.save_employee(
        first_name="سارا",
        last_name="کاظمی",
        personnel_code="2002",
        phone="09122222222",
        hourly_rate="130000",
        employee_id=employee_id,
    )
    staff_service.deactivate_employee(employee_id)

    employee = staff_service.get_employee(employee_id)
    assert employee is not None
    assert employee.full_name == "سارا کاظمی"
    assert employee.is_active is False


def test_duplicate_personnel_code_rejected(staff_service: StaffService) -> None:
    staff_service.save_employee("نیما", "رضایی", "3003", "", "90000")
    with pytest.raises(ValueError, match="کد پرسنلی"):
        staff_service.save_employee("آرش", "کریمی", "3003", "", "80000")
