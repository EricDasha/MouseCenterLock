# 鼠标宏示例

本目录放可直接在「高级设置 → 鼠标宏 → External JSON file」中选择的 JSON 示例。

## 示例文件

- `right-left-left-2-1.json`：按住右键，再点左键 → 左键、主键盘 `2`、主键盘 `1`。
- `x1-left-copy.json`：按住 `x1` 后退侧键，再点左键 → `Ctrl+C`。
- `x2-left-paste-enter.json`：按住 `x2` 前进侧键，再点左键 → `Ctrl+V`、`Enter`。
- `middle-right-text.json`：按住中键，再点右键 → 输入 `GG`、等待 80ms、`Enter`。

## 鼠标键名称

| 配置值 | 对应按键 |
|---|---|
| `left` | 鼠标左键 |
| `right` | 鼠标右键 |
| `middle` | 鼠标中键 / 滚轮键 |
| `x1` | 鼠标侧键 1，通常是后退 Back |
| `x2` | 鼠标侧键 2，通常是前进 Forward |

> 不支持写 `back` / `forward`，请写 `x1` / `x2`。

## 键盘 key 名称

- 字母：`A` ~ `Z`
- 主键盘数字：`0` ~ `9`（键盘上排数字，不是小键盘）
- 功能键：`F1` ~ `F24`
- 特殊键：`Space`, `Tab`, `Enter`, `Backspace`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Up`, `Down`, `Left`, `Right`

## 动作类型

- `hotkey`：组合键，例如 `{ "type": "hotkey", "modCtrl": true, "key": "C" }`。
- `key`：单键，例如 `{ "type": "key", "key": "1" }`。
- `mouseClick`：鼠标点击，例如 `{ "type": "mouseClick", "button": "left" }`。
- `text`：输入文本，例如 `{ "type": "text", "text": "GG" }`。
- `delay`：等待毫秒，例如 `{ "type": "delay", "ms": 80 }`。
