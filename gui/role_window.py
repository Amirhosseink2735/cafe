"""Home screen: staff kiosk or admin panel."""

from __future__ import annotations

import customtkinter as ctk

from database.db_manager import DatabaseManager
from gui.style import COLORS, app_font, center_window
from utils.jalali_helper import JalaliHelper


class RoleWindow(ctk.CTk):
    def __init__(self, db: DatabaseManager) -> None:
        super().__init__()
        self.db = db
        self.choice: str | None = None

        self.title("سامانه پرسنل کافه")
        self.configure(fg_color=COLORS["cream"])
        self.resizable(False, False)
        center_window(self, 720, 520)

        card = ctk.CTkFrame(self, corner_radius=28, fg_color=COLORS["card"])
        card.pack(expand=True, fill="both", padx=36, pady=36)

        ctk.CTkLabel(card, text="☕", font=ctk.CTkFont(size=44)).pack(pady=(36, 4))
        ctk.CTkLabel(
            card,
            text="سامانه پرسنل کافه",
            font=app_font(28, "bold"),
            text_color=COLORS["espresso"],
        ).pack()
        ctk.CTkLabel(
            card,
            text=JalaliHelper.today_str(),
            font=app_font(14),
            text_color=COLORS["caramel"],
        ).pack(pady=(4, 28))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(fill="x", padx=48, pady=(0, 40))

        ctk.CTkButton(
            buttons,
            text="کیوسک پرسنل",
            font=app_font(20, "bold"),
            height=72,
            command=lambda: self._choose("kiosk"),
        ).pack(fill="x", pady=(0, 12))
        ctk.CTkButton(
            buttons,
            text="پنل مدیر",
            font=app_font(18, "bold"),
            height=64,
            fg_color=COLORS["ghost"],
            hover_color=COLORS["ghost_hover"],
            text_color=COLORS["espresso"],
            command=lambda: self._choose("admin"),
        ).pack(fill="x")

    def _choose(self, choice: str) -> None:
        self.choice = choice
        self.destroy()
