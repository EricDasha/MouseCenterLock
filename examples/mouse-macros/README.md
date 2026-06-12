# Mouse macro examples / 宏示例

Choose your language:

- [简体中文](zh-Hans/README.md)
- [繁體中文](zh-Hant/README.md)
- [English](en/README.md)
- [日本語](ja/README.md)
- [한국어](ko/README.md)

## What this folder contains

- copy-pasteable JSON presets
- trigger rules for mouse/keyboard combos
- action syntax for click, hold, delay, and text
- notes on the mouse button names used by the app

## Common rules

- `holdMouseButton` / `holdKey`: required hold side
- `pressMouseButton` / `pressKey`: trigger side
- `triggerMode`: `hold`, `toggle`, `holdLoop`, `toggleLoop`
- `actions`: ordered action list
- `onCancel`: cleanup actions when interrupted
- `cooldownMs`: minimum delay before the same rule can fire again
- `loopIntervalMs`: repeat interval for loop modes
- `loopWhilePressHeld`: for loop modes, only fire while `pressMouseButton` / `pressKey` is held
- `toggleOnKey` / `toggleOnMouseButton`: optional one-way arm input for `toggle` / `toggleLoop`
- `toggleOffKey` / `toggleOffMouseButton`: optional one-way stop input for `toggle` / `toggleLoop`; when omitted, the on/hold input keeps legacy same-key toggle behavior
- `mouseClick.holdMs`: keep the mouse button down before release for compatibility
- `repeat`: repeat a nested action list
- `mouseMove` / `mouseMoveRelative` / `mouseScroll`: cursor and wheel actions
- App-level `panicHotkey`: default `F12`; force-stops running/toggled macros and releases held outputs.

## Example map

| File | Use case |
|---|---|
| `right-left-left-2-1.json` | simple mouse hold + click combo |
| `x1-left-copy.json` | side button + click to copy |
| `x2-left-paste-enter.json` | side button + click to paste |
| `middle-right-text.json` | text macro |
| `key-delay-key.json` | keyboard hold + repeatable trigger |
| `repeat-r-on-1-off-2.json` | press `1` to press `R` every 100ms, press `2` to stop |
| `left-hold-repeat-r-on-1-off-2.json` | press `1` to arm, hold left mouse to press `R` every 100ms, press `2` to stop |

Each language folder contains the same JSON examples plus localized notes.
