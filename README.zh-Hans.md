**语言 / Language / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# 鼠标中心锁定

一款 Windows 工具，可在观看视频或游戏多任务时将鼠标光标锁定到屏幕中心。支持全局热键、托盘菜单、简单/高级界面、多语言，以及可配置的重置频率/位置。

## 功能特性

- 全局热键（可自定义）：锁定 / 解锁 / 切换
- Minecraft 风格快捷键设置：点击后直接按下按键组合
- 托盘图标和菜单；关闭到托盘；Shift+关闭 退出
- 简单/高级模式
  - 高级：自定义热键、重置间隔、目标位置（虚拟中心、主屏幕中心、自定义）、语言、主题
- 窗口特定锁定：仅在指定窗口激活时锁定
- 窗口切换自动锁定/解锁
- 单实例检测：防止重复打开程序
- 开机自启动
- 多语言支持：English, 简体中文, 繁體中文, 日本語, 한국어
- 浅色/深色主题
- 多显示器支持

## 项目结构

- `mouse_center_lock_gui.py` – GUI 应用（PySide6）
- `win_api.py` – Windows API 封装模块
- `widgets.py` – 自定义 UI 组件（快捷键捕获、进程选择器）
- `mouse_center_lock.py` – CLI/基础版本（可选）
- `pythonProject/i18n/` – 语言文件
- `pythonProject/assets/` – 图标和资源
- `config.json` – 默认配置

## 系统要求

- Windows 10+
- Python 3.9+
- 依赖项：见 `requirements.txt`

安装依赖：
```bash
python -m pip install -r requirements.txt
```

运行：
```bash
python mouse_center_lock_gui.py
```

## 构建（PyInstaller）

创建虚拟环境（推荐）并构建窗口化 exe：
```bash
pyinstaller --noconfirm --clean --onefile --windowed \
  --name MouseCenterLock \
  --icon pythonProject/assets/app.ico \
  --add-data "pythonProject/i18n;i18n" \
  --add-data "config.json;." \
  --add-data "pythonProject/assets;assets" \
  --hidden-import win_api \
  --hidden-import widgets \
  mouse_center_lock_gui.py
```
exe 文件将位于 `dist/MouseCenterLock.exe`。

## 更新日志

### v1.0.6
- 修复 BUG：在启用特定窗口锁定时，在非目标窗口使用快捷键仍会导致鼠标移动/锁定的问题。
- 优化：特定窗口锁定现在会将鼠标锁定到目标窗口的中心，而非屏幕中心。
- 改进：添加了更多关于锁定位置的调试日志。

### v1.0.5
- 新功能：关闭窗口时询问操作（最小化/退出），支持“不再询问”
- 改善：设置界面增加重置关闭行为的选项
- 调试：新增特定窗口锁定逻辑的调试日志

### v1.0.4
- 修复 BUG：启用特定窗口锁定时，手动锁定（快捷键）会导致锁定范围失效（锁到所有窗口）的问题
- 优化：启用特定窗口锁定时，严格限制锁定范围

### v1.0.3
- Minecraft 风格快捷键设置：点击输入框后直接按下按键组合
- 单实例检测：防止重复打开程序
- 开机自启动功能
- 进程选择器新增搜索过滤
- 快捷键冲突检测与提示
- 代码重构为模块化架构

### v1.0.2
- 新增浅色主题
- 窗口切换自动锁定/解锁功能

## 许可证

MIT
