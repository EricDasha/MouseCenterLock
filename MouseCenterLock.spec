# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['mouse_center_lock_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('i18n', 'i18n'), ('Mconfig.example.json', '.'), ('assets', 'assets'), ('native', 'native')],
    hiddenimports=['win_api', 'widgets', 'app_logging', 'app_paths', 'app_runtime', 'i18n_manager', 'settings_manager', 'services.action_scheduler', 'services.clicker_service', 'services.clicker_profile_controller', 'services.input_backends', 'services.input_service', 'services.native_input', 'services.lock_service', 'services.settings_apply_controller', 'services.theme_service', 'services.tray_service', 'ui.main_window', 'ui.pages.common', 'ui.pages.simple_page', 'ui.pages.advanced_page', 'ui.forms.clicker_profile_form', 'ui.forms.settings_form', 'ui.presenters.main_window_presenter', 'ui.presenters.tray_presenter'],
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
    icon=['assets\\app.ico'],
)
