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
- `config.json` – default config

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
  --add-data "config.json;." \
  --add-data "pythonProject/assets;assets" \
  --hidden-import win_api \
  --hidden-import widgets \
  mouse_center_lock_gui.py
```
The exe will be in `dist/MouseCenterLock.exe`.

## Changelog

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
