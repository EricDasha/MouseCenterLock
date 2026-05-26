# Mouse macro examples / 鼠标宏示例

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

## Example map

| File | Use case |
|---|---|
| `right-left-left-2-1.json` | simple mouse hold + click combo |
| `x1-left-copy.json` | side button + click to copy |
| `x2-left-paste-enter.json` | side button + click to paste |
| `middle-right-text.json` | text macro |
| `key-delay-key.json` | keyboard hold + repeatable trigger |

Each language folder contains the same JSON examples plus localized notes.
