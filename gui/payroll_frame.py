"""Admin bonuses, deductions, and current-month payroll report."""

from __future__ import annotations

import customtkinter as ctk

from gui.style import COLORS, app_font
from services.payroll_service import (
    TYPE_BONUS,
    TYPE_DEDUCTION,
    TYPE_LABELS,
    PayrollService,
    PayrollSummary,
)
from services.staff_service import StaffService
from utils.jalali_helper import JalaliHelper


def _toman(amount: float) -> str:
    return f"{int(round(amount)):,} تومان"


class PayrollFrame(ctk.CTkFrame):
    def __init__(self, master, payroll: PayrollService, staff: StaffService) -> None:
        super().__init__(master, fg_color="transparent")
        self.payroll = payroll
        self.staff = staff
        self._employees_by_label: dict[str, int] = {}

        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            heading,
            text=f"کارکرد و حقوق {JalaliHelper.month_label()}",
            font=app_font(22, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(side="right")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(expand=True, fill="both")
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_report(body)
        self._build_form(body)
        self.refresh()

    def _build_report(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(parent, corner_radius=18, fg_color=COLORS["card"])
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(
            panel,
            text="گزارش تجمیعی ماه جاری",
            font=app_font(16, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=16, pady=(14, 8))
        self.report_list = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.report_list.pack(expand=True, fill="both", padx=8, pady=(0, 12))

    def _build_form(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkScrollableFrame(parent, corner_radius=18, fg_color=COLORS["card"])
        panel.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(
            panel,
            text="ثبت پاداش / کسورات",
            font=app_font(16, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=12, pady=(14, 8))

        ctk.CTkLabel(panel, text="پرسنل", font=app_font(13), anchor="e").pack(fill="x", padx=12)
        self.employee_combo = ctk.CTkComboBox(
            panel, font=app_font(13), justify="right", height=40, values=["—"]
        )
        self.employee_combo.pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkLabel(panel, text="نوع", font=app_font(13), anchor="e").pack(fill="x", padx=12)
        self.type_var = ctk.StringVar(value=TYPE_LABELS[TYPE_BONUS])
        ctk.CTkSegmentedButton(
            panel,
            values=[TYPE_LABELS[TYPE_BONUS], TYPE_LABELS[TYPE_DEDUCTION]],
            variable=self.type_var,
            font=app_font(13, "bold"),
            height=38,
        ).pack(fill="x", padx=12, pady=(4, 8))

        self.date_entry = self._entry(panel, "تاریخ")
        self.date_entry.insert(0, JalaliHelper.today_str())
        self.amount_entry = self._entry(panel, "مبلغ (تومان)")
        self.reason_entry = self._entry(panel, "دلیل")

        self.form_error = ctk.CTkLabel(
            panel, text="", font=app_font(12), text_color=COLORS["danger"]
        )
        self.form_error.pack(fill="x", padx=12)
        ctk.CTkButton(
            panel, text="ثبت", height=42, command=self._save_adjustment
        ).pack(fill="x", padx=12, pady=(4, 14))

        ctk.CTkLabel(
            panel,
            text="ثبت‌های این ماه",
            font=app_font(14, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=12, pady=(4, 6))
        self.adjustment_list = ctk.CTkFrame(panel, fg_color="transparent")
        self.adjustment_list.pack(fill="x", padx=8, pady=(0, 16))

    def _entry(self, parent, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=app_font(13), anchor="e").pack(fill="x", padx=12)
        entry = ctk.CTkEntry(parent, justify="right", font=app_font(14), height=38)
        entry.pack(fill="x", padx=12, pady=(4, 8))
        return entry

    def refresh(self) -> None:
        employees = self.staff.list_employees(include_inactive=False)
        self._employees_by_label = {
            f"{emp.full_name}  |  {emp.personnel_code}": emp.id for emp in employees
        }
        labels = list(self._employees_by_label.keys()) or ["پرسنل فعالی نیست"]
        current = self.employee_combo.get()
        self.employee_combo.configure(values=labels)
        self.employee_combo.set(current if current in self._employees_by_label else labels[0])

        for child in self.report_list.winfo_children():
            child.destroy()
        summaries = self.payroll.month_summaries()
        if not summaries:
            ctk.CTkLabel(
                self.report_list,
                text="هنوز کارمندی برای گزارش نیست.",
                font=app_font(14),
                text_color=COLORS["muted"],
            ).pack(pady=28)
        else:
            for item in summaries:
                self._add_summary_card(item)

        for child in self.adjustment_list.winfo_children():
            child.destroy()
        adjustments = self.payroll.list_adjustments()
        if not adjustments:
            ctk.CTkLabel(
                self.adjustment_list,
                text="پاداش یا کسوراتی در این ماه ثبت نشده.",
                font=app_font(12),
                text_color=COLORS["muted"],
            ).pack(pady=8)
            return
        for item in adjustments:
            color = COLORS["success"] if item.type == TYPE_BONUS else COLORS["danger"]
            sign = "+" if item.type == TYPE_BONUS else "−"
            ctk.CTkLabel(
                self.adjustment_list,
                text=f"{item.employee_name}  ·  {item.type_label}  {sign}{_toman(item.amount)}\n{item.jalali_date} — {item.reason}",
                font=app_font(12),
                text_color=color,
                anchor="e",
                justify="right",
            ).pack(fill="x", pady=4)

    def _add_summary_card(self, item: PayrollSummary) -> None:
        card = ctk.CTkFrame(self.report_list, corner_radius=16, fg_color=COLORS["cream"])
        card.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(
            card,
            text=item.employee_name,
            font=app_font(16, "bold"),
            text_color=COLORS["ink"],
            anchor="e",
        ).pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            card,
            text=(
                f"کارکرد: {item.worked_hours_label}  ·  "
                f"{item.completed_days} روز حضور  ·  "
                f"{item.absence_days} روز غیبت"
            ),
            font=app_font(12),
            text_color=COLORS["muted"],
            anchor="e",
        ).pack(fill="x", padx=14)
        ctk.CTkLabel(
            card,
            text=(
                f"تأخیر {item.delay_minutes} دقیقه  ·  "
                f"تعجیل {item.early_leave_minutes} دقیقه  ·  "
                f"اضافه‌کار {item.overtime_minutes} دقیقه"
            ),
            font=app_font(12),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=14, pady=(2, 2))
        ctk.CTkLabel(
            card,
            text=(
                f"پایه {_toman(item.base_pay)}  + پاداش {_toman(item.bonus_total)}  "
                f"− کسورات {_toman(item.deduction_total)}"
            ),
            font=app_font(12),
            text_color=COLORS["muted"],
            anchor="e",
        ).pack(fill="x", padx=14)
        ctk.CTkLabel(
            card,
            text=f"حقوق نهایی: {_toman(item.net_pay)}",
            font=app_font(15, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=14, pady=(2, 12))

    def _save_adjustment(self) -> None:
        employee_id = self._employees_by_label.get(self.employee_combo.get())
        if employee_id is None:
            self.form_error.configure(text="پرسنل را انتخاب کنید.")
            return
        kind = TYPE_BONUS if self.type_var.get() == TYPE_LABELS[TYPE_BONUS] else TYPE_DEDUCTION
        try:
            self.payroll.add_adjustment(
                employee_id=employee_id,
                adjustment_type=kind,
                amount=self.amount_entry.get(),
                reason=self.reason_entry.get(),
                jalali_date=self.date_entry.get(),
            )
        except ValueError as exc:
            self.form_error.configure(text=str(exc))
            return
        self.form_error.configure(text="")
        self.amount_entry.delete(0, "end")
        self.reason_entry.delete(0, "end")
        self.refresh()
