"""Shared CustomTkinter appearance for cafe admin screens."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

FONT_FAMILY = "Segoe UI"
THEME_PATH = Path(__file__).resolve().parent / "themes" / "cafe.json"

COLORS = {
    "cream": "#F3EBE3",
    "card": "#FFF8F1",
    "espresso": "#6F4E37",
    "espresso_dark": "#5A3D2B",
    "caramel": "#C4A574",
    "muted": "#8A7360",
    "ink": "#3B2A1F",
    "success": "#3D7A5A",
    "success_hover": "#2F6248",
    "danger": "#B85C4A",
    "danger_hover": "#944738",
    "ghost": "#E8D9C8",
    "ghost_hover": "#D8C6B4",
    "pill_ok_bg": "#E4F2EA",
    "pill_ok_fg": "#2F6248",
    "pill_off_bg": "#F6E4DF",
    "pill_off_fg": "#944738",
    "avatar": "#6F4E37",
}


def app_font(size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def apply_theme() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme(str(THEME_PATH))


def center_window(window: ctk.CTk | ctk.CTkToplevel, width: int, height: int) -> None:
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x = max((screen_w - width) // 2, 0)
    y = max((screen_h - height) // 2, 0)
    window.geometry(f"{width}x{height}+{x}+{y}")


def initials_of(full_name: str) -> str:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return "؟"
    if len(parts) == 1:
        return parts[0][:1]
    return parts[0][:1] + parts[-1][:1]
