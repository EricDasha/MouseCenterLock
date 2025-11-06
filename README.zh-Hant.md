**语言 / Language / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# 滑鼠中心鎖定

一款 Windows 工具，可在觀看影片或遊戲多工時將滑鼠游標鎖定到螢幕中心。支援全域熱鍵、系統匣選單、簡單/進階介面、多語言，以及可設定的重置頻率/位置。

## 功能特性
- 全域熱鍵（可自訂）：鎖定 / 解鎖 / 切換
- 系統匣圖示和選單；關閉到系統匣；Shift+關閉 退出
- 簡單/進階模式
  - 進階：自訂熱鍵、重置間隔、目標位置（虛擬中心、主螢幕中心、自訂）、語言
- 多語言支援：English, 简体中文, 繁體中文, 日本語, 한국어
- 多顯示器支援

## 專案結構
- `mouse_center_lock_gui.py` – GUI 應用（PySide6）
- `mouse_center_lock.py` – CLI/基礎版本（可選）
- `pythonProject/i18n/` – 語言檔案
- `pythonProject/assets/` – 圖示和資源（將 `app.ico` 放在此處）
- `config.json` – 預設設定（使用者設定會寫入到 exe 旁邊）
- `pythonProject/create_icon.py` – 從圖片產生多尺寸 `.ico` 的輔助工具（Pillow）

## 系統需求
- Windows 10+
- Python 3.9+
- 相依項目：見 `requirements.txt`

安裝相依項目：
```bash
python -m pip install -r requirements.txt
```

執行：
```bash
python mouse_center_lock_gui.py
```

## 建置（PyInstaller）
建立虛擬環境（建議）並建置視窗化 exe：
```bash
pyinstaller --noconfirm --clean --onefile --windowed \
  --name MouseCenterLock \
  --icon pythonProject/assets/app.ico \
  --add-data "pythonProject/i18n;i18n" \
  --add-data "config.json;." \
  --add-data "pythonProject/assets;assets" \
  mouse_center_lock_gui.py
```
exe 檔案將位於 `dist/MouseCenterLock.exe`。

## 自訂圖示
將您的多尺寸 `app.ico` 放在 `pythonProject/assets/` 中。應用程式和系統匣將自動使用它。如果不存在，將使用內建向量圖示。

從 PNG/JPG 產生 `app.ico`：
```bash
python pythonProject/create_icon.py <input_image> pythonProject/assets/app.ico
```

## 授權
MIT

