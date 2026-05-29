**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

# MouseControlLayer

MouseControlLayer は、カーソルロック、自動クリック、簡単なマクロ操作を扱う Windows 向けマウス / キーボード制御ツールです。

最初は「マウスを画面中央に固定する」ための小さなツールでしたが、実際の利用で連打、ホットキー、ウィンドウ別ルール、マクロが必要になり、現在の形になりました。

## 機能

### マウスロック

仮想画面中央、メイン画面中央、現在のウィンドウ中央、またはカスタム位置へカーソルを固定できます。

### 自動クリックとプロファイル

トグル / ホールド式トリガー、クリック間隔、プロセス除外、起動音、複数プロファイルに対応します。「その他」メニューからプロファイルの読み込み、書き出し、削除、全消去ができます。未保存の変更がある状態で切り替えると保存確認が出ます。

### 簡単なマクロ

クリック、キー押下 / 解放、遅延、ホットキー、テキスト入力を順番に実行できます。既定の `F12` 強制停止キーで、実行中またはトグル中のマクロを停止し、押下中の出力を解放できます。

### ウィンドウルール

指定したウィンドウがアクティブな時だけ、ロック、連打、マクロを有効にできます。

## 必要環境

- Windows 10+
- Python 3.9+
- 依存関係：`requirements.txt`

```bash
python -m pip install -r requirements.txt
python mouse_center_lock_gui.py
python -m unittest discover tests
```

## ビルド

```bash
python build.py
```

exe は `dist/MCL.exe` に出力されます。ローカル release zip は `release/` に作られ、zip 内のファイル名は `MouseControlLayer.exe` です。

## マウスマクロ設定

- [マウスマクロ例と設定リファレンス](examples/mouse-macros/ja/README.md)
- [入力バックエンドロードマップ](docs/backend-roadmap.md)

## 既知の制限

主に Windows API / SendInput を使うユーザー層の入力です。管理者権限ウィンドウ、Raw Input ゲーム、アンチチート、シミュレート入力を拒否するアプリでは動作しない場合があります。

## 入力バックエンド

`native-sendinput`、`python-sendinput`、`window-message` を使用できます。`virtual-hid` と `hardware-hid` は将来用の予約です。

## プロジェクト構成

- `mouse_center_lock_gui.py` – GUI アプリ
- `win_api.py` – Windows API ラッパー
- `services/` – 実行時サービス
- `ui/pages/` – ページ構築
- `tests/` – テスト
- `i18n/` – 言語ファイル
- `examples/mouse-macros/` – マクロ例

## 変更履歴

[CHANGELOG.md](CHANGELOG.md)

## ライセンス

[GPL-3.0](LICENSE)
