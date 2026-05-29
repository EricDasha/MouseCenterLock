**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

# MouseControlLayer

MouseControlLayer 是一個 Windows 滑鼠 / 鍵盤控制工具，主要用於滑鼠鎖定、自動點擊與簡單巨集操作。

它最開始只是想做一個「把滑鼠鎖在螢幕中心」的小工具。後來因為實際使用裡還需要連點、快捷鍵、視窗規則和一些巨集動作，所以逐漸整理成現在這個專案。

適合這些場景：

- 需要把滑鼠固定到螢幕中心或視窗中心
- 需要用熱鍵切換連點狀態
- 需要給滑鼠側鍵、鍵盤按鍵綁定一組簡單動作
- 需要針對不同視窗使用不同規則

## 功能

### 滑鼠鎖定

可以把滑鼠鎖定到螢幕中心、主顯示器中心、目前視窗中心或自訂位置。

### 自動點擊與方案

支援熱鍵切換、按住觸發、點擊間隔、黑名單進程、啟動音效與多方案。方案可在「更多」中匯入、匯出、刪除或清空；切換方案前若有未儲存變更，會詢問是否儲存。

### 簡單巨集

可以把滑鼠或鍵盤輸入組合成一組動作，例如點擊、按下 / 放開按鍵、延遲與文字輸入。巨集提供預設 F12 的強制終止鍵，用於停止失控的動作序列。

### 視窗規則

可以為不同視窗設定不同規則，讓鎖定、連點或巨集只在指定程式中生效。

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

```bash
python -m pip install -r requirements.txt
python mouse_center_lock_gui.py
python -m unittest discover tests
```

## 建置（PyInstaller）

```bash
python build.py
```

exe 位於 `dist/MouseControlLayer.exe`；本地 release 壓縮包位於 `release/`，壓縮包內檔名固定為 `MouseControlLayer.exe`。

常用選項：

- `python build.py` — 完整建置（清理 + 測試 + 打包 + release zip）
- `python build.py --skip-test` — 跳過單元測試
- `python build.py --no-archive` — 不產生本地 release zip
- `python build.py --dev` — 開發建置
- `python build.py --clean-only` — 僅清理建置產物

## 滑鼠巨集設定

滑鼠巨集支援「介面拼裝」和「外部 JSON 設定檔」兩種方式。

- [滑鼠巨集範例與設定說明](examples/mouse-macros/zh-Hant/README.md)
- [輸入後端路線圖](docs/backend-roadmap.md)

## 已知限制

MouseControlLayer 主要依賴 Windows API / SendInput 實現輸入模擬，不屬於驅動層輸入。管理員權限視窗、Raw Input 遊戲、反作弊保護或主動過濾模擬輸入的軟體可能無法正常工作。

## 輸入後端

| 後端 | 狀態 | 說明 |
|---|---|---|
| `native-sendinput` | 預設 | 基於 Rust DLL，優先使用 scan code / Unicode 輸入 |
| `python-sendinput` | 兜底 | Python 實作的 SendInput 路徑 |
| `window-message` | 相容 | 向前台視窗訊息鏈傳送輸入訊息 |
| `virtual-hid` | 預留 | 為後續虛擬 HID / 驅動輸入預留 |
| `hardware-hid` | 預留 | 為外部硬體輸入模式預留 |

## 專案結構

- `mouse_center_lock_gui.py` – GUI 應用（PySide6）
- `win_api.py` – Windows API 封裝模組
- `widgets.py` – 自訂 UI 元件
- `services/` – 執行期服務
- `ui/pages/` – 簡單 / 進階頁面
- `tests/` – 單元測試
- `i18n/` – 語言檔案
- `examples/mouse-macros/` – 巨集範例
- `Mconfig.example.json` – 預設設定範本；`Mconfig.json` 僅作本機設定

## 更新日誌

完整更新記錄見 [CHANGELOG.md](CHANGELOG.md)。

## 授權

[GPL-3.0](LICENSE)
