# 鼠标宏示例

本目录放可直接在「高级设置 → 鼠标宏 → External JSON file」中选择的 JSON 示例。

## 目录

- [示例文件](#示例文件)
- [规则字段](#规则字段)
- [鼠标键名称](#鼠标键名称)
- [键盘 key 名称](#键盘-key-名称)
- [动作类型](#动作类型)

## 示例文件

- `right-left-left-2-1.json`：按住右键，再点左键 → 左键、主键盘 `2`、主键盘 `1`。
- `x1-left-copy.json`：按住 `x1` 返回侧键，再点左键 → `Ctrl+C`。
- `x2-left-paste-enter.json`：按住 `x2` 前进侧键，再点左键 → `Ctrl+V`、`Enter`。
- `middle-right-text.json`：按住中键，再点右键 → 输入 `GG`、等待 80ms、`Enter`。
- `middle-left-test.json`：运行时诊断用；按住中键，再点左键 → 主键盘 `1`。
- `back-left-2-delay-1.json`：按住鼠标后侧键（`back`/`x1`），每次点左键 → 主键盘 `2`、等待 100ms、主键盘 `1`；左键本身由真实点击产生，动作里不再额外点击左键。
- `key-delay-key.json`：按住键盘 `A`，每次按下 `B` → `A`、等待 50ms、`B`；不松开 `A` 时，重复按 `B` 会重复执行。

## 规则字段

```json
{
  "id": "rule-id",
  "name": "规则名称",
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

| 值 | 含义 |
|---|---|
| `hold` | 按住触发键时，按下动作键即可执行一次 |
| `toggle` | 按一次切换 armed，再按动作键执行 |
| `holdLoop` | 按住触发键时，循环执行动作 |
| `toggleLoop` | 按一次切换循环，再按一次停止 |

### 安全终止键

`panicHotkey` 是应用级设置，不属于单条规则。默认是 `F12`；按下后会强制停止正在运行/切换中的宏，并释放已按下的输出。

## 鼠标键名称

| 设置值 | 对应按键 |
|---|---|
| `left` | 鼠标左键 |
| `right` | 鼠标右键 |
| `middle` | 鼠标中键 / 滚轮键 |
| `x1` | 鼠标侧键 1，通常是返回 Back |
| `x2` | 鼠标侧键 2，通常是前进 Forward |

> 不支持写 `back` / `forward`，请写 `x1` / `x2`。

## 键盘 key 名称

- 字母：`A` ~ `Z`
- 主键盘数字：`0` ~ `9`（键盘上排数字，不是数字小键盘）
- 功能键：`F1` ~ `F24`
- 特殊键：`Space`, `Tab`, `Enter`, `Backspace`, `Delete`, `Insert`, `Home`, `End`, `PageUp`, `PageDown`, `Up`, `Down`, `Left`, `Right`

## 动作类型

- `hotkey`：组合键，例如 `{ "type": "hotkey", "modCtrl": true, "key": "C" }`
- `key`：单键，例如 `{ "type": "key", "key": "1" }`
- `keyDown` / `keyUp`：按下 / 松开，适合重叠时序
- `mouseClick`：鼠标点击
- `mouseDown` / `mouseUp`：鼠标按下 / 松开
- `text`：输入文本
- `delay`：等待毫秒，例如 `{ "type": "delay", "ms": 80 }`
