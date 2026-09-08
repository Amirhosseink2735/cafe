"""Phase 4 admin leave inbox tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.db_manager import DatabaseManager
from services.leave_service import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    LEAVE_DAILY,
    LeaveService,
)
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


@pytest.fixture
def leave_setup(tmp_path: Path) -> tuple[LeaveService, int]:
    db = DatabaseManager(tmp_path / "cafe.db")
    db.initialize()
    staff = StaffService(db)
    employee_id = staff.save_employee("سارا", "احمدی", "2002", "", "120000")
    return LeaveService(db), employee_id


def _submit(leave: LeaveService, employee_id: int, reason: str = "کار شخصی") -> int:
    return leave.submit_request(
        employee_id=employee_id,
        leave_type=LEAVE_DAILY,
        reason=reason,
        start_date=JalaliHelper.today_str(),
        end_date=JalaliHelper.today_str(),
    )


def test_new_request_is_pending(leave_setup) -> None:
    leave, employee_id = leave_setup
    request_id = _submit(leave, employee_id)
    pending = leave.list_requests(STATUS_PENDING)
    assert request_id > 0
    assert leave.pending_count() == 1
    assert pending[0].status == STATUS_PENDING
    assert pending[0].employee_name == "سارا احمدی"


def test_approve_with_admin_comment(leave_setup) -> None:
    leave, employee_id = leave_setup
    request_id = _submit(leave, employee_id)
    leave.approve(request_id, "با مرخصی موافقم")
    approved = leave.list_requests(STATUS_APPROVED)
    assert leave.pending_count() == 0
    assert len(approved) == 1
    assert approved[0].admin_comment == "با مرخصی موافقم"
    assert approved[0].reviewed_at


def test_reject_with_admin_comment(leave_setup) -> None:
    leave, employee_id = leave_setup
    request_id = _submit(leave, employee_id, "سفر")
    leave.reject(request_id, "در این تاریخ نیرو کم است")
    rejected = leave.list_requests(STATUS_REJECTED)
    assert rejected[0].status == STATUS_REJECTED
    assert "نیرو کم" in (rejected[0].admin_comment or "")


def test_comment_is_required(leave_setup) -> None:
    leave, employee_id = leave_setup
    request_id = _submit(leave, employee_id)
    with pytest.raises(ValueError, match="توضیحات"):
        leave.approve(request_id, "   ")


def test_cannot_review_twice(leave_setup) -> None:
    leave, employee_id = leave_setup
    request_id = _submit(leave, employee_id)
    leave.approve(request_id, "تایید شد")
    with pytest.raises(ValueError, match="بررسی"):
        leave.reject(request_id, "تغییر نظر")


def test_filter_splits_statuses(leave_setup) -> None:
    leave, employee_id = leave_setup
    first = _submit(leave, employee_id, "اول")
    second = _submit(leave, employee_id, "دوم")
    leave.approve(first, "تایید اول")
    assert len(leave.list_requests(STATUS_PENDING)) == 1
    assert leave.list_requests(STATUS_PENDING)[0].id == second
    assert len(leave.list_requests(STATUS_APPROVED)) == 1
    assert len(leave.list_requests()) == 2
