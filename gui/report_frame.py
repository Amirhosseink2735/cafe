"""Admin monthly attendance report and Excel export."""

from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from gui.style import COLORS, app_font
from services.report_service import EmployeeMonthReport, MonthlyAttendanceReport, ReportService
from services.staff_service import StaffService
from services.work_time import minutes_label
from utils.jalali_helper import MONTH_NAMES, JalaliHelper


ALL_STAFF = "همه پرسنل"


class ReportFrame(ctk.CTkFrame):
    def __init__(self, master, reports: ReportService, staff: StaffService) -> None:
        super().__init__(master, fg_color="transparent")
        self.reports = reports
        self.staff = staff
        self._employees_by_label: dict[str, Optional[int]] = {ALL_STAFF: None}
        self._current: Optional[MonthlyAttendanceReport] = None
        self._refreshing = False
        self._exporting = False

        today = JalaliHelper.today()
        years = [str(year) for year in range(today.year - 5, today.year + 2)]
        months = [f"{index:02d} — {MONTH_NAMES[index]}" for index in range(1, 13)]

        heading = ctk.CTkFrame(self, fg_color="transparent")
        heading.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            heading,
            text="گزارش ماهانه تردد پرسنل",
            font=app_font(22, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(side="right")

        filters = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=16)
        filters.pack(fill="x", pady=(0, 10))

        self.year_menu = ctk.CTkOptionMenu(filters, values=years, width=110, font=app_font(13))
        self.year_menu.set(str(today.year))
        self.year_menu.pack(side="right", padx=(8, 14), pady=12)

        self.month_menu = ctk.CTkOptionMenu(filters, values=months, width=180, font=app_font(13))
        self.month_menu.set(months[today.month - 1])
        self.month_menu.pack(side="right", padx=8, pady=12)

        self.search_entry = ctk.CTkEntry(
            filters,
            placeholder_text="جست‌وجو نام یا کد پرسنلی",
            justify="right",
            font=app_font(13),
            height=36,
            width=220,
        )
        self.search_entry.pack(side="right", padx=8, pady=12)
        self.search_entry.bind("<Return>", lambda _e: self.refresh())

        self.staff_menu = ctk.CTkOptionMenu(
            filters,
            values=[ALL_STAFF],
            width=220,
            font=app_font(13),
        )
        self.staff_menu.set(ALL_STAFF)
        self.staff_menu.pack(side="right", padx=8, pady=12)

        ctk.CTkButton(
            filters, text="اعمال فیلتر", width=110, height=36, command=self.refresh
        ).pack(side="left", padx=10, pady=12)
        ctk.CTkButton(
            filters,
            text="دریافت خروجی اکسل",
            width=160,
            height=36,
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            command=self._export_excel,
        ).pack(side="left", padx=(0, 10), pady=12)

        self.meta_label = ctk.CTkLabel(
            self, text="", font=app_font(13), text_color=COLORS["muted"], anchor="e"
        )
        self.meta_label.pack(fill="x", pady=(0, 6))

        self.list_frame = ctk.CTkScrollableFrame(self, corner_radius=18, fg_color=COLORS["card"])
        self.list_frame.pack(expand=True, fill="both")
        self.year_menu.configure(command=lambda _v: self.refresh())
        self.month_menu.configure(command=lambda _v: self.refresh())
        self.staff_menu.configure(command=lambda _v: self.refresh())
        self.refresh()

    def _selected_year_month(self) -> tuple[int, int]:
        year = int(self.year_menu.get())
        month = int(self.month_menu.get().split("—")[0].strip())
        return year, month

    def refresh(self) -> None:
        if not getattr(self, "list_frame", None) or self._refreshing:
            return
        self._refreshing = True
        try:
            self._refresh_body()
        finally:
            self._refreshing = False

    def _refresh_body(self) -> None:
        employees = self.staff.list_employees(include_inactive=True)
        self._employees_by_label = {ALL_STAFF: None}
        for emp in employees:
            self._employees_by_label[f"{emp.full_name}  |  {emp.personnel_code}"] = emp.id
        labels = list(self._employees_by_label.keys())
        current = self.staff_menu.get()
        self.staff_menu.configure(values=labels)
        self.staff_menu.set(current if current in self._employees_by_label else ALL_STAFF)

        year, month = self._selected_year_month()
        employee_id = self._employees_by_label.get(self.staff_menu.get())
        self._current = self.reports.build_month_report(
            year=year,
            month=month,
            employee_id=employee_id,
            search=self.search_entry.get(),
        )
        for child in self.list_frame.winfo_children():
            child.destroy()
        report = self._current
        self.meta_label.configure(
            text=(
                f"{report.month_label}  ·  از {report.start_date} تا {report.end_date}  ·  "
                f"{len(report.employees)} پرسنل"
            )
        )
        if not report.employees:
            ctk.CTkLabel(
                self.list_frame,
                text="پرسنلی با این فیلتر پیدا نشد.",
                font=app_font(15),
                text_color=COLORS["muted"],
            ).pack(pady=40)
            return
        for item in report.employees:
            self._add_employee_card(item)

    def _add_employee_card(self, item: EmployeeMonthReport) -> None:
        card = ctk.CTkFrame(self.list_frame, corner_radius=16, fg_color=COLORS["cream"])
        card.pack(fill="x", padx=8, pady=8)
        status = "فعال" if item.employee.is_active else "غیرفعال"
        ctk.CTkLabel(
            card,
            text=f"{item.employee.full_name}  |  {item.employee.personnel_code}  ({status})",
            font=app_font(16, "bold"),
            text_color=COLORS["ink"],
            anchor="e",
        ).pack(fill="x", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            card,
            text=(
                f"حضور {item.presence_days} روز  ·  "
                f"ناقص {item.incomplete_days} روز  ·  "
                f"کارکرد {minutes_label(item.worked_minutes)}  ·  "
                f"تأخیر {item.delay_minutes}  ·  "
                f"تعجیل {item.early_leave_minutes}  ·  "
                f"اضافه‌کار {item.overtime_minutes} دقیقه"
            ),
            font=app_font(12),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=14, pady=(0, 8))

        headers = (
            "وضعیت روز",
            "ثبت",
            "اضافه‌کار",
            "تعجیل",
            "تأخیر",
            "کارکرد",
            "خروج",
            "ورود",
            "تاریخ",
        )
        weights = (3, 2, 2, 2, 2, 2, 2, 2, 3)
        table = ctk.CTkFrame(card, fg_color="transparent")
        table.pack(fill="x", padx=8, pady=(0, 10))
        column_count = len(headers)
        for column in range(column_count):
            right_index = column_count - 1 - column
            table.grid_columnconfigure(column, weight=weights[right_index], uniform="attendance")

        self._paint_attendance_row(table, 0, headers, bold=True, color=COLORS["muted"])
        row_index = 1
        for day in item.days:
            if not day.check_in and not day.check_out and day.day_label == "عدم ثبت تردد":
                continue
            values = (
                day.day_label,
                "دستی" if day.is_manual_entry else "عادی",
                str(day.overtime_minutes),
                str(day.early_leave_minutes),
                str(day.delay_minutes),
                minutes_label(day.worked_minutes),
                day.check_out or "—",
                day.check_in or "—",
                day.jalali_date,
            )
            color = COLORS["danger"] if day.is_incomplete else COLORS["ink"]
            self._paint_attendance_row(table, row_index, values, color=color)
            row_index += 1

    def _paint_attendance_row(
        self,
        table: ctk.CTkFrame,
        row_index: int,
        values: tuple[str, ...],
        *,
        bold: bool = False,
        color: tuple[str, str] | str,
    ) -> None:
        column_count = len(values)
        for index, value in enumerate(values):
            ctk.CTkLabel(
                table,
                text=value,
                font=app_font(11, "bold" if bold else "normal"),
                text_color=color,
                anchor="center",
            ).grid(row=row_index, column=column_count - 1 - index, sticky="ew", padx=2, pady=3)

    def _export_excel(self) -> None:
        if self._exporting:
            return
        self._exporting = True
        try:
            self._do_export_excel()
        finally:
            self._exporting = False

    def _do_export_excel(self) -> None:
        if self._current is None:
            self.refresh()
        report = self._current
        if report is None or not report.employees:
            messagebox.showerror("خطا", "گزارشی برای خروجی وجود ندارد.")
            return
        suggested = self.reports.default_excel_name(report.year, report.month)
        path = filedialog.asksaveasfilename(
            title="ذخیره گزارش اکسل",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=suggested,
        )
        if not path:
            return
        try:
            saved = self.reports.export_excel(report, path)
        except ValueError as exc:
            messagebox.showerror("خطا", str(exc))
            return
        messagebox.showinfo("موفق", f"فایل اکسل ذخیره شد:\n{saved}")
