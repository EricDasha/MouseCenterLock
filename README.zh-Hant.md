**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

> 注意：此翻譯可能會落後於中文與英文 README 的更新進度。如需最新資訊，建議優先查看 [README.md](README.md)、[简体中文](README.zh-Hans.md) 或 [English](README.en.md)。

# MCL 滑鼠控制層

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
- `services/` – 執行期服務（連點器、鎖定狀態機）
- `ui/pages/` – 簡單/進階頁面建構模組
- `tests/` – 最小單元測試集
- `pythonProject/i18n/` – 語言檔案
- `pythonProject/assets/` – 圖示和資源
- `Mconfig.json` – 預設設定（相容讀取舊版 `config.json`）

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

測試：
```bash
python -m unittest discover tests
```

## 建置（PyInstaller）

建立虛擬環境（建議）並建置視窗化 exe：
```bash
pyinstaller --noconfirm --clean --onefile --windowed \
  --name MCL \
  --icon pythonProject/assets/app.ico \
  --add-data "pythonProject/i18n;i18n" \
  --add-data "Mconfig.json;." \
  --add-data "pythonProject/assets;assets" \
  --hidden-import win_api \
  --hidden-import widgets \
  mouse_center_lock_gui.py
```
exe 檔案將位於 `dist/MCL.exe`。

如需恢復預設設定，請刪除 `Mconfig.json`。若程式目錄中仍有舊版 `config.json`，新版本也會相容讀取。

## 滑鼠巨集設定

滑鼠巨集支援「介面拼裝」和「外部 JSON 設定檔」兩種方式。完整寫法、範例檔案、滑鼠鍵名與鍵盤 `key` 名稱見：

- [滑鼠巨集範例與設定說明](examples/mouse-macros/zh-Hant/README.md)

## 更新日誌

完整更新記錄見 [CHANGELOG.md](CHANGELOG.md)。

## 授權

[GPL-3.0](LICENSE)
