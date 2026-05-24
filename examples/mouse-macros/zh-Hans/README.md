# 鼠标宏示例

本目录放可直接在「高级设置 → 鼠标宏 → External JSON file」中选择的 JSON 示例。

## 示例文件

- `right-left-left-2-1.json`：按住右键，再点左键 → 左键、主键盘 `2`、主键盘 `1`。
- `x1-left-copy.json`：按住 `x1` 后退侧键，再点左键 → `Ctrl+C`。
- `x2-left-paste-enter.json`：按住 `x2` 前进侧键，再点左键 → `Ctrl+V`、`Enter`。
- `middle-right-text.json`：按住中键，再点右键 → 输入 `GG`、等待 80ms、`Enter`。
- `middle-left-test.json`：运行时诊断用；按住中键，再点左键 → 主键盘 `1`。
- `back-left-2-delay-1.json`：按住鼠标后侧键（`back`/`x1`），每次点左键 → 主键盘 `2`、等待 100ms、主键盘 `1`；左键本身由真实点击产生，动作里不再额外点击左键。
- `far-far-west-back-left-combo.json`：按住鼠标后侧键 `x1`，点左键 → 左键点击、54ms、按下 `2`、80ms、按下 `1`、27ms、松开 `2`、66ms、松开 `1`；取消时自动补 `KeyUp 2/1`。建议 `cooldownMs=450`，避免连续触发撞进切枪冷却。
- `far-far-west-x1-switch-combo.json`：单独按下鼠标后侧键 `x1` → `2`、等待、`1`，不再依赖左键触发，也不模拟左键开火。
- `key-delay-key.json`：按住键盘 `A`，每次按下 `B` → `A`、等待 50ms、`B`；不松开 `A` 时，重复按 `B` 会重复执行。

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

## 单键触发规则

外部 JSON 可只写 `pressMouseButton` 或 `pressKey`，不写 `holdMouseButton` / `holdKey`，表示单独按下该键即触发。

```json
{
  "pressMouseButton": "x1",
  "actions": [
    { "type": "key", "key": "2" }
  ]
}
```

## 键盘触发规则

外部 JSON 也支持键盘按住/触发规则：

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

按住 `A` 不松开时，每次重新按下 `B` 都会重新执行动作序列。

## 动作类型

- `hotkey`：组合键，例如 `{ "type": "hotkey", "modCtrl": true, "key": "C" }`。
- `key`：单键点击，例如 `{ "type": "key", "key": "1" }`。
- `keyDown` / `keyUp`：按下/松开按键，适合需要重叠按住时序的游戏宏，例如 `{ "type": "keyDown", "key": "2" }`。
- `mouseClick`：鼠标点击，例如 `{ "type": "mouseClick", "button": "left" }`。
- `text`：输入文本，例如 `{ "type": "text", "text": "GG" }`。
- `delay`：等待毫秒，例如 `{ "type": "delay", "ms": 80 }`。
