**Language / 语言 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# Mouse Center Lock

A Windows utility that locks the mouse cursor to the screen center while you watch videos or multitask during games. Global hotkeys, tray menu, Simple/Advanced UI, i18n, and configurable recenter frequency/position.

## Features

- Global hotkeys (customizable) for Lock / Unlock / Toggle
- Minecraft-style hotkey capture: click and press key combination directly
- Tray icon and menu; close to tray; Shift+Close to quit
- Simple/Advanced modes
  - Advanced: customize hotkeys, recenter interval, target position (virtual-center, primary-center, custom), language, theme
- Window-specific locking: lock only when target window is active
- Auto lock/unlock on window switch
- Single instance detection: prevents duplicate launches
- Launch on startup
- i18n: English, 简体中文, 繁體中文, 日本語, 한국어
- Light/Dark theme
- Multi-monitor support

## Project Layout

- `mouse_center_lock_gui.py` – GUI app (PySide6)
- `win_api.py` – Windows API wrapper module
- `widgets.py` – Custom UI widgets (hotkey capture, process picker)
- `mouse_center_lock.py` – CLI/basic version (optional)
- `pythonProject/i18n/` – language files
- `pythonProject/assets/` – icons and assets
- `Mconfig.json` – default config (legacy `config.json` is still read for compatibility)

## Requirements

- Windows 10+
- Python 3.9+
- Dependencies: see `requirements.txt`

Install deps:
```bash
python -m pip install -r requirements.txt
```

Run:
```bash
python mouse_center_lock_gui.py
```

## Build (PyInstaller)

Create a virtual environment (recommended) and build a windowed exe:
```bash
pyinstaller --noconfirm --clean --onefile --windowed \
  --name MouseCenterLock \
  --icon pythonProject/assets/app.ico \
  --add-data "pythonProject/i18n;i18n" \
  --add-data "Mconfig.json;." \
  --add-data "pythonProject/assets;assets" \
  --hidden-import win_api \
  --hidden-import widgets \
  mouse_center_lock_gui.py
```
The exe will be in `dist/MouseCenterLock.exe`.

To restore default settings, delete `Mconfig.json`. If an older `config.json` is present in the app directory, the app will still read it as a fallback.

## Changelog

### v1.1.0
- Added clicker profile management with create, switch, save, and delete support for multiple clicker presets.
- Added Windows action notifications, preferring native toast and falling back to tray messages when unavailable.
- Added clicker start sound support with built-in presets, custom audio files, and sound preview.
- Added more clicker trigger modes: toggle, hold keyboard key, and hold mouse button.
- Added middle mouse button support for click execution.
- Migrated the default config file to `Mconfig.json` while keeping backward compatibility for legacy `config.json`.

### v1.0.7
- New: Window-specific locking now has an option "Auto re-lock after leaving and re-entering target window (for manual unlock)", so you can choose between keeping the old behavior or auto re-lock.
- Improved: Simple mode "Current Configuration" now shows clearer status for window-specific locking and the auto re-lock behavior.
- Build: Updated PyInstaller one-file build to produce a single `MouseCenterLock.exe` with icon in the `dist` directory.

### v1.0.6
- Fixed BUG: Shortcuts would still move/lock the cursor in non-target windows when window-specific locking was enabled.
- Improved: Window-specific locking now locks to the center of the target window instead of screen center.
- Debug: Added more debug logs for lock positioning.

### v1.0.5
- New: Ask for action when closing window (Minimize/Quit), with "Don't ask again" option
- Improved: Added option to reset close behavior in settings
- Debug: Added debug logs for window locking logic

### v1.0.4
- Fixed BUG: Manual lock (hotkey) bypasses window restriction when "Window-Specific Locking" is enabled
- Improved: Strict window matching when window-specific locking is active

### v1.0.3
- Minecraft-style hotkey capture: click input and press key combination
- Single instance detection: prevents duplicate launches
- Launch on startup option
- Process picker with search filter
- Hotkey conflict detection and warning
- Code refactored to modular architecture

### v1.0.2
- Added light theme
- Auto lock/unlock on window switch

## License

MIT
