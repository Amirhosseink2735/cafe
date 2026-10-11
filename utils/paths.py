"""Resolve source vs PyInstaller-frozen resource and data paths."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from utils.app_info import APP_NAME_EN


def resource_root() -> Path:
    """Bundled assets (themes, fonts) live in _MEIPASS when frozen."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def runtime_root() -> Path:
    """Directory of the executable, or the project root in development."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def user_data_dir() -> Path:
    """Writable customer data folder, outside the install directory when frozen."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        folder = base / APP_NAME_EN
    else:
        folder = runtime_root() / "database"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def fonts_dir() -> Path:
    return resource_root() / "assets" / "fonts"


def theme_path() -> Path:
    return resource_root() / "gui" / "themes" / "cafe.json"


def icon_path() -> Path:
    return resource_root() / "assets" / "icon.ico"


def default_db_path() -> Path:
    target = user_data_dir() / "cafe.db"
    if getattr(sys, "frozen", False) and not target.exists():
        for legacy in (
            runtime_root() / "database" / "cafe.db",
            runtime_root() / "cafe.db",
        ):
            if legacy.exists():
                shutil.copy2(legacy, target)
                break
    return target
