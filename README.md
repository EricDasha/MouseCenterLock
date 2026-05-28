**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

# MouseControlLayer

MouseControlLayer 是一個 Windows 滑鼠 / 鍵盤控制工具，主要用於滑鼠鎖定、自動點擊與簡單巨集操作

一個想做「把滑鼠鎖在螢幕中心」的小軟體，然後因為實際使用時還需要連點、快捷鍵、視窗規則和一些巨集動作，所以逐漸累積成了現在的專案

適合這些場景：

- 需要把滑鼠固定到螢幕中心或視窗中心
- 需要用熱鍵切換連點狀態
- 需要給滑鼠側鍵、鍵盤按鍵綁定一組簡單動作
- 需要針對不同視窗使用不同規則


## 目錄

- [MouseControlLayer](#mousecontrollayer)
  - [目錄](#目錄)
  - [功能](#功能)
    - [滑鼠鎖定](#滑鼠鎖定)
    - [自動點擊](#自動點擊)
    - [簡單巨集](#簡單巨集)
    - [視窗規則](#視窗規則)
    - [其他功能](#其他功能)
  - [系統需求](#系統需求)
  - [建置（PyInstaller）](#建置pyinstaller)
  - [滑鼠巨集設定](#滑鼠巨集設定)
  - [已知限制](#已知限制)
  - [輸入後端](#輸入後端)
  - [專案結構](#專案結構)
  - [更新日誌](#更新日誌)
  - [授權](#授權)

## 功能

### 滑鼠鎖定

可以把滑鼠鎖定到指定位置，例如：

- 螢幕中心
- 主顯示器中心
- 目前視窗中心
- 自訂位置

適合需要固定滑鼠位置的視窗或遊戲場景

### 自動點擊

支援透過熱鍵啟用 / 停止自動點擊，也可以設定為按住某個按鍵時持續點擊

常見用途包括：

- 長按觸發連點
- 快捷鍵切換連點狀態
- 調整點擊間隔

### 簡單巨集

可以把滑鼠或鍵盤輸入組合成一組動作，例如：

- 點擊滑鼠
- 按下 / 放開鍵盤按鍵
- 延遲指定時間
- 按順序執行一組輸入

巨集功能主要面向簡單、可控的輸入流程，不是複雜腳本引擎

### 視窗規則

可以為不同視窗設定不同規則，讓鎖定、連點或巨集只在指定程式中生效

### 其他功能

- 系統匣執行
- 開機自啟
- 深色 / 淺色主題
- 多語言介面
- 多顯示器支援

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
exe 檔案將位於 `dist/MCL.exe`

打包腳本選項：
- `python build.py` — 完整建置（清理 + 測試 + 打包）
- `python build.py --skip-test` — 跳過單元測試
- `python build.py --dev` — 開發建置（含除錯資訊）
- `python build.py --clean-only` — 僅清理建置產物

如需恢復預設設定，請刪除本機 `Mconfig.json`，程式會回退讀取 `Mconfig.example.json`若程式目錄中仍有舊版 `config.json`，新版本也會相容讀取

## 滑鼠巨集設定

滑鼠巨集支援兩種來源：

- **介面拼裝**：直接在進階頁編輯規則
- **外部 JSON**：載入範例檔或自訂檔案

完整規格、範例檔案、按鍵名稱與動作型別見：

- [滑鼠巨集範例與設定說明](examples/mouse-macros/README.md)

後端階段、fallback 策略與非目標見：[輸入後端路線圖](docs/backend-roadmap.md)

## 已知限制

MouseControlLayer 主要依賴 Windows API / SendInput 實現輸入模擬，不屬於驅動層輸入

因此在以下場景中可能無法正常工作：

- 系統管理員權限視窗
- 使用 Raw Input 的遊戲
- 帶有反作弊保護的遊戲
- 主動過濾模擬輸入的軟體
- 對前台視窗和輸入焦點要求較嚴格的程式

這些限制來自 Windows 輸入機制和目標程式本身，不一定是專案 bug

## 輸入後端

專案目前提供多個輸入後端，用於在不同場景下盡量提高相容性

| 後端 | 狀態 | 說明 |
|---|---|---|
| `native-sendinput` | 預設 | 基於 Rust DLL，優先使用 scan code / Unicode 輸入 |
| `python-sendinput` | 兜底 | Python 實作的 SendInput 路徑，相容性較保守 |
| `window-message` | 相容 | 向前台視窗訊息鏈傳送輸入訊息 |
| `virtual-hid` | 預留 | 為後續虛擬 HID / 驅動輸入預留 |
| `hardware-hid` | 預留 | 為外部硬體輸入模式預留 |

這些後端不能保證繞過遊戲、反作弊或系統權限限制

## 專案結構

- `mouse_center_lock_gui.py` – GUI 應用（PySide6）
- `win_api.py` – Windows API 封裝模組
- `widgets.py` – 自訂 UI 元件（快捷鍵捕獲、進程選擇器）
- `services/` – 執行期服務（連點器、鎖定狀態機、巨集執行鏈）
- `ui/pages/` – 簡單 / 進階頁面建構模組
- `tests/` – 最小單元測試集
- `i18n/` – 語言檔案
- `assets/` – 圖示和資源
- `Mconfig.example.json` – 可提交的預設設定範本；執行時 `Mconfig.json` 僅作本機設定（相容讀取舊版 `config.json`）

## 更新日誌

完整更新記錄見 [CHANGELOG.md](CHANGELOG.md)。

## 授權

[GPL-3.0](LICENSE)
