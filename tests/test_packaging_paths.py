"""Frozen-resource and Windows path handling (spaces, AppData)."""

from __future__ import annotations

import sys
from pathlib import Path

from utils import paths
from utils.app_info import APP_NAME_EN


def test_dev_db_lives_under_project_database() -> None:
    db_path = paths.default_db_path()
    assert db_path.name == "cafe.db"
    assert db_path.parent.name == "database"


def test_frozen_paths_use_meipass_and_localappdata(monkeypatch, tmp_path: Path) -> None:
    meipass = tmp_path / "Program Files" / "CafeManagement" / "_internal"
    (meipass / "assets" / "fonts").mkdir(parents=True)
    (meipass / "gui" / "themes").mkdir(parents=True)
    exe_dir = tmp_path / "Program Files" / "CafeManagement"
    exe_dir.mkdir(parents=True, exist_ok=True)
    local = tmp_path / "Users" / "Arad Shop" / "AppData" / "Local"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "CafeManagement.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    assert paths.resource_root() == meipass
    assert paths.runtime_root() == exe_dir
    assert paths.fonts_dir() == meipass / "assets" / "fonts"
    assert " " in str(paths.fonts_dir())
    data = paths.user_data_dir()
    assert data == local / APP_NAME_EN
    assert data.exists()
    db_path = paths.default_db_path()
    assert db_path == data / "cafe.db"


def test_frozen_copies_legacy_db_once(monkeypatch, tmp_path: Path) -> None:
    meipass = tmp_path / "bundle"
    meipass.mkdir()
    exe_dir = tmp_path / "installed app"
    (exe_dir / "database").mkdir(parents=True)
    legacy = exe_dir / "database" / "cafe.db"
    legacy.write_bytes(b"legacy-sqlite")
    local = tmp_path / "Local App"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_dir / "CafeManagement.exe"))
    monkeypatch.setenv("LOCALAPPDATA", str(local))

    first = paths.default_db_path()
    assert first.read_bytes() == b"legacy-sqlite"
    first.write_bytes(b"updated")
    second = paths.default_db_path()
    assert second.read_bytes() == b"updated"
