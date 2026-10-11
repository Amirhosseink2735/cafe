"""Shared CustomTkinter appearance, Vazir font, and light/dark colors."""

from __future__ import annotations

import customtkinter as ctk
from customtkinter.windows.widgets.font.font_manager import FontManager

from utils.paths import fonts_dir, icon_path, theme_path

FONT_FAMILY = "Segoe UI"
_FONTS_LOADED = False

# Light / dark pairs. Original cafe espresso palette.
COLORS = {
    "cream": ("#F3EBE3", "#1C1612"),
    "card": ("#FFF8F1", "#2A221C"),
    "selected": ("#F7EFE6", "#332920"),
    "espresso": ("#6F4E37", "#C4A574"),
    "espresso_dark": ("#5A3D2B", "#8A6A4B"),
    "caramel": ("#C4A574", "#D4B98A"),
    "muted": ("#8A7360", "#C8B8A8"),
    "ink": ("#3B2A1F", "#F3EBE3"),
    "on_espresso": ("#FFF8F1", "#1C1612"),
    "success": ("#3D7A5A", "#6FBF93"),
    "success_hover": ("#2F6248", "#3D7A5A"),
    "danger": ("#B85C4A", "#E08A7A"),
    "danger_hover": ("#944738", "#B85C4A"),
    "ghost": ("#E8D9C8", "#3B2A1F"),
    "ghost_hover": ("#D8C6B4", "#4A3B30"),
    "pill_ok_bg": ("#E4F2EA", "#24382E"),
    "pill_ok_fg": ("#2F6248", "#6FBF93"),
    "pill_off_bg": ("#F6E4DF", "#3A241F"),
    "pill_off_fg": ("#944738", "#E08A7A"),
    "avatar": ("#6F4E37", "#C4A574"),
    "header": ("#5A3D2B", "#2A221C"),
    "gold": ("#C4A574", "#D4B98A"),
}


def load_persian_fonts() -> str:
    global FONT_FAMILY, _FONTS_LOADED
    if _FONTS_LOADED:
        return FONT_FAMILY
    folder = fonts_dir()
    loaded = False
    for name in ("Vazirmatn-Regular.ttf", "Vazirmatn-Bold.ttf"):
        path = folder / name
        if path.exists() and FontManager.load_font(str(path)):
            loaded = True
    FONT_FAMILY = "Vazirmatn" if loaded else "Segoe UI"
    _FONTS_LOADED = True
    return FONT_FAMILY


def app_font(size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def apply_window_icon(window) -> None:
    path = icon_path()
    if not path.exists():
        return
    try:
        window.iconbitmap(str(path))
    except Exception:
        pass


def apply_theme(mode: str | None = None) -> None:
    load_persian_fonts()
    appearance = (mode or "light").lower()
    if appearance not in {"light", "dark", "system"}:
        appearance = "light"
    ctk.set_appearance_mode(appearance)
    ctk.set_default_color_theme(str(theme_path()))


def toggle_appearance(db) -> str:
    current = (db.get_setting("appearance_mode") or "light").lower()
    nxt = "dark" if current != "dark" else "light"
    db.set_setting("appearance_mode", nxt)
    ctk.set_appearance_mode(nxt)
    return nxt


def theme_button_text(db) -> str:
    current = (db.get_setting("appearance_mode") or "light").lower()
    return "تم روشن" if current == "dark" else "تم تیره"


def close_window(window) -> None:
    """Close a window without cancelling other Tk after() jobs in the app."""
    try:
        window.grab_release()
    except Exception:
        pass
    try:
        for job_attr in ("_clock_job", "_status_job", "_focus_job"):
            job = getattr(window, job_attr, None)
            if job:
                window.after_cancel(job)
                setattr(window, job_attr, None)
    except Exception:
        pass
    try:
        window.destroy()
    except Exception:
        pass


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
