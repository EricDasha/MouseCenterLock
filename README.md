**语言 / Language / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [한국어](README.ko.md)

---

# 滑鼠中心鎖定

一款 Windows 工具，可在觀看影片或遊戲多工時將滑鼠游標鎖定到螢幕中心。支援全域熱鍵、系統匣選單、簡單/進階介面、多語言，以及可設定的重置頻率/位置。

## 功能特性

- 全域熱鍵（可自訂）：鎖定 / 解鎖 / 切換
- Minecraft 風格快捷鍵設定：點擊後直接按下按鍵組合
- 系統匣圖示和選單；關閉到系統匣；Shift+關閉 退出
- 簡單/進階模式
  - 進階：自訂熱鍵、重置間隔、目標位置（虛擬中心、主螢幕中心、自訂）、語言、主題
- 視窗特定鎖定：僅在指定視窗啟用時鎖定
- 視窗切換自動鎖定/解鎖
- 單實例檢測：防止重複開啟程式
- 開機自啟動
- 多語言支援：English, 简体中文, 繁體中文, 日本語, 한국어
- 淺色/深色主題
- 多顯示器支援

## 專案結構

- `mouse_center_lock_gui.py` – GUI 應用（PySide6）
- `win_api.py` – Windows API 封裝模組
- `widgets.py` – 自訂 UI 元件（快捷鍵捕獲、進程選擇器）
- `mouse_center_lock.py` – CLI/基礎版本（可選）
- `pythonProject/i18n/` – 語言檔案
- `pythonProject/assets/` – 圖示和資源
- `config.json` – 預設設定

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
  --hidden-import win_api \
  --hidden-import widgets \
  mouse_center_lock_gui.py
```
exe 檔案將位於 `dist/MouseCenterLock.exe`。

## 更新日誌

### v1.0.5
- 新功能：關閉視窗時詢問操作（最小化/退出），支持「不再詢問」
- 改善：設定介面增加重設關閉行為的選項
- 調試：新增特定視窗鎖定邏輯的調試日誌

### v1.0.4
- 修復 BUG：啟用特定視窗鎖定時，手動鎖定（快捷鍵）會導致鎖定範圍失效（鎖到所有視窗）的問題
- 優化：啟用特定視窗鎖定時，嚴格限制鎖定範圍

### v1.0.3
- Minecraft 風格快捷鍵設定：點擊輸入框後直接按下按鍵組合
- 單實例檢測：防止重複開啟程式
- 開機自啟動功能
- 進程選擇器新增搜索過濾
- 快捷鍵衝突檢測與提示
- 代碼重構為模組化架構

### v1.0.2
- 新增淺色主題
- 視窗切換自動鎖定/解鎖功能

## 授權

MIT
