# 滑鼠巨集範例

本目錄放可直接在「進階設定 → 滑鼠巨集 → External JSON file」中選擇的 JSON 範例。

## 範例檔案

- `right-left-left-2-1.json`：按住右鍵，再點左鍵 → 左鍵、主鍵盤 `2`、主鍵盤 `1`。
- `x1-left-copy.json`：按住 `x1` 返回側鍵，再點左鍵 → `Ctrl+C`。
- `x2-left-paste-enter.json`：按住 `x2` 前進側鍵，再點左鍵 → `Ctrl+V`、`Enter`。
- `middle-right-text.json`：按住中鍵，再點右鍵 → 輸入 `GG`、等待 80ms、`Enter`。
- `key-delay-key.json`：按住鍵盤 `A`，每次按下 `B` → `A`、等待 50ms、`B`；不放開 `A` 時，重複按 `B` 會重複執行。

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

## 鍵盤觸發規則

外部 JSON 也支援鍵盤按住/觸發規則：

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

按住 `A` 不放開時，每次重新按下 `B` 都會重新執行動作序列。

## 動作類型

- `hotkey`：組合鍵。
- `key`：單鍵。
- `mouseClick`：滑鼠點擊。
- `text`：輸入文字。
- `delay`：等待毫秒。
