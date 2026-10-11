# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)
icon_file = root / "assets" / "icon.ico"
datas = [
    (str(root / "gui" / "themes" / "cafe.json"), "gui/themes"),
    (str(root / "assets" / "fonts"), "assets/fonts"),
]
if icon_file.exists():
    datas.append((str(icon_file), "assets"))

a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "customtkinter",
        "jdatetime",
        "PIL",
        "darkdetect",
        "openpyxl",
        "et_xmlfile",
        "app.self_test",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CafeManagement",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_file) if icon_file.exists() else None,
    version=str(root / "installer" / "version_info.txt")
    if (root / "installer" / "version_info.txt").exists()
    else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CafeManagement",
)
