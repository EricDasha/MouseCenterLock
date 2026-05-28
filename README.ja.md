**语言 / Language / 日本語 / 언어**: [简体中文](README.zh-Hans.md) | [繁體中文](README.zh-Hant.md) | [English](README.en.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

---

> 注記: この翻訳は中国語版と英語版 README より更新が遅れる場合があります。最新情報が必要な場合は、[简体中文](README.zh-Hans.md) または [English](README.en.md) を確認してください。

# マウスセンターロック

動画視聴やゲーム中のマルチタスク時に、マウスカーソルを画面中央へ固定する Windows ツールです。グローバルホットキー、トレイメニュー、シンプル/詳細 UI、多言語、リセンター間隔/位置の設定に対応しています。

## 機能

- グローバルホットキー（カスタマイズ可能）：ロック / アンロック / 切り替え
- Minecraft 風ホットキー設定：入力欄をクリックしてキー組み合わせを直接押す
- トレイアイコンとメニュー、閉じるとトレイへ、Shift+閉じるで終了
- シンプル / 詳細モード
- 特定ウィンドウでのみロック
- ウィンドウ切り替え時の自動ロック / アンロック
- 単一インスタンス検出
- スタートアップ起動
- 多言語対応：English, 简体中文, 繁體中文, 日本語, 한국어
- ライト / ダークテーマ
- マルチディスプレイ対応
- マウスマクロ：マウスボタンを押しながら別のマウスボタンを押してルールを実行

## プロジェクト構成

- `mouse_center_lock_gui.py` – GUI アプリ（PySide6）
- `win_api.py` – Windows API ラッパー
- `widgets.py` – カスタム UI コンポーネント
- `services/` – 実行時サービス（クリック連打、ロック状態機械、マクロ）
- `ui/pages/` – シンプル / 詳細ページ
- `tests/` – ユニットテスト
- `i18n/` – 言語ファイル
- `assets/` – アイコンとリソース
- `examples/mouse-macros/` – マウスマクロの JSON 例
- `Mconfig.json` – デフォルト設定（旧 `config.json` も互換読み込み）

## 必要環境

- Windows 10+
- Python 3.9+
- 依存関係：`requirements.txt` を参照

依存関係のインストール：
```bash
python -m pip install -r requirements.txt
```

実行：
```bash
python mouse_center_lock_gui.py
```

テスト：
```bash
python -m unittest discover tests
```

## ビルド（PyInstaller）

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

exe は `dist/MCL.exe` に出力されます。

## マウスマクロ設定

マウスマクロは、UI ビルダーと外部 JSON ファイルの両方に対応しています。完全な書式、サンプルファイル、マウスボタン名、キーボード `key` 名は次を参照してください。

- [マウスマクロ例と設定リファレンス](examples/mouse-macros/ja/README.md)

## 変更履歴

完全な変更履歴は [CHANGELOG.md](CHANGELOG.md) を確認してください。

## ライセンス

[GPL-3.0](LICENSE)
