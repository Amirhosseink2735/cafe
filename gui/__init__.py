"""Desktop GUI package (CustomTkinter)."""

from gui.admin_window import AdminWindow
from gui.kiosk_window import KioskWindow
from gui.login_window import LoginWindow
from gui.role_window import RoleWindow
from gui.style import apply_theme

__all__ = ["AdminWindow", "KioskWindow", "LoginWindow", "RoleWindow", "apply_theme"]
