"""Touch-friendly leave request modal for the staff kiosk."""

from __future__ import annotations

import customtkinter as ctk

from gui.style import COLORS, app_font, center_window, close_window
from services.leave_service import LEAVE_DAILY, LEAVE_HOURLY, LeaveService
from utils.jalali_helper import JalaliHelper


class LeaveRequestDialog(ctk.CTkToplevel):
    def __init__(self, master, leave_service: LeaveService, employee_id: int, employee_name: str) -> None:
        super().__init__(master)
        self.leave_service = leave_service
        self.employee_id = employee_id
        self.submitted = False

        self.title("درخواست مرخصی")
        self.configure(fg_color=COLORS["cream"])
        self.resizable(False, False)
        self.transient(master)
        center_window(self, 560, 640)
        self.grab_set()

        card = ctk.CTkFrame(self, corner_radius=22, fg_color=COLORS["card"])
        card.pack(expand=True, fill="both", padx=20, pady=20)

        ctk.CTkLabel(
            card,
            text="ثبت درخواست مرخصی",
            font=app_font(22, "bold"),
            text_color=COLORS["espresso"],
        ).pack(pady=(18, 4))
        ctk.CTkLabel(
            card,
            text=employee_name,
            font=app_font(14),
            text_color=COLORS["muted"],
        ).pack(pady=(0, 16))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24)

        ctk.CTkLabel(form, text="نوع مرخصی", font=app_font(13), anchor="e").pack(fill="x")
        self.type_var = ctk.StringVar(value="روزانه")
        self.type_segment = ctk.CTkSegmentedButton(
            form,
            values=["روزانه", "ساعتی"],
            variable=self.type_var,
            font=app_font(14, "bold"),
            height=42,
            command=self._toggle_type,
        )
        self.type_segment.pack(fill="x", pady=(6, 14))

        self.start_date_entry = self._entry(form, "تاریخ شروع (YYYY/MM/DD)")
        self.end_date_entry = self._entry(form, "تاریخ پایان (YYYY/MM/DD)")
        self.start_time_entry = self._entry(form, "ساعت شروع (HH:MM)")
        self.end_time_entry = self._entry(form, "ساعت پایان (HH:MM)")

        today = JalaliHelper.today_str()
        self.start_date_entry.insert(0, today)
        self.end_date_entry.insert(0, today)

        ctk.CTkLabel(form, text="دلیل", font=app_font(13), anchor="e").pack(fill="x")
        self.reason_box = ctk.CTkTextbox(form, height=90, font=app_font(14))
        self.reason_box.pack(fill="x", pady=(4, 8))

        self.error_label = ctk.CTkLabel(
            form, text="", font=app_font(12), text_color=COLORS["danger"], height=22
        )
        self.error_label.pack(fill="x")

        ctk.CTkButton(
            form,
            text="ارسال درخواست",
            font=app_font(16, "bold"),
            height=48,
            command=self._submit,
        ).pack(fill="x", pady=(4, 18))

        self._toggle_type("روزانه")

    def _entry(self, parent, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=app_font(13), anchor="e").pack(fill="x")
        entry = ctk.CTkEntry(parent, justify="right", font=app_font(16), height=42)
        entry.pack(fill="x", pady=(4, 10))
        return entry

    def _toggle_type(self, value: str) -> None:
        hourly = value == "ساعتی"
        self._set_enabled(self.end_date_entry, not hourly)
        self._set_enabled(self.start_time_entry, hourly)
        self._set_enabled(self.end_time_entry, hourly)

    def _set_enabled(self, entry: ctk.CTkEntry, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        entry.configure(state=state)

    def _submit(self) -> None:
        leave_type = LEAVE_HOURLY if self.type_var.get() == "ساعتی" else LEAVE_DAILY
        reason = self.reason_box.get("1.0", "end").strip()
        try:
            self.leave_service.submit_request(
                employee_id=self.employee_id,
                leave_type=leave_type,
                reason=reason,
                start_date=self.start_date_entry.get(),
                end_date=self.end_date_entry.get(),
                start_time=self.start_time_entry.get(),
                end_time=self.end_time_entry.get(),
            )
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        self.submitted = True
        close_window(self)
