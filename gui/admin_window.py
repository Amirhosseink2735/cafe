"""Admin staff and shift management window."""

from __future__ import annotations

from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from database.db_manager import DatabaseManager
from gui.attendance_inbox import AttendanceInboxFrame
from gui.leave_inbox import LeaveInboxFrame
from gui.password_dialog import ChangePasswordDialog
from gui.payroll_frame import PayrollFrame
from gui.report_frame import ReportFrame
from gui.style import COLORS, app_font, apply_window_icon, center_window, close_window, initials_of, theme_button_text, toggle_appearance
from services.attendance_service import AttendanceService
from services.auth_service import AuthService
from services.leave_service import LeaveService
from services.backup_service import BackupService
from services.payroll_service import PayrollService
from services.report_service import ReportService
from services.staff_service import EmployeeRecord, StaffService
from utils.jalali_helper import JalaliHelper


class AdminWindow(ctk.CTk):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        apply_window_icon(self)
        self.db = db
        self.auth = AuthService(db)
        self.staff = StaffService(db)
        self.leave_service = LeaveService(db)
        self.attendance_service = AttendanceService(db)
        self.payroll_service = PayrollService(db)
        self.report_service = ReportService(db)
        self.backup_service = BackupService(db)
        self.logout_requested = False
        self.selected_employee_id: Optional[int] = None

        self.title("پنل مدیریت پرسنل و شیفت")
        self.configure(fg_color=COLORS["cream"])
        center_window(self, 1360, 860)
        self.minsize(1180, 740)

        self._build_header()
        self._build_body()
        self.refresh_list()
        self._sync_leave_badge()
        self._sync_attendance_badge()
        self.protocol("WM_DELETE_WINDOW", self._logout)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, height=88, corner_radius=0, fg_color=COLORS["header"])
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="right", padx=24)
        ctk.CTkLabel(
            brand,
            text="☕  مدیریت پرسنل کافه",
            font=app_font(22, "bold"),
            text_color=COLORS["on_espresso"],
        ).pack(anchor="e")
        ctk.CTkLabel(
            brand,
            text=f"امروز {JalaliHelper.today_str()}",
            font=app_font(12),
            text_color=COLORS["caramel"],
        ).pack(anchor="e")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="left", padx=20)
        ctk.CTkButton(
            actions,
            text="خروج",
            width=96,
            height=38,
            fg_color=COLORS["espresso_dark"],
            hover_color=COLORS["espresso_dark"],
            text_color=COLORS["on_espresso"],
            command=self._logout,
        ).pack(side="left", padx=(0, 8), pady=24)
        ctk.CTkButton(
            actions,
            text="تغییر رمز",
            width=120,
            height=38,
            fg_color=COLORS["gold"],
            hover_color=COLORS["caramel"],
            text_color=COLORS["ink"],
            command=self._change_password,
        ).pack(side="left", pady=24)
        self.theme_button = ctk.CTkButton(
            actions,
            text=theme_button_text(self.db),
            width=100,
            height=38,
            fg_color=COLORS["espresso_dark"],
            hover_color=COLORS["espresso_dark"],
            text_color=COLORS["on_espresso"],
            command=self._toggle_theme,
        )
        self.theme_button.pack(side="left", padx=(8, 0), pady=24)
        ctk.CTkButton(
            actions,
            text="پشتیبان",
            width=90,
            height=38,
            fg_color=COLORS["espresso_dark"],
            hover_color=COLORS["espresso_dark"],
            text_color=COLORS["on_espresso"],
            command=self._backup,
        ).pack(side="left", padx=(8, 0), pady=24)
        ctk.CTkButton(
            actions,
            text="بازیابی",
            width=90,
            height=38,
            fg_color=COLORS["espresso_dark"],
            hover_color=COLORS["espresso_dark"],
            text_color=COLORS["on_espresso"],
            command=self._restore,
        ).pack(side="left", padx=(8, 0), pady=24)

        self.status_label = ctk.CTkLabel(
            header,
            text="",
            font=app_font(12),
            text_color=COLORS["on_espresso"],
        )
        self.status_label.pack(side="left", padx=12)
        self.leave_badge = ctk.CTkLabel(
            header,
            text="",
            font=app_font(12, "bold"),
            text_color=COLORS["gold"],
        )
        self.leave_badge.pack(side="left", padx=8)
        self.attendance_badge = ctk.CTkLabel(
            header,
            text="",
            font=app_font(12, "bold"),
            text_color=COLORS["on_espresso"],
        )
        self.attendance_badge.pack(side="left", padx=8)

    def _build_body(self) -> None:
        self.tabs = ctk.CTkTabview(self, command=self._on_tab_change)
        self.tabs.pack(expand=True, fill="both", padx=20, pady=18)
        staff_tab = self.tabs.add("پرسنل و شیفت")
        leave_tab = self.tabs.add("کارتابل مرخصی")
        attendance_tab = self.tabs.add("اصلاح دستی ترددها")
        payroll_tab = self.tabs.add("حقوق و کارکرد")
        report_tab = self.tabs.add("گزارش ماهانه تردد")

        staff_tab.grid_columnconfigure(0, weight=3)
        staff_tab.grid_columnconfigure(1, weight=2)
        staff_tab.grid_rowconfigure(0, weight=1)
        self._build_list_panel(staff_tab)
        self._build_form_panel(staff_tab)

        self.leave_inbox = LeaveInboxFrame(
            leave_tab,
            self.leave_service,
            on_changed=self._sync_leave_badge,
        )
        self.leave_inbox.pack(expand=True, fill="both")

        self.attendance_inbox = AttendanceInboxFrame(
            attendance_tab,
            self.attendance_service,
            self.staff,
            on_changed=self._sync_attendance_badge,
        )
        self.attendance_inbox.pack(expand=True, fill="both")

        self.payroll_frame = PayrollFrame(payroll_tab, self.payroll_service, self.staff)
        self.payroll_frame.pack(expand=True, fill="both")

        self.report_frame = ReportFrame(report_tab, self.report_service, self.staff)
        self.report_frame.pack(expand=True, fill="both")

    def _on_tab_change(self, _value: str | None = None) -> None:
        selected = _value or self.tabs.get()
        if selected == "کارتابل مرخصی":
            self.leave_inbox.refresh()
        elif selected == "اصلاح دستی ترددها":
            self.attendance_inbox.refresh()
        elif selected == "حقوق و کارکرد":
            self.payroll_frame.refresh()
        elif selected == "گزارش ماهانه تردد":
            self.report_frame.refresh()

    def _sync_leave_badge(self) -> None:
        pending = self.leave_service.pending_count()
        if pending:
            self.leave_badge.configure(text=f"{pending} مرخصی در انتظار")
        else:
            self.leave_badge.configure(text="")

    def _sync_attendance_badge(self) -> None:
        incomplete = self.attendance_service.incomplete_count()
        if incomplete:
            self.attendance_badge.configure(text=f"{incomplete} تردد بلاتکلیف")
        else:
            self.attendance_badge.configure(text="")

    def _build_list_panel(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(parent, corner_radius=22, fg_color=COLORS["card"])
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        heading = ctk.CTkFrame(panel, fg_color="transparent")
        heading.pack(fill="x", padx=20, pady=(18, 8))
        ctk.CTkLabel(
            heading,
            text="لیست پرسنل",
            font=app_font(20, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(side="right")
        self.count_label = ctk.CTkLabel(
            heading,
            text="",
            font=app_font(12),
            text_color=COLORS["muted"],
            anchor="w",
        )
        self.count_label.pack(side="left")

        self.list_frame = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", corner_radius=12
        )
        self.list_frame.pack(expand=True, fill="both", padx=12, pady=(0, 14))

    def _build_form_panel(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkScrollableFrame(parent, corner_radius=22, fg_color=COLORS["card"])
        panel.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="ثبت و ویرایش کارمند",
            font=app_font(20, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=8, pady=(14, 12))

        names = ctk.CTkFrame(panel, fg_color="transparent")
        names.pack(fill="x", padx=8)
        names.grid_columnconfigure((0, 1), weight=1)
        self.last_name_entry = self._grid_entry(names, "نام خانوادگی", 0, 0)
        self.first_name_entry = self._grid_entry(names, "نام", 0, 1)

        self.code_entry = self._form_entry(panel, "کد پرسنلی")
        self.phone_entry = self._form_entry(panel, "شماره تماس")
        self.rate_entry = self._form_entry(panel, "دستمزد ساعتی (تومان)")

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkButton(
            buttons,
            text="ذخیره کارمند",
            height=42,
            command=self._save_employee,
        ).pack(side="right", padx=(6, 0), expand=True, fill="x")
        ctk.CTkButton(
            buttons,
            text="فرم جدید",
            height=42,
            fg_color=COLORS["ghost"],
            hover_color=COLORS["ghost_hover"],
            text_color=COLORS["espresso"],
            command=self._reset_forms,
        ).pack(side="right", expand=True, fill="x")

        divider = ctk.CTkFrame(panel, height=2, fg_color=COLORS["ghost"])
        divider.pack(fill="x", padx=8, pady=14)

        ctk.CTkLabel(
            panel,
            text="شیفت ثابت روزانه",
            font=app_font(18, "bold"),
            text_color=COLORS["espresso"],
            anchor="e",
        ).pack(fill="x", padx=8)

        self.selected_label = ctk.CTkLabel(
            panel,
            text="کارمندی انتخاب نشده است.",
            font=app_font(13),
            anchor="e",
            text_color=COLORS["muted"],
        )
        self.selected_label.pack(fill="x", padx=8, pady=(2, 10))

        times = ctk.CTkFrame(panel, fg_color="transparent")
        times.pack(fill="x", padx=8)
        times.grid_columnconfigure((0, 1, 2), weight=1)
        self.tolerance_entry = self._grid_entry(times, "فرجه (دقیقه)", 0, 0)
        self.end_entry = self._grid_entry(times, "ساعت پایان", 0, 1)
        self.start_entry = self._grid_entry(times, "ساعت شروع", 0, 2)
        self.tolerance_entry.insert(0, "5")
        self.start_entry.configure(placeholder_text="08:00")
        self.end_entry.configure(placeholder_text="16:00")

        ctk.CTkButton(
            panel,
            text="ذخیره شیفت",
            height=42,
            command=self._save_shift,
        ).pack(fill="x", padx=8, pady=(8, 20))

    def _form_entry(self, parent, label: str) -> ctk.CTkEntry:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkLabel(
            wrap, text=label, font=app_font(13), anchor="e", text_color=COLORS["ink"]
        ).pack(fill="x")
        entry = ctk.CTkEntry(wrap, justify="right", font=app_font(14), height=40)
        entry.pack(fill="x", pady=(4, 0))
        return entry

    def _grid_entry(self, parent, label: str, row: int, column: int) -> ctk.CTkEntry:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.grid(row=row, column=column, sticky="ew", padx=4, pady=(0, 8))
        ctk.CTkLabel(
            wrap, text=label, font=app_font(13), anchor="e", text_color=COLORS["ink"]
        ).pack(fill="x")
        entry = ctk.CTkEntry(wrap, justify="right", font=app_font(14), height=40)
        entry.pack(fill="x", pady=(4, 0))
        return entry

    def refresh_list(self) -> None:
        for child in self.list_frame.winfo_children():
            child.destroy()

        employees = self.staff.list_employees(include_inactive=True)
        active_count = sum(1 for employee in employees if employee.is_active)
        self.count_label.configure(text=f"{active_count} فعال از {len(employees)} نفر")

        if not employees:
            empty = ctk.CTkFrame(self.list_frame, fg_color=COLORS["cream"], corner_radius=18)
            empty.pack(fill="x", padx=8, pady=28)
            ctk.CTkLabel(empty, text="☕", font=ctk.CTkFont(size=36)).pack(pady=(28, 8))
            ctk.CTkLabel(
                empty,
                text="هنوز کارمندی ثبت نشده",
                font=app_font(16, "bold"),
                text_color=COLORS["espresso"],
            ).pack()
            ctk.CTkLabel(
                empty,
                text="از فرم سمت راست اولین پرسنل را اضافه کنید.",
                font=app_font(13),
                text_color=COLORS["muted"],
            ).pack(pady=(4, 28))
            return

        for employee in employees:
            self._add_employee_card(employee)

    def _add_employee_card(self, employee: EmployeeRecord) -> None:
        selected = employee.id == self.selected_employee_id
        card = ctk.CTkFrame(
            self.list_frame,
            corner_radius=18,
            fg_color=COLORS["selected"] if selected else COLORS["cream"],
            border_width=2 if selected else 0,
            border_color=COLORS["caramel"],
        )
        card.pack(fill="x", pady=6, padx=6)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 6))

        avatar = ctk.CTkFrame(top, width=48, height=48, corner_radius=24, fg_color=COLORS["avatar"])
        avatar.pack(side="right", padx=(8, 0))
        avatar.pack_propagate(False)
        ctk.CTkLabel(
            avatar,
            text=initials_of(employee.full_name),
            font=app_font(14, "bold"),
            text_color=COLORS["on_espresso"],
        ).pack(expand=True)

        identity = ctk.CTkFrame(top, fg_color="transparent")
        identity.pack(side="right", fill="x", expand=True)
        ctk.CTkLabel(
            identity,
            text=employee.full_name,
            font=app_font(16, "bold"),
            text_color=COLORS["ink"] if employee.is_active else COLORS["muted"],
            anchor="e",
        ).pack(fill="x")
        ctk.CTkLabel(
            identity,
            text=f"کد {employee.personnel_code}   |   {employee.phone or 'بدون شماره'}",
            font=app_font(12),
            text_color=COLORS["muted"],
            anchor="e",
        ).pack(fill="x")

        pill_bg = COLORS["pill_ok_bg"] if employee.is_active else COLORS["pill_off_bg"]
        pill_fg = COLORS["pill_ok_fg"] if employee.is_active else COLORS["pill_off_fg"]
        pill = ctk.CTkFrame(top, fg_color=pill_bg, corner_radius=12, width=86, height=28)
        pill.pack(side="left", padx=(0, 8))
        pill.pack_propagate(False)
        ctk.CTkLabel(
            pill,
            text="فعال" if employee.is_active else "غیرفعال",
            font=app_font(12, "bold"),
            text_color=pill_fg,
        ).pack(expand=True)

        meta = ctk.CTkFrame(card, fg_color="transparent")
        meta.pack(fill="x", padx=14, pady=(0, 8))
        rate = (
            f"{int(employee.hourly_rate):,} تومان"
            if employee.hourly_rate is not None
            else "دستمزد ثبت نشده"
        )
        ctk.CTkLabel(
            meta,
            text=f"🕒  {employee.shift_label}     ·     💰  {rate}",
            font=app_font(12),
            text_color=COLORS["espresso"] if employee.is_active else COLORS["muted"],
            anchor="e",
        ).pack(fill="x")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(
            actions,
            text="ویرایش",
            width=90,
            height=32,
            command=lambda emp_id=employee.id: self._load_employee(emp_id),
        ).pack(side="right", padx=(6, 0))
        if employee.is_active:
            ctk.CTkButton(
                actions,
                text="غیرفعال",
                width=90,
                height=32,
                fg_color=COLORS["danger"],
                hover_color=COLORS["danger_hover"],
                command=lambda emp_id=employee.id, name=employee.full_name: self._deactivate(
                    emp_id, name
                ),
            ).pack(side="right")
        else:
            ctk.CTkButton(
                actions,
                text="فعال‌سازی",
                width=90,
                height=32,
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                command=lambda emp_id=employee.id: self._activate(emp_id),
            ).pack(side="right")

    def _flash_status(self, text: str) -> None:
        self.status_label.configure(text=text)

        def _clear() -> None:
            if self.winfo_exists():
                self.status_label.configure(text="")

        if getattr(self, "_status_job", None):
            try:
                self.after_cancel(self._status_job)
            except Exception:
                pass
        self._status_job = self.after(3500, _clear)

    def _load_employee(self, employee_id: int) -> None:
        employee = self.staff.get_employee(employee_id)
        if employee is None:
            messagebox.showerror("خطا", "کارمند پیدا نشد.")
            return
        self.selected_employee_id = employee.id
        self._set_entry(self.first_name_entry, employee.first_name)
        self._set_entry(self.last_name_entry, employee.last_name)
        self._set_entry(self.code_entry, employee.personnel_code)
        self._set_entry(self.phone_entry, employee.phone)
        self._set_entry(
            self.rate_entry,
            "" if employee.hourly_rate is None else str(int(employee.hourly_rate)),
        )
        self._set_entry(self.start_entry, employee.shift_start or "")
        self._set_entry(self.end_entry, employee.shift_end or "")
        self._set_entry(
            self.tolerance_entry,
            "5" if employee.tolerance_minutes is None else str(employee.tolerance_minutes),
        )
        self.selected_label.configure(text=f"شیفت برای {employee.full_name}")
        self.refresh_list()

    def _save_employee(self) -> None:
        try:
            employee_id = self.staff.save_employee(
                first_name=self.first_name_entry.get(),
                last_name=self.last_name_entry.get(),
                personnel_code=self.code_entry.get(),
                phone=self.phone_entry.get(),
                hourly_rate=self.rate_entry.get(),
                employee_id=self.selected_employee_id,
            )
        except ValueError as exc:
            messagebox.showerror("خطای اعتبارسنجی", str(exc))
            return
        self.selected_employee_id = employee_id
        employee = self.staff.get_employee(employee_id)
        if employee:
            self.selected_label.configure(text=f"شیفت برای {employee.full_name}")
        self.refresh_list()
        self._flash_status("اطلاعات کارمند ذخیره شد.")

    def _save_shift(self) -> None:
        if self.selected_employee_id is None:
            messagebox.showwarning(
                "انتخاب کارمند", "ابتدا کارمند را ذخیره یا از لیست ویرایش کنید."
            )
            return
        try:
            self.staff.save_shift(
                employee_id=self.selected_employee_id,
                start_time=self.start_entry.get(),
                end_time=self.end_entry.get(),
                tolerance_minutes=self.tolerance_entry.get(),
            )
        except ValueError as exc:
            messagebox.showerror("خطای اعتبارسنجی", str(exc))
            return
        self.refresh_list()
        self._flash_status("شیفت ثابت روزانه ذخیره شد.")

    def _deactivate(self, employee_id: int, name: str) -> None:
        if not messagebox.askyesno(
            "غیرفعال‌سازی",
            f"کارمند «{name}» غیرفعال شود؟ سابقه او حذف نمی‌شود.",
        ):
            return
        self.staff.deactivate_employee(employee_id)
        if self.selected_employee_id == employee_id:
            self._reset_forms()
        self.refresh_list()
        self._flash_status("کارمند غیرفعال شد.")

    def _activate(self, employee_id: int) -> None:
        self.staff.activate_employee(employee_id)
        self.refresh_list()
        self._flash_status("کارمند دوباره فعال شد.")

    def _reset_forms(self) -> None:
        self.selected_employee_id = None
        for entry in (
            self.first_name_entry,
            self.last_name_entry,
            self.code_entry,
            self.phone_entry,
            self.rate_entry,
            self.start_entry,
            self.end_entry,
        ):
            self._set_entry(entry, "")
        self._set_entry(self.tolerance_entry, "5")
        self.selected_label.configure(text="کارمندی انتخاب نشده است.")
        self.refresh_list()

    def _backup(self) -> None:
        today = JalaliHelper.today_str().replace("/", "-")
        path = filedialog.asksaveasfilename(
            title="ذخیره نسخه پشتیبان",
            defaultextension=".db",
            filetypes=[("SQLite", "*.db"), ("همه فایل‌ها", "*.*")],
            initialfile=f"cafe_backup_{today}.db",
        )
        if not path:
            return
        try:
            saved = self.backup_service.backup_to(path)
        except ValueError as exc:
            messagebox.showerror("خطا", str(exc))
            return
        messagebox.showinfo("موفق", f"نسخه پشتیبان ذخیره شد:\n{saved}")

    def _restore(self) -> None:
        if not messagebox.askyesno(
            "بازیابی",
            "بازیابی، اطلاعات فعلی را با فایل پشتیبان جایگزین می‌کند. ادامه می‌دهید؟",
        ):
            return
        path = filedialog.askopenfilename(
            title="انتخاب فایل پشتیبان",
            filetypes=[("SQLite", "*.db"), ("همه فایل‌ها", "*.*")],
        )
        if not path:
            return
        try:
            self.backup_service.restore_from(path)
        except ValueError as exc:
            messagebox.showerror("خطا", str(exc))
            return
        messagebox.showinfo("موفق", "اطلاعات بازیابی شد. لطفاً صفحه را یک‌بار ببندید و دوباره باز کنید.")
        self.refresh_list()
        self.leave_inbox.refresh()
        self.attendance_inbox.refresh()
        self.payroll_frame.refresh()
        self.report_frame.refresh()

    def _change_password(self) -> None:
        ChangePasswordDialog(self, self.auth)

    def _toggle_theme(self) -> None:
        toggle_appearance(self.db)
        self.theme_button.configure(text=theme_button_text(self.db))

    def _logout(self) -> None:
        self.logout_requested = True
        close_window(self)

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)
