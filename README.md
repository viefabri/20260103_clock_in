# Touch On Time Auto Clock-In

Touch On Timeの個人打刻画面を自動操作するPythonツールです。
Bitwarden CLIを利用してパスワードレス（かつハードコードなし）で安全にログインします。

## 安全機能
デフォルトで **DRY_RUN (寸止めモード)** が有効になっています。
`src/config.py` を変更しない限り、実際の「打刻」ボタンはクリックされません。

## 前提条件
- **OS**: WSL2 (Ubuntu) 推奨
- **Python**: 3.10+
- **Google Chrome**: インストール済みであること
- **Bitwarden CLI (`bw`)**: インストール済みであること

## セットアップ手順

### 1. 仮想環境の作成とライブラリのインストール
Ubuntu 24.04+ (WSL2) では、システムPythonへの直接インストールが制限されています（PEP 668）。
以下の手順で仮想環境 (`venv`) を作成して実行してください。

```bash
# 1. venvモジュールのインストール (未インストールの場合)
sudo apt install python3-venv

# 2. 仮想環境の作成
python3 -m venv venv

# 3. 仮想環境の有効化
source venv/bin/activate

# 4. 依存ライブラリのインストール
pip install -r requirements.txt
```

> **Note:** 仮想環境を有効化すると、プロンプトに `(venv)` と表示されます。
> 以降のコマンドは、この状態で実行してください。

### 2. Bitwardenの準備
`bw` コマンドがログイン状態であり、Touch On Time用のアイテムが存在することを確認してください。

```bash
# ログイン（初回のみ）
bw login

# セッションキーの発行と環境変数へのセット（毎回、またはprofile等で設定）
export BW_SESSION=$(bw unlock --raw)

# アイテムの確認 (config.py の BITWARDEN_ITEM_NAME と一致させる)
bw get item touchontime_personal
```

### 3. 設定の確認
`src/config.py` を開き、以下の項目を確認・変更してください。
- `TOUCH_ON_TIME_URL`: URLが正しいか
- `BITWARDEN_ITEM_NAME`: Bitwardenのアイテム名
- `DRY_RUN`: 動作確認時は `True` のままにしてください

## 実行方法

引数で「出勤(`in`)」か「退勤(`out`)」を指定します。
デフォルトは **DryRun (寸止め)** モードです。

```bash
# 出勤 (DryRun: 打刻しません)
python3 main.py in

# 退勤 (DryRun: 打刻しません)
python3 main.py out
```

実際に打刻を行う場合は `--live` オプションを付けます。

```bash
# 【本番】出勤打刻
python3 main.py in --live

# 【本番】退勤打刻
python3 main.py out --live
```

### 時間チェック機能
以下の時間は推奨時間外として警告ログが出ますが、処理は続行されます。
- 出勤: 08:45 - 09:00 以外
- 退勤: 18:00 - 20:00 以外

## 💻 Screen Operation (Web UI)

本アプリケーションは [Streamlit](https://streamlit.io/) を使用したWeb UIを提供しています。

### 起動方法

**デスクトップアプリとして起動（推奨）:**
```bash
make app
```
-> 小さなランチャー画面が立ち上がります。「Start Web UI」でサーバを起動し、ウィンドウを閉じるとサーバも終了します。

**サーバーモードで起動:**
```bash
make web
```

### ショートカットキー (Web UI)
効率的な操作のために以下のショートカットが利用可能です。

| キー操作 | 動作 |
| :--- | :--- |
| **Alt + Shift + D** | **日付 (Date)** 入力欄にフォーカス |
| **Alt + Shift + T** | **時刻 (Time)** 入力欄にフォーカス |
| **Shift + S** | **登録 (Add Schedule)** ボタンを実行 |
| **Shift + Enter** | **今すぐ実行 (Run Now)** ボタンを実行 |
| **Alt + 1** | Type: **出勤 (In)** を選択 |
| **Alt + 2** | Type: **退勤 (Out)** を選択 |

## プロジェクト構成

```
src/
├── config/             # 設定ファイル (Settings)
├── core/               # ビジネスロジック (Automator, Bitwarden)
├── interfaces/         # ユーザーインターフェース (CLI, GUI, Web)
│   ├── cli/            # コマンドラインツール
│   ├── gui/            # Streamlitランチャー (Desktop App)
│   └── web/            # Webブラウザ管理画面
└── utils/              # ユーティリティ (Logger)
```

## 使い方

### 1. ランチャー起動 (推奨)
```bash
make app
```
GUIランチャーが起動し、サーバーの起動・停止、ブラウザ表示を管理できます。

### 2. CLI実行 (手動)
```bash
# 出勤 (本番)
make cli -- type=in --live
```
- `bw` コマンドがエラーになる場合は、`export BW_SESSION=...` が正しく設定されているか確認してください。

## エラー時の対応
- `src/automator.py` はエラー時にスクリーンショット (`error_*.png`) を保存します。
- `bw` コマンドがエラーになる場合は、`export BW_SESSION=...` が正しく設定されているか確認してください。
