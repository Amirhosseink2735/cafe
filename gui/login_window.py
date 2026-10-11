"""Admin login window."""

from __future__ import annotations

import customtkinter as ctk

from database.db_manager import DatabaseManager
from gui.style import COLORS, app_font, apply_window_icon, center_window, close_window
from services.auth_service import AuthService
from utils.jalali_helper import JalaliHelper


class LoginWindow(ctk.CTk):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        apply_window_icon(self)
        self.db = db
        self.auth = AuthService(db)
        self.authenticated = False

        self.title("ورود مدیر | کافه")
        self.resizable(False, False)
        center_window(self, 520, 640)
        self.configure(fg_color=COLORS["cream"])

        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(expand=True, fill="both", padx=36, pady=32)

        card = ctk.CTkFrame(shell, corner_radius=28, fg_color=COLORS["card"])
        card.pack(expand=True, fill="both")

        ctk.CTkLabel(
            card,
            text="☕",
            font=ctk.CTkFont(size=48),
        ).pack(pady=(40, 8))
        ctk.CTkLabel(
            card,
            text="کافه",
            font=app_font(30, "bold"),
            text_color=COLORS["espresso"],
        ).pack()
        ctk.CTkLabel(
            card,
            text="سامانه مدیریت پرسنل",
            font=app_font(15),
            text_color=COLORS["muted"],
        ).pack(pady=(4, 6))
        ctk.CTkLabel(
            card,
            text=JalaliHelper.today_str(),
            font=app_font(12),
            text_color=COLORS["caramel"],
        ).pack(pady=(0, 28))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=48)

        ctk.CTkLabel(
            form,
            text="رمز عبور مدیر",
            font=app_font(13),
            text_color=COLORS["ink"],
            anchor="e",
        ).pack(fill="x")
        self.password_entry = ctk.CTkEntry(
            form,
            placeholder_text="رمز را وارد کنید",
            show="*",
            justify="right",
            font=app_font(16),
            height=48,
            border_width=1,
        )
        self.password_entry.pack(fill="x", pady=(6, 10))
        self.password_entry.bind("<Return>", lambda _event: self._login())

        self.error_label = ctk.CTkLabel(
            form,
            text="",
            font=app_font(12),
            text_color=COLORS["danger"],
            height=20,
        )
        self.error_label.pack(fill="x")

        ctk.CTkButton(
            form,
            text="ورود به پنل",
            font=app_font(16, "bold"),
            height=48,
            corner_radius=14,
            command=self._login,
        ).pack(fill="x", pady=(8, 18))

        hint = ctk.CTkFrame(form, fg_color=COLORS["ghost"], corner_radius=12)
        hint.pack(fill="x", pady=(0, 28))
        ctk.CTkLabel(
            hint,
            text="رمز پیش‌فرض: admin",
            font=app_font(12),
            text_color=COLORS["espresso"],
        ).pack(pady=10)

        self.after(120, self.password_entry.focus_set)

    def _login(self) -> None:
        password = self.password_entry.get()
        if self.auth.verify_password(password):
            self.authenticated = True
            close_window(self)
            return
        self.error_label.configure(text="رمز عبور نادرست است.")
        self.password_entry.delete(0, "end")
        self.password_entry.focus_set()
