# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['mouse_center_lock_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('pythonProject/i18n', 'i18n'), ('config.json', '.'), ('pythonProject/assets', 'assets')],
    hiddenimports=['win_api', 'widgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MouseCenterLock',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['pythonProject\\assets\\app.ico'],
)
