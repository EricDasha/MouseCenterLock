# Mouse Macro Examples

This folder contains JSON presets that can be selected from Advanced Settings → Mouse Macros → External JSON file.

## Contents

- [Example files](#example-files)
- [Rule fields](#rule-fields)
- [Mouse button names](#mouse-button-names)
- [Keyboard `key` names](#keyboard-key-names)
- [Action types](#action-types)

## Example files

- `right-left-left-2-1.json`: hold right button, click left → left click, top-row `2`, top-row `1`.
- `x1-left-copy.json`: hold `x1` Back side button, click left → `Ctrl+C`.
- `x2-left-paste-enter.json`: hold `x2` Forward side button, click left → `Ctrl+V`, `Enter`.
- `middle-right-text.json`: hold middle button, click right → type `GG`, wait 80ms, `Enter`.
- `middle-left-test.json`: runtime diagnostics; hold middle button, click left → top-row `1`.
- `back-left-2-delay-1.json`: hold mouse Back side button (`back` / `x1`), each left click → top-row `2`, wait 100ms, top-row `1`; the real left click is passed through, so the action list does not click left again.
- `key-delay-key.json`: hold keyboard `A`, each `B` press → `A`, wait 50ms, `B`; while `A` remains held, repeated `B` presses repeat the sequence.

## Rule fields

```json
{
  "id": "rule-id",
  "name": "Rule name",
  "enabled": true,
  "triggerMode": "hold",
  "holdMouseButton": "x1",
  "pressMouseButton": "left",
  "actions": [],
  "onCancel": [],
  "cooldownMs": 0,
  "loopIntervalMs": 1
}
```

### `triggerMode`

| Value | Meaning |
|---|---|
| `hold` | While the hold key is pressed, one press of the trigger key runs once |
| `toggle` | Press once to arm, then use the trigger key to fire |
| `holdLoop` | While the hold key is pressed, repeat the action list |
| `toggleLoop` | Press once to start looping, press again to stop |

### Safety stop

`panicHotkey` is app-level, not per-rule. The default is `F12`; pressing it force-stops running/toggled macros and releases held outputs.

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

- `hotkey`: key combination, e.g. `{ "type": "hotkey", "modCtrl": true, "key": "C" }`
- `key`: single key, e.g. `{ "type": "key", "key": "1" }`
- `keyDown` / `keyUp`: press / release, useful for overlapping timings
- `mouseClick`: mouse click
- `mouseDown` / `mouseUp`: mouse press / release
- `text`: type text
- `delay`: wait milliseconds, e.g. `{ "type": "delay", "ms": 80 }`
