# Mouse Macro Examples

This folder contains JSON examples that can be selected from Advanced Settings → Mouse Macros → External JSON file.

## Example files

- `right-left-left-2-1.json`: hold right button, click left → left click, top-row `2`, top-row `1`.
- `x1-left-copy.json`: hold `x1` Back side button, click left → `Ctrl+C`.
- `x2-left-paste-enter.json`: hold `x2` Forward side button, click left → `Ctrl+V`, `Enter`.
- `middle-right-text.json`: hold middle button, click right → type `GG`, wait 80ms, `Enter`.

## Mouse button names

| Config value | Physical button |
|---|---|
| `left` | Left mouse button |
| `right` | Right mouse button |
| `middle` | Middle / wheel button |
| `x1` | Side button 1, usually Back |
| `x2` | Side button 2, usually Forward |

> `back` / `forward` are not valid config values. Use `x1` / `x2`.

## Keyboard `key` names

- Letters: `A` ~ `Z`
- Top-row numbers: `0` ~ `9` (not numpad keys)
- Function keys: `F1` ~ `F24`
- Special keys: `Space`, `Tab`, `Enter`, `Backspace`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Up`, `Down`, `Left`, `Right`

## Action types

- `hotkey`: key combination, e.g. `{ "type": "hotkey", "modCtrl": true, "key": "C" }`.
- `key`: single key, e.g. `{ "type": "key", "key": "1" }`.
- `mouseClick`: mouse click, e.g. `{ "type": "mouseClick", "button": "left" }`.
- `text`: type text, e.g. `{ "type": "text", "text": "GG" }`.
- `delay`: wait milliseconds, e.g. `{ "type": "delay", "ms": 80 }`.
