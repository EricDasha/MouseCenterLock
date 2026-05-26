# 滑鼠巨集範例

本目錄放可直接在「進階設定 → 滑鼠巨集 → External JSON file」中選擇的 JSON 範例。

## 目錄

- [範例檔案](#範例檔案)
- [規則欄位](#規則欄位)
- [滑鼠鍵名稱](#滑鼠鍵名稱)
- [鍵盤 key 名稱](#鍵盤-key-名稱)
- [動作類型](#動作類型)

## 範例檔案

- `right-left-left-2-1.json`：按住右鍵，再點左鍵 → 左鍵、主鍵盤 `2`、主鍵盤 `1`。
- `x1-left-copy.json`：按住 `x1` 返回側鍵，再點左鍵 → `Ctrl+C`。
- `x2-left-paste-enter.json`：按住 `x2` 前進側鍵，再點左鍵 → `Ctrl+V`、`Enter`。
- `middle-right-text.json`：按住中鍵，再點右鍵 → 輸入 `GG`、等待 80ms、`Enter`。
- `middle-left-test.json`：執行期診斷用；按住中鍵，再點左鍵 → 主鍵盤 `1`。
- `back-left-2-delay-1.json`：按住滑鼠後側鍵（`back`/`x1`），每次點左鍵 → 主鍵盤 `2`、等待 100ms、主鍵盤 `1`；左鍵本身由真實點擊產生，動作裡不再額外點擊左鍵。
- `key-delay-key.json`：按住鍵盤 `A`，每次按下 `B` → `A`、等待 50ms、`B`；不鬆開 `A` 時，重複按 `B` 會重複執行。

## 規則欄位

```json
{
  "id": "rule-id",
  "name": "規則名稱",
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

| 值 | 含義 |
|---|---|
| `hold` | 按住觸發鍵時，按下動作鍵即可執行一次 |
| `toggle` | 按一次切換 armed，再按動作鍵執行 |
| `holdLoop` | 按住觸發鍵時，循環執行動作 |
| `toggleLoop` | 按一次切換循環，再按一次停止 |

## 滑鼠鍵名稱

| 設定值 | 對應按鍵 |
|---|---|
| `left` | 滑鼠左鍵 |
| `right` | 滑鼠右鍵 |
| `middle` | 滑鼠中鍵 / 滾輪鍵 |
| `x1` | 滑鼠側鍵 1，通常是返回 Back |
| `x2` | 滑鼠側鍵 2，通常是前進 Forward |

> 不支援寫 `back` / `forward`，請寫 `x1` / `x2`。

## 鍵盤 key 名稱

- 字母：`A` ~ `Z`
- 主鍵盤數字：`0` ~ `9`（鍵盤上排數字，不是數字小鍵盤）
- 功能鍵：`F1` ~ `F24`
- 特殊鍵：`Space`, `Tab`, `Enter`, `Backspace`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Up`, `Down`, `Left`, `Right`

## 動作類型

- `hotkey`：組合鍵，例如 `{ "type": "hotkey", "modCtrl": true, "key": "C" }`
- `key`：單鍵，例如 `{ "type": "key", "key": "1" }`
- `keyDown` / `keyUp`：按下 / 鬆開，適合重疊時序
- `mouseClick`：滑鼠點擊
- `mouseDown` / `mouseUp`：滑鼠按下 / 鬆開
- `text`：輸入文字
- `delay`：等待毫秒，例如 `{ "type": "delay", "ms": 80 }`
