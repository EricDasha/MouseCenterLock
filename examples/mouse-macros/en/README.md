# Mouse Macro Examples

This folder contains JSON examples that can be selected from Advanced Settings → Mouse Macros → External JSON file.

## Example files

- `right-left-left-2-1.json`: hold right button, click left → left click, top-row `2`, top-row `1`.
- `x1-left-copy.json`: hold `x1` Back side button, click left → `Ctrl+C`.
- `x2-left-paste-enter.json`: hold `x2` Forward side button, click left → `Ctrl+V`, `Enter`.
- `middle-right-text.json`: hold middle button, click right → type `GG`, wait 80ms, `Enter`.
- `far-far-west-back-left-combo.json`: hold mouse back side button `x1`, press left → left `mouseDown`, 60ms, `mouseUp`, 120ms, KeyDown `2`, 80ms, KeyDown `1`, 27ms, KeyUp `2`, 66ms, KeyUp `1`; cancel cleanup sends `KeyUp 2/1`. Recommended `cooldownMs=450` to avoid weapon-swap overlap.
- `far-far-west-x1-switch-combo.json`: press mouse back side button `x1` alone → `2`, delay, `1`; no left-click trigger and no simulated firing.
- `key-delay-key.json`: hold keyboard `A`, each `B` press → `A`, wait 50ms, `B`; while `A` stays held, repeated `B` presses repeat the sequence.

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

## Single-input trigger rules

External JSON may use only `pressMouseButton` or `pressKey` without `holdMouseButton` / `holdKey`, meaning the single press fires the rule.

```json
{
  "pressMouseButton": "x1",
  "actions": [
    { "type": "key", "key": "2" }
  ]
}
```

## Keyboard trigger rules

External JSON also supports keyboard hold/press rules:

```json
{
  "holdKey": "A",
  "pressKey": "B",
  "actions": [
    { "type": "key", "key": "A" },
    { "type": "delay", "ms": 50 },
    { "type": "key", "key": "B" }
  ]
}
```

While `A` remains held, each new `B` press runs the action sequence again.

## Action types

- `hotkey`: key combination, e.g. `{ "type": "hotkey", "modCtrl": true, "key": "C" }`.
- `key`: single key, e.g. `{ "type": "key", "key": "1" }`.
- `mouseClick`: mouse click, e.g. `{ "type": "mouseClick", "button": "left" }`.
- `text`: type text, e.g. `{ "type": "text", "text": "GG" }`.
- `delay`: wait milliseconds, e.g. `{ "type": "delay", "ms": 80 }`.
