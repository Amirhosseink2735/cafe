"""Touch-friendly staff kiosk for check-in, check-out, and leave requests."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from database.db_manager import DatabaseManager
from gui.leave_dialog import LeaveRequestDialog
from gui.style import COLORS, app_font, apply_window_icon, center_window, close_window, initials_of
from services.attendance_service import AttendanceService
from services.leave_service import LeaveService
from services.staff_service import EmployeeRecord, StaffService
from utils.jalali_helper import JalaliHelper


class KioskWindow(ctk.CTk):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        apply_window_icon(self)
        self.db = db
        self.staff = StaffService(db)
        self.attendance = AttendanceService(db)
        self.leave_service = LeaveService(db)
        self.selected_employee_id: Optional[int] = None
        self._employees: dict[int, EmployeeRecord] = {}
        self._clock_job: Optional[str] = None

        self.title("کیوسک پرسنل کافه")
        self.configure(fg_color=COLORS["cream"])
        center_window(self, 1280, 860)
        self.minsize(1100, 760)

        self._build_header()
        self._build_body()
        self._tick_clock()
        self.refresh_staff()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, height=110, corner_radius=0, fg_color=COLORS["header"])
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkButton(
            header,
            text="بازگشت",
            width=110,
            height=44,
            fg_color=COLORS["espresso_dark"],
            hover_color=COLORS["espresso_dark"],
            command=self._on_close,
        ).pack(side="left", padx=20, pady=32)

        clock_box = ctk.CTkFrame(header, fg_color="transparent")
        clock_box.pack(side="right", padx=28)
        self.time_label = ctk.CTkLabel(
            clock_box,
            text="",
            font=app_font(36, "bold"),
            text_color=COLORS["on_espresso"],
        )
        self.time_label.pack(anchor="e")
        self.date_label = ctk.CTkLabel(
            clock_box,
            text="",
            font=app_font(16),
            text_color=COLORS["caramel"],
        )
        self.date_label.pack(anchor="e")

        ctk.CTkLabel(
            header,
            text="کیوسک پرسنل",
            font=app_font(22, "bold"),
            text_color=COLORS["on_espresso"],
        ).pack(side="right", padx=12)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(expand=True, fill="both", padx=20, pady=18)

        select_card = ctk.CTkFrame(body, corner_radius=22, fg_color=COLORS["card"])
        select_card.pack(fill="x", pady=(0, 14))

        top = ctk.CTkFrame(select_card, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(
            top,
            text="پرسنل خود را انتخاب کنید",
            font=app_font(20, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(side="right")

        self.staff_combo = ctk.CTkComboBox(
            top,
            width=280,
            height=40,
            font=app_font(14),
            justify="right",
            command=self._on_combo_select,
            values=["—"],
        )
        self.staff_combo.pack(side="left")
        self.staff_combo.set("انتخاب سریع از لیست")

        self.staff_cards = ctk.CTkScrollableFrame(
            select_card, height=150, fg_color="transparent"
        )
        self.staff_cards.pack(fill="x", padx=12, pady=(0, 14))

        status_card = ctk.CTkFrame(body, corner_radius=22, fg_color=COLORS["card"])
        status_card.pack(fill="x", pady=(0, 14))
        self.selected_name_label = ctk.CTkLabel(
            status_card,
            text="هنوز کسی انتخاب نشده است",
            font=app_font(22, "bold"),
            text_color=COLORS["espresso"],
        )
        self.selected_name_label.pack(pady=(18, 4))
        self.status_pill = ctk.CTkLabel(
            status_card,
            text="خارج از کافه",
            font=app_font(18, "bold"),
            text_color=COLORS["pill_off_fg"],
        )
        self.status_pill.pack()
        self.status_detail = ctk.CTkLabel(
            status_card,
            text="برای ثبت ورود یا خروج، نام خود را لمس کنید.",
            font=app_font(14),
            text_color=COLORS["muted"],
        )
        self.status_detail.pack(pady=(4, 18))
        self.feedback_label = ctk.CTkLabel(
            status_card,
            text="",
            font=app_font(14, "bold"),
            text_color=COLORS["success"],
            height=22,
        )
        self.feedback_label.pack(pady=(0, 12))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="both", expand=True)
        actions.grid_columnconfigure((0, 1), weight=1)
        actions.grid_rowconfigure(0, weight=1)

        self.check_in_button = ctk.CTkButton(
            actions,
            text="ثبت ورود",
            font=app_font(28, "bold"),
            height=140,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._check_in,
        )
        self.check_in_button.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=(0, 12))

        self.check_out_button = ctk.CTkButton(
            actions,
            text="ثبت خروج",
            font=app_font(28, "bold"),
            height=140,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            command=self._check_out,
        )
        self.check_out_button.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(0, 12))

        ctk.CTkButton(
            body,
            text="درخواست مرخصی",
            font=app_font(18, "bold"),
            height=56,
            fg_color=COLORS["ghost"],
            hover_color=COLORS["ghost_hover"],
            text_color=COLORS["espresso"],
            command=self._open_leave,
        ).pack(fill="x")

    def _tick_clock(self) -> None:
        if not self.winfo_exists():
            return
        now = JalaliHelper.now()
        self.time_label.configure(text=now.strftime("%H:%M:%S"))
        self.date_label.configure(text=now.strftime("%Y/%m/%d"))
        self._clock_job = self.after(500, self._tick_clock)

    def refresh_staff(self) -> None:
        for child in self.staff_cards.winfo_children():
            child.destroy()

        employees = self.staff.list_employees(include_inactive=False)
        self._employees = {employee.id: employee for employee in employees}
        names = [f"{emp.full_name}  |  {emp.personnel_code}" for emp in employees]
        self.staff_combo.configure(values=names or ["پرسنل فعالی نیست"])

        if not employees:
            ctk.CTkLabel(
                self.staff_cards,
                text="پرسنل فعالی ثبت نشده. از پنل مدیر کارمند اضافه کنید.",
                font=app_font(15),
                text_color=COLORS["muted"],
            ).pack(pady=24)
            return

        row = ctk.CTkFrame(self.staff_cards, fg_color="transparent")
        row.pack(fill="x")
        for index, employee in enumerate(employees):
            if index and index % 4 == 0:
                row = ctk.CTkFrame(self.staff_cards, fg_color="transparent")
                row.pack(fill="x")
            self._staff_card(row, employee)

        if self.selected_employee_id in self._employees:
            employee = self._employees[self.selected_employee_id]
            self.staff_combo.set(f"{employee.full_name}  |  {employee.personnel_code}")

    def _staff_card(self, parent: ctk.CTkFrame, employee: EmployeeRecord) -> None:
        selected = employee.id == self.selected_employee_id
        card = ctk.CTkButton(
            parent,
            text=f"{initials_of(employee.full_name)}\n{employee.full_name}\nکد {employee.personnel_code}",
            font=app_font(14, "bold"),
            width=220,
            height=110,
            fg_color=COLORS["espresso"] if selected else COLORS["cream"],
            text_color=COLORS["on_espresso"] if selected else COLORS["ink"],
            hover_color=COLORS["espresso_dark"] if selected else COLORS["ghost"],
            command=lambda emp_id=employee.id: self._select_employee(emp_id),
        )
        card.pack(side="right", padx=6, pady=6)

    def _on_combo_select(self, value: str) -> None:
        for employee in self._employees.values():
            label = f"{employee.full_name}  |  {employee.personnel_code}"
            if label == value:
                self._select_employee(employee.id)
                return

    def _select_employee(self, employee_id: int) -> None:
        self.selected_employee_id = employee_id
        self.feedback_label.configure(text="")
        self.refresh_staff()
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self.selected_employee_id is None:
            return
        employee = self._employees.get(self.selected_employee_id)
        if employee is None:
            return
        status = self.attendance.current_status(employee.id)
        self.selected_name_label.configure(text=employee.full_name)
        self.status_pill.configure(
            text=status.label,
            text_color=COLORS["pill_ok_fg"] if status.is_inside else COLORS["pill_off_fg"],
        )
        self.status_detail.configure(text=status.detail)
        self.check_in_button.configure(state="disabled" if status.is_inside else "normal")
        self.check_out_button.configure(state="normal" if status.is_inside else "disabled")

    def _require_employee(self) -> Optional[EmployeeRecord]:
        if self.selected_employee_id is None:
            self.feedback_label.configure(
                text="ابتدا نام خود را انتخاب کنید.",
                text_color=COLORS["danger"],
            )
            return None
        return self._employees.get(self.selected_employee_id)

    def _check_in(self) -> None:
        employee = self._require_employee()
        if employee is None:
            return
        try:
            status = self.attendance.check_in(employee.id)
        except ValueError as exc:
            self.feedback_label.configure(text=str(exc), text_color=COLORS["danger"])
            return
        self.feedback_label.configure(
            text=f"ورود ثبت شد — {JalaliHelper.now_time_str()}",
            text_color=COLORS["success"],
        )
        self.status_pill.configure(text=status.label, text_color=COLORS["pill_ok_fg"])
        self.status_detail.configure(text=status.detail)
        self.check_in_button.configure(state="disabled")
        self.check_out_button.configure(state="normal")

    def _check_out(self) -> None:
        employee = self._require_employee()
        if employee is None:
            return
        try:
            status = self.attendance.check_out(employee.id)
        except ValueError as exc:
            self.feedback_label.configure(text=str(exc), text_color=COLORS["danger"])
            return
        self.feedback_label.configure(
            text=f"خروج ثبت شد — {JalaliHelper.now_time_str()}",
            text_color=COLORS["espresso"],
        )
        self.status_pill.configure(text=status.label, text_color=COLORS["pill_off_fg"])
        self.status_detail.configure(text=status.detail)
        self.check_in_button.configure(state="normal")
        self.check_out_button.configure(state="disabled")

    def _open_leave(self) -> None:
        employee = self._require_employee()
        if employee is None:
            return
        dialog = LeaveRequestDialog(self, self.leave_service, employee.id, employee.full_name)
        self.wait_window(dialog)
        if getattr(dialog, "submitted", False):
            self.feedback_label.configure(
                text="درخواست مرخصی ارسال شد و در انتظار تایید مدیر است.",
                text_color=COLORS["success"],
            )

    def _on_close(self) -> None:
        close_window(self)
