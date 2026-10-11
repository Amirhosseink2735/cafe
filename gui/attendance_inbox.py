"""Admin inbox for missed punches and manual attendance corrections."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from gui.style import COLORS, app_font
from services.attendance_service import AttendanceService, IncompleteAttendance
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


class AttendanceInboxFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        attendance: AttendanceService,
        staff: StaffService,
        on_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.attendance = attendance
        self.staff = staff
        self.on_changed = on_changed
        self._employees_by_label: dict[str, int] = {}

        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            heading,
            text="اصلاح دستی ترددها",
            font=app_font(22, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(side="right")
        self.count_badge = ctk.CTkLabel(
            heading,
            text="",
            font=app_font(13, "bold"),
            text_color=COLORS["espresso"],
        )
        self.count_badge.pack(side="left")

        self._build_manual_form()

        ctk.CTkLabel(
            self,
            text="ترددهای بلاتکلیف (ورود بدون خروج)",
            font=app_font(16, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", pady=(8, 6))

        self.list_frame = ctk.CTkScrollableFrame(
            self, corner_radius=18, fg_color=COLORS["card"]
        )
        self.list_frame.pack(expand=True, fill="both")
        self.refresh()

    def _build_manual_form(self) -> None:
        form = ctk.CTkFrame(self, corner_radius=18, fg_color=COLORS["card"])
        form.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            form,
            text="ثبت ورود / خروج جامانده",
            font=app_font(16, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=16, pady=(14, 8))

        grid = ctk.CTkFrame(form, fg_color="transparent")
        grid.pack(fill="x", padx=12, pady=(0, 8))
        grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.checkout_entry = self._grid_entry(grid, "ساعت خروج (اختیاری)", 0, 0)
        self.checkin_entry = self._grid_entry(grid, "ساعت ورود", 0, 1)
        self.date_entry = self._grid_entry(grid, "تاریخ شمسی", 0, 2)
        self.date_entry.insert(0, JalaliHelper.today_str())
        self.checkin_entry.insert(0, "08:00")

        wrap = ctk.CTkFrame(grid, fg_color="transparent")
        wrap.grid(row=0, column=3, sticky="ew", padx=4)
        ctk.CTkLabel(wrap, text="پرسنل", font=app_font(13), anchor="e").pack(fill="x")
        self.employee_combo = ctk.CTkComboBox(
            wrap, font=app_font(13), justify="right", height=40, values=["—"]
        )
        self.employee_combo.pack(fill="x", pady=(4, 0))

        self.form_error = ctk.CTkLabel(
            form, text="", font=app_font(12), text_color=COLORS["danger"]
        )
        self.form_error.pack(fill="x", padx=16)
        ctk.CTkButton(
            form,
            text="ثبت دستی با پرچم اصلاح مدیر",
            height=42,
            command=self._save_manual,
        ).pack(fill="x", padx=16, pady=(4, 16))

    def _grid_entry(self, parent, label: str, row: int, column: int) -> ctk.CTkEntry:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="ew", padx=4)
        ctk.CTkLabel(wrap, text=label, font=app_font(13), anchor="e").pack(fill="x")
        entry = ctk.CTkEntry(wrap, justify="right", font=app_font(14), height=40)
        entry.pack(fill="x", pady=(4, 0))
        return entry

    def refresh(self) -> None:
        employees = self.staff.list_employees(include_inactive=False)
        self._employees_by_label = {
            f"{emp.full_name}  |  {emp.personnel_code}": emp.id for emp in employees
        }
        labels = list(self._employees_by_label.keys()) or ["پرسنل فعالی نیست"]
        current = self.employee_combo.get()
        self.employee_combo.configure(values=labels)
        if current in self._employees_by_label:
            self.employee_combo.set(current)
        else:
            self.employee_combo.set(labels[0])

        for child in self.list_frame.winfo_children():
            child.destroy()

        items = self.attendance.list_incomplete()
        self.count_badge.configure(
            text=f"{len(items)} تردد بلاتکلیف" if items else "تردد بلاتکلیفی نیست"
        )
        if not items:
            ctk.CTkLabel(
                self.list_frame,
                text="همه ورودها خروج متناظر دارند.",
                font=app_font(15),
                text_color=COLORS["muted"],
            ).pack(pady=36)
        else:
            for item in items:
                self._add_card(item)
        if self.on_changed:
            self.on_changed()

    def _add_card(self, item: IncompleteAttendance) -> None:
        card = ctk.CTkFrame(self.list_frame, corner_radius=16, fg_color=COLORS["cream"])
        card.pack(fill="x", padx=10, pady=8)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 4))
        ctk.CTkLabel(
            top,
            text=item.employee_name,
            font=app_font(16, "bold"),
            text_color=COLORS["ink"],
            anchor="e",
        ).pack(side="right")
        pill = ctk.CTkFrame(
            top, fg_color=COLORS["pill_off_bg"], corner_radius=12, width=130, height=28
        )
        pill.pack(side="left")
        pill.pack_propagate(False)
        ctk.CTkLabel(
            pill,
            text=item.status_label,
            font=app_font(12, "bold"),
            text_color=COLORS["pill_off_fg"],
        ).pack(expand=True)

        delay_text = f"تأخیر {item.delay_minutes} دقیقه" if item.delay_minutes else "بدون تأخیر"
        ctk.CTkLabel(
            card,
            text=f"کد {item.personnel_code}  ·  {item.jalali_date}  ·  ورود {item.check_in}  ·  {delay_text}",
            font=app_font(13),
            text_color=COLORS["muted"],
            anchor="e",
        ).pack(fill="x", padx=14, pady=(0, 8))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        time_entry = ctk.CTkEntry(
            actions,
            placeholder_text="ساعت خروج واقعی (HH:MM)",
            justify="right",
            font=app_font(13),
            height=34,
            width=200,
        )
        time_entry.pack(side="right", padx=(8, 0))
        error = ctk.CTkLabel(actions, text="", font=app_font(12), text_color=COLORS["danger"])
        error.pack(side="left")
        ctk.CTkButton(
            actions,
            text="ثبت خروج دستی",
            width=140,
            height=34,
            command=lambda att_id=item.id, entry=time_entry, err=error: self._complete(
                att_id, entry, err
            ),
        ).pack(side="right")

    def _complete(self, attendance_id: int, entry: ctk.CTkEntry, error: ctk.CTkLabel) -> None:
        try:
            self.attendance.complete_missed_checkout(attendance_id, entry.get())
        except ValueError as exc:
            error.configure(text=str(exc))
            return
        self.refresh()

    def _save_manual(self) -> None:
        label = self.employee_combo.get()
        employee_id = self._employees_by_label.get(label)
        if employee_id is None:
            self.form_error.configure(text="پرسنل را انتخاب کنید.")
            return
        try:
            self.attendance.save_manual_entry(
                employee_id=employee_id,
                jalali_date=self.date_entry.get(),
                check_in_time=self.checkin_entry.get(),
                check_out_time=self.checkout_entry.get(),
            )
        except ValueError as exc:
            self.form_error.configure(text=str(exc))
            return
        self.form_error.configure(text="")
        self.checkout_entry.delete(0, "end")
        self.refresh()
