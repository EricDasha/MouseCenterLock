**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

# Mouse Control Layer (MCL)

> 面向 Windows 的滑鼠鎖定、連點、快捷鍵與巨集控制工具。

Mouse Control Layer (MCL) 是一個輕量 Windows 輸入控制層：保留原本的游標鎖定能力，並延伸到連點、滑鼠巨集、全域熱鍵、視窗特定規則、系統匣狀態提示與多輸入後端。倉庫名稱暫保留 `MouseCenterLock`，以避免既有連結失效。

## 目錄

- [功能特性](#功能特性)
- [專案結構](#專案結構)
- [系統需求](#系統需求)
- [滑鼠巨集設定](#滑鼠巨集設定)
- [輸入後端](#輸入後端)
- [更新日誌](#更新日誌)
- [授權](#授權)

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
- `i18n/` – 語言檔案
- `assets/` – 圖示和資源
- `Mconfig.example.json` – 可提交的預設設定範本；執行時 `Mconfig.json` 僅作本機設定（相容讀取舊版 `config.json`）

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
python build.py
```
或使用 PyInstaller 直接建置：
```bash
pyinstaller --noconfirm --clean MCL.spec
```
exe 檔案將位於 `dist/MCL.exe`。

打包腳本選項：
- `python build.py` — 完整建置（清理 + 測試 + 打包）
- `python build.py --skip-test` — 跳過單元測試
- `python build.py --dev` — 開發建置（含除錯資訊）
- `python build.py --clean-only` — 僅清理建置產物

如需恢復預設設定，請刪除本機 `Mconfig.json`，程式會回退讀取 `Mconfig.example.json`。若程式目錄中仍有舊版 `config.json`，新版本也會相容讀取。

## 滑鼠巨集設定

滑鼠巨集支援兩種來源：

- **介面拼裝**：直接在進階頁編輯規則
- **外部 JSON**：載入範例檔或自訂檔案

完整規格、範例檔案、按鍵名稱與動作型別見：

- [滑鼠巨集範例與設定說明](examples/mouse-macros/README.md)

輸入後端預設仍是使用者層：Rust 原生 SendInput（scan code / Unicode）、Python SendInput 兜底與視窗訊息。這能提升多數桌面軟體相容性，但不是 driver/HID 輸入，不能保證所有遊戲、Raw Input 程式、系統管理員權限視窗或反作弊目標都接收。

後端階段、fallback 策略與非目標見：[輸入後端路線圖](docs/backend-roadmap.md)。

## 輸入後端

| 後端 | 狀態 | 用途 |
|---|---|---|
| `native-sendinput` | 預設 | Rust DLL 注入，優先 scan code / Unicode |
| `python-sendinput` | 兜底 | 舊路徑，保守但相容 |
| `window-message` | 兼容 | 傳遞到前台視窗訊息鏈 |
| `virtual-hid` | 預留 | 驅動檢測與後續接入 |
| `hardware-hid` | 預留 | 外部設備模式 |

## 更新日誌

### 開發中 / 最近變更

- 新增 Rust native input backend 與 backend 診斷。
- 滑鼠巨集支援 `keyDown` / `keyUp`、`mouseDown` / `mouseUp`、`cooldownMs`、`triggerMode`。
- 巨集觸發新增 `holdLoop` / `toggleLoop`，並加入內建範例預設與重置。
- 進階頁加入宏預設選擇、外部 JSON 重置與任務欄狀態提示。
- `clicker` 與巨集共用同一條輸入執行鏈，便於後續接入 `virtual-hid`。

### 已發佈版本

### v1.1.0
- 新增連點器方案管理，支援建立、切換、儲存與刪除多組連點設定。
- 新增 Windows 通知播報，優先使用原生 toast，失敗時回退到系統匣提示。
- 新增連點器啟動音效，支援內建預設、自訂音訊檔案與音效試聽。
- 新增多種連點觸發方式，支援切換啟動、按住鍵盤按鍵啟動、按住滑鼠按鍵啟動。
- 連點按鍵新增支援滑鼠中鍵。
- 預設設定檔改為 `Mconfig.json`，並相容讀取舊版 `config.json`。

### v1.0.7
- 新功能：視窗特定鎖定新增「手動解鎖後，切換回目標視窗時重新自動鎖定」選項，可在保留原有行為與自動重鎖之間自由切換。
- 改善：簡單模式「目前配置」中增加視窗特定鎖定與自動重鎖狀態的視覺化提示。
- 建置：更新 PyInstaller 單檔打包流程，產生附帶圖示的 `MCL.exe`（位於 dist 目錄）。

### v1.0.6
- 修復 BUG：在啟用特定窗口鎖定時，在非目標窗口使用快捷鍵仍會導致鼠標移動/鎖定的問題。
- 優化：特定視窗鎖定現在會將滑鼠鎖定到目標視窗的中心，而非螢幕中心。
- 改進：添加了更多關於鎖定位置的調試日誌。

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
