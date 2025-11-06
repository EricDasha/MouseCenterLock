**语言 / Language / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# 鼠标中心锁定

一款 Windows 工具，可在观看视频或游戏多任务时将鼠标光标锁定到屏幕中心。支持全局热键、托盘菜单、简单/高级界面、多语言，以及可配置的重置频率/位置。

## 功能特性
- 全局热键（可自定义）：锁定 / 解锁 / 切换
- 托盘图标和菜单；关闭到托盘；Shift+关闭 退出
- 简单/高级模式
  - 高级：自定义热键、重置间隔、目标位置（虚拟中心、主屏幕中心、自定义）、语言
- 多语言支持：English, 简体中文, 繁體中文, 日本語, 한국어
- 多显示器支持

## 项目结构
- `mouse_center_lock_gui.py` – GUI 应用（PySide6）
- `mouse_center_lock.py` – CLI/基础版本（可选）
- `pythonProject/i18n/` – 语言文件
- `pythonProject/assets/` – 图标和资源（将 `app.ico` 放在此处）
- `config.json` – 默认配置（用户配置会写入到 exe 旁边）
- `pythonProject/create_icon.py` – 从图片生成多尺寸 `.ico` 的辅助工具（Pillow）

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
  mouse_center_lock_gui.py
```
exe 文件将位于 `dist/MouseCenterLock.exe`。

## 自定义图标
将您的多尺寸 `app.ico` 放在 `pythonProject/assets/` 中。应用和托盘将自动使用它。如果不存在，将使用内置矢量图标。

从 PNG/JPG 生成 `app.ico`：
```bash
python pythonProject/create_icon.py <input_image> pythonProject/assets/app.ico
```

## 许可证
MIT

