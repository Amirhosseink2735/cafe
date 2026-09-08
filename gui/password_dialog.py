"""Dialog for changing the admin password."""

from __future__ import annotations

import customtkinter as ctk

from gui.style import COLORS, app_font, center_window
from services.auth_service import AuthService


class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, master, auth: AuthService) -> None:
        super().__init__(master)
        self.auth = auth
        self.title("تغییر رمز مدیر")
        self.resizable(False, False)
        self.transient(master)
        self.configure(fg_color=COLORS["cream"])
        center_window(self, 440, 430)
        self.grab_set()

        card = ctk.CTkFrame(self, corner_radius=22, fg_color=COLORS["card"])
        card.pack(expand=True, fill="both", padx=22, pady=22)

        ctk.CTkLabel(
            card,
            text="تغییر رمز عبور",
            font=app_font(20, "bold"),
            text_color=COLORS["espresso"],
        ).pack(pady=(18, 6))
        ctk.CTkLabel(
            card,
            text="رمز جدید باید حداقل ۴ کاراکتر باشد.",
            font=app_font(12),
            text_color=COLORS["muted"],
        ).pack(pady=(0, 14))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24)

        self.current_entry = self._labeled_entry(form, "رمز فعلی")
        self.new_entry = self._labeled_entry(form, "رمز جدید")
        self.confirm_entry = self._labeled_entry(form, "تکرار رمز جدید")

        self.error_label = ctk.CTkLabel(
            form, text="", font=app_font(12), text_color=COLORS["danger"], height=18
        )
        self.error_label.pack(fill="x")

        ctk.CTkButton(
            form,
            text="ذخیره رمز جدید",
            font=app_font(14, "bold"),
            height=44,
            command=self._save,
        ).pack(fill="x", pady=(6, 16))

        self.after(50, self.current_entry.focus_set)

    def _labeled_entry(self, parent, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(
            parent, text=label, font=app_font(13), anchor="e", text_color=COLORS["ink"]
        ).pack(fill="x")
        entry = ctk.CTkEntry(
            parent, show="*", justify="right", font=app_font(14), height=40
        )
        entry.pack(fill="x", pady=(4, 12))
        return entry

    def _save(self) -> None:
        new_password = self.new_entry.get().strip()
        confirm = self.confirm_entry.get().strip()
        if new_password != confirm:
            self.error_label.configure(text="رمز جدید و تکرار آن یکسان نیستند.")
            return
        try:
            self.auth.change_password(self.current_entry.get(), new_password)
        except ValueError as exc:
            self.error_label.configure(text=str(exc))
            return
        self.destroy()
