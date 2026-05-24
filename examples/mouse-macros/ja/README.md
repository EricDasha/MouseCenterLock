# マウスマクロ例

このフォルダーには、Advanced Settings → Mouse Macros → External JSON file で選択できる JSON 例があります。

## サンプルファイル

- `right-left-left-2-1.json`: 右ボタンを押しながら左クリック → 左クリック、上段数字 `2`、上段数字 `1`。
- `x1-left-copy.json`: `x1` 戻るサイドボタンを押しながら左クリック → `Ctrl+C`。
- `x2-left-paste-enter.json`: `x2` 進むサイドボタンを押しながら左クリック → `Ctrl+V`, `Enter`。
- `middle-right-text.json`: 中ボタンを押しながら右クリック → `GG` 入力、80ms 待機、`Enter`。

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

- `hotkey`, `key`, `mouseClick`, `text`, `delay`
