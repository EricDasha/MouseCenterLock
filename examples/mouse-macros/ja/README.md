# マウスマクロ例

このフォルダーには、Advanced Settings → Mouse Macros → External JSON file で選択できる JSON 例があります。

## 目次

- [サンプルファイル](#サンプルファイル)
- [ルール項目](#ルール項目)
- [マウスボタン名](#マウスボタン名)
- [キーボード `key` 名](#キーボード-key-名)
- [アクションタイプ](#アクションタイプ)

## サンプルファイル

- `right-left-left-2-1.json`: 右ボタンを押しながら左クリック → 左クリック、上段数字 `2`、上段数字 `1`。
- `x1-left-copy.json`: `x1` 戻るサイドボタンを押しながら左クリック → `Ctrl+C`。
- `x2-left-paste-enter.json`: `x2` 進むサイドボタンを押しながら左クリック → `Ctrl+V`, `Enter`。
- `middle-right-text.json`: 中ボタンを押しながら右クリック → `GG` 入力、80ms 待機、`Enter`。
- `middle-left-test.json`: 実行時診断用。中ボタンを押しながら左クリック → 上段数字 `1`。
- `back-left-2-delay-1.json`: `back` / `x1` を押しながら左クリック → `2`、100ms、`1`。左クリック自体は実クリックを通す。
- `key-delay-key.json`: `A` を押しながら `B` を押すたびに → `A`、50ms、`B`。

## ルール項目

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

| 値 | 意味 |
|---|---|
| `hold` | 押し続けている間に、トリガー押下で 1 回実行 |
| `toggle` | 1 回押して armed、以後トリガーで実行 |
| `holdLoop` | 押し続けている間、動作列を繰り返す |
| `toggleLoop` | 1 回押してループ開始、もう 1 回で停止 |

### Safety stop

`panicHotkey` はアプリ全体の設定です。既定は `F12`。実行中/トグル中のマクロを強制停止し、押下中の出力を解放します。

## マウスボタン名

| 設定値 | 物理ボタン |
|---|---|
| `left` | 左ボタン |
| `right` | 右ボタン |
| `middle` | 中 / ホイールボタン |
| `x1` | サイドボタン 1、通常 Back |
| `x2` | サイドボタン 2、通常 Forward |

> `back` / `forward` は無効です。`x1` / `x2` を使ってください。

## キーボード `key` 名

- 英字: `A` ~ `Z`
- 上段数字: `0` ~ `9`（テンキーではありません）
- ファンクションキー: `F1` ~ `F24`
- 特殊キー: `Space`, `Tab`, `Enter`, `Backspace`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Up`, `Down`, `Left`, `Right`

## アクションタイプ

- `hotkey`
- `key`
- `keyDown` / `keyUp`
- `mouseClick`
- `mouseDown` / `mouseUp`
- `text`
- `delay`
