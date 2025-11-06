**Language / 语言 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# Mouse Center Lock

A Windows utility that locks the mouse cursor to the screen center while you watch videos or multitask during games. Global hotkeys, tray menu, Simple/Advanced UI, i18n, and configurable recenter frequency/position.

## Features
- Global hotkeys (customizable) for Lock / Unlock / Toggle
- Tray icon and menu; close to tray; Shift+Close to quit
- Simple/Advanced modes
  - Advanced: customize hotkeys, recenter interval, target position (virtual-center, primary-center, custom), language
- i18n: English, 简体中文, 繁體中文, 日本語, 한국어
- Multi-monitor support

## Project Layout
- `mouse_center_lock_gui.py` – GUI app (PySide6)
- `mouse_center_lock.py` – CLI/basic version (optional)
- `pythonProject/i18n/` – language files
- `pythonProject/assets/` – icons and assets (put `app.ico` here)
- `config.json` – default config (user override is written next to the exe)
- `pythonProject/create_icon.py` – helper to build multi-size `.ico` from an image (Pillow)

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
  mouse_center_lock_gui.py
```
The exe will be in `dist/MouseCenterLock.exe`.

## Custom Icon
Place your multi-size `app.ico` in `pythonProject/assets/`. The app and tray will use it automatically. If absent, a built-in vector icon is used.

To generate `app.ico` from a PNG/JPG:
```bash
python pythonProject/create_icon.py <input_image> pythonProject/assets/app.ico
```

## License
MIT

