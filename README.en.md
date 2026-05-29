**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

# MouseControlLayer

MouseControlLayer is a Windows mouse / keyboard control utility for cursor locking, auto clicking, and simple macro actions.

It started as a small tool for locking the cursor near the screen center, then grew into a practical control layer with click automation, hotkeys, window rules, and macro presets.

Good for:

- locking the cursor to the screen or window center
- toggling auto clicker states with hotkeys
- binding simple action sequences to mouse side buttons or keyboard keys
- applying behavior only to selected windows

## Features

### Mouse locking

Lock the cursor to the virtual screen center, primary display center, current window center, or a custom position.

### Auto clicker profiles

Supports toggle/hold triggers, click interval, process blacklist, startup sound, and multiple profiles. The **More** menu can import, export, delete, or clear saved profiles. If a profile has unsaved edits, switching profiles asks whether to save them.

### Simple macros

Build ordered input sequences: mouse clicks, key down/up, delays, hotkeys, and text. Macros include a default `F12` panic stop key to force-stop running/toggled actions and release held outputs.

### Window rules

Apply locking, clicker, or macro behavior only when matching windows are active.

### Other features

- system tray operation
- launch on startup
- dark / light theme
- multilingual UI
- multi-monitor support

## Requirements

- Windows 10+
- Python 3.9+
- Dependencies: `requirements.txt`

```bash
python -m pip install -r requirements.txt
python mouse_center_lock_gui.py
python -m unittest discover tests
```

## Build (PyInstaller)

```bash
python build.py
```

The exe is created at `dist/MCL.exe`. Local release archives are created under `release/`, with `MouseControlLayer.exe` inside the zip.

Common options:

- `python build.py` — full build: clean + tests + package + release zip
- `python build.py --skip-test` — skip unit tests
- `python build.py --no-archive` — skip local release zip
- `python build.py --dev` — development build
- `python build.py --clean-only` — clean only

## Mouse macro configuration

Mouse macros support both the UI builder and external JSON files.

- [Mouse macro examples and configuration reference](examples/mouse-macros/en/README.md)
- [Input Backend Roadmap](docs/backend-roadmap.md)

## Known limitations

MouseControlLayer mainly uses Windows API / SendInput. It is not driver-level input. Elevated windows, Raw Input games, anti-cheat protected games, or apps that filter simulated input may not work.

## Input backends

| Backend | Status | Notes |
|---|---|---|
| `native-sendinput` | default | Rust DLL backend, scan-code / Unicode first |
| `python-sendinput` | fallback | Python SendInput path |
| `window-message` | compatible | sends messages to the foreground window chain |
| `virtual-hid` | reserved | placeholder for future virtual HID / driver path |
| `hardware-hid` | reserved | placeholder for external hardware mode |

## Project layout

- `mouse_center_lock_gui.py` – GUI app (PySide6)
- `win_api.py` – Windows API wrapper
- `widgets.py` – custom UI widgets
- `services/` – runtime services
- `ui/pages/` – Simple / Advanced page builders
- `tests/` – unit tests
- `i18n/` – language files
- `examples/mouse-macros/` – macro examples
- `Mconfig.example.json` – default template; runtime `Mconfig.json` is local-only

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

[GPL-3.0](LICENSE)
