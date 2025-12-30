# セットアップガイド

このガイドでは、プログラミングの知識がなくても、このシステムをセットアップできるよう、一つずつ丁寧に説明します。

## 目次

1. [このシステムについて](#このシステムについて)
2. [必要なもの](#必要なもの)
3. [事前準備](#事前準備)
   - [Macの場合](#macの場合)
   - [Windowsの場合](#windowsの場合)
4. [システムのセットアップ](#システムのセットアップ)
5. [動作確認](#動作確認)
6. [トラブルシューティング](#トラブルシューティング)

---

## このシステムについて

このシステムは、生活保護受給者を「ケース番号」ではなく「尊厳ある個人」として支援するためのデータベースシステムです。

```
┌─────────────────────────────────────────────────────┐
│  Streamlit（データ入力画面）                         │
│    ↓ ケース記録を入力                               │
│  Gemini AI（AIによる構造化）                        │
│    ↓ 自動的に情報を整理                             │
│  Neo4j（グラフデータベース）                        │
│    → 関係性を可視化して支援に活用                   │
└─────────────────────────────────────────────────────┘
```

---

## 必要なもの

| 必要なソフト | 用途 | 必須/任意 |
|------------|------|----------|
| Docker Desktop | データベースを動かすため | **必須** |
| Python 3.11以上 | プログラムを動かすため | **必須** |
| uv | Pythonの依存関係を管理 | **必須** |
| Git | プログラムをダウンロード | **必須** |
| Gemini API キー | AIによるテキスト構造化 | 任意（AI機能を使う場合） |

---

## 事前準備

### Macの場合

#### ステップ1: Homebrewをインストール

Homebrewは、Macでソフトウェアを簡単にインストールするためのツールです。

1. **ターミナルを開く**
   - `Finder` → `アプリケーション` → `ユーティリティ` → `ターミナル` をダブルクリック
   - または `Command + Space` を押して「ターミナル」と入力

2. **以下のコマンドをコピー＆ペースト**して `Enter` キーを押す：
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. パスワードを求められたら、Macのログインパスワードを入力（入力しても画面に表示されません）

4. インストールが完了したら、ターミナルを一度閉じて開き直す

#### ステップ2: Docker Desktopをインストール

1. **Docker公式サイト** (https://www.docker.com/products/docker-desktop/) にアクセス

2. 「Download for Mac」をクリック
   - Apple Silicon (M1/M2/M3チップ) のMacは「Apple Silicon」を選択
   - Intel チップのMacは「Intel chip」を選択

3. ダウンロードした `.dmg` ファイルを開く

4. Dockerアイコンを「Applications」フォルダにドラッグ

5. アプリケーションフォルダから **Docker** を起動

6. 初回起動時、利用規約に同意して設定を完了

7. メニューバーにDockerのクジラアイコン🐳が表示されればOK

#### ステップ3: Pythonとuvをインストール

ターミナルで以下のコマンドを実行：

```bash
# Python 3.12をインストール
brew install python@3.12

# uvをインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# ターミナルを再起動するか、以下を実行
source ~/.zshrc
```

#### ステップ4: Gitをインストール

```bash
brew install git
```

#### ステップ5: インストール確認

以下のコマンドを実行して、バージョンが表示されれば成功：

```bash
# Dockerの確認
docker --version
# 出力例: Docker version 24.0.7, build ...

# Pythonの確認
python3 --version
# 出力例: Python 3.12.0

# uvの確認
uv --version
# 出力例: uv 0.5.x

# Gitの確認
git --version
# 出力例: git version 2.43.0
```

---

### Windowsの場合

#### ステップ1: Docker Desktopをインストール

1. **Docker公式サイト** (https://www.docker.com/products/docker-desktop/) にアクセス

2. 「Download for Windows」をクリック

3. ダウンロードした `Docker Desktop Installer.exe` を実行

4. インストーラーの指示に従ってインストール
   - 「Use WSL 2 instead of Hyper-V」にチェックを入れることを推奨

5. インストール完了後、**PCを再起動**

6. 再起動後、スタートメニューから **Docker Desktop** を起動

7. 利用規約に同意して設定を完了

8. タスクバーにDockerのクジラアイコン🐳が表示されればOK

> **注意**: WSL 2が必要な場合、Dockerが自動的にインストールを促します。指示に従ってWSL 2をセットアップしてください。

#### ステップ2: Pythonをインストール

1. **Python公式サイト** (https://www.python.org/downloads/) にアクセス

2. 「Download Python 3.12.x」をクリック

3. ダウンロードした `.exe` ファイルを実行

4. **重要**: 最初の画面で **「Add Python to PATH」にチェック**を入れる ☑️

5. 「Install Now」をクリック

6. インストール完了後、「Close」をクリック

#### ステップ3: uvをインストール

1. **PowerShell を管理者として実行**
   - スタートメニューで「PowerShell」を検索
   - 右クリック → 「管理者として実行」

2. 以下のコマンドを実行：
   ```powershell
   irm https://astral.sh/uv/install.ps1 | iex
   ```

3. PowerShellを閉じて、再度開く

#### ステップ4: Gitをインストール

1. **Git公式サイト** (https://git-scm.com/download/win) にアクセス

2. 自動でダウンロードが始まる（始まらない場合は「Click here to download manually」をクリック）

3. ダウンロードした `.exe` ファイルを実行

4. インストーラーの設定は、すべてデフォルトのまま「Next」で進む

5. インストール完了

#### ステップ5: インストール確認

**コマンドプロンプト**または**PowerShell**を開いて確認：

```powershell
# Dockerの確認
docker --version
# 出力例: Docker version 24.0.7, build ...

# Pythonの確認
python --version
# 出力例: Python 3.12.0

# uvの確認
uv --version
# 出力例: uv 0.5.x

# Gitの確認
git --version
# 出力例: git version 2.43.0.windows.1
```

---

## システムのセットアップ

以下の手順は、Mac/Windows共通です。

### ステップ1: プロジェクトをダウンロード

ターミナル（Mac）またはPowerShell（Windows）で：

```bash
# 作業ディレクトリに移動（例: ドキュメントフォルダ）
cd ~/Documents

# プロジェクトをダウンロード（クローン）
git clone <リポジトリURL> neo4j-livelihood-support

# プロジェクトフォルダに移動
cd neo4j-livelihood-support
```

> **注意**: `<リポジトリURL>` は実際のGitリポジトリURLに置き換えてください。

### ステップ2: 環境変数を設定

1. 設定ファイルのテンプレートをコピー：

   **Mac/Linux:**
   ```bash
   cp .env.example .env
   ```

   **Windows:**
   ```powershell
   copy .env.example .env
   ```

2. `.env` ファイルを編集：

   お好みのテキストエディタ（メモ帳、VSCode等）で `.env` を開き、以下を設定：

   ```
   # Neo4j データベース設定（このままでOK）
   NEO4J_URI=bolt://localhost:7688
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password

   # Gemini API キー（AI機能を使う場合のみ）
   GEMINI_API_KEY=ここにあなたのAPIキーを入力
   ```

   > **Gemini API キーの取得方法**:
   > 1. Google AI Studio (https://makersuite.google.com/app/apikey) にアクセス
   > 2. Googleアカウントでログイン
   > 3. 「Create API Key」をクリック
   > 4. 生成されたキーをコピーして `.env` に貼り付け

### ステップ3: Pythonの依存関係をインストール

```bash
uv sync
```

このコマンドは、システムに必要なすべてのPythonライブラリを自動的にインストールします。
初回は数分かかる場合があります。

### ステップ4: データベースを起動

```bash
docker compose up -d
```

> **解説**:
> - `docker compose up` : Dockerコンテナを起動
> - `-d` : バックグラウンドで実行（ターミナルを閉じても動き続ける）

起動確認：
```bash
docker compose ps
```

以下のような出力が表示されればOK：
```
NAME                        STATUS
livelihood-support-neo4j    Up (healthy)
```

### ステップ5: データベースを初期化

初回のみ、データベースの初期設定を行います：

```bash
uv run python setup_schema.py
```

成功すると以下のような出力が表示されます：
```
============================================================
生活保護受給者尊厳支援データベース - 初期設定
Manifesto Version 1.4 準拠
============================================================

ℹ️ [INFO] 制約を設定中...
✅ [SUCCESS] 制約作成: recipient_name_unique
...
✅ [SUCCESS] 初期設定が完了しました
============================================================
```

### ステップ6: アプリケーションを起動

```bash
uv run streamlit run app_case_record.py
```

ブラウザが自動的に開き、以下のURLでアプリケーションにアクセスできます：
- **URL**: http://localhost:8501

---

## 動作確認

### Neo4j ブラウザでデータを確認

1. ブラウザで http://localhost:7475 にアクセス

2. 以下の情報でログイン：
   - Username: `neo4j`
   - Password: `password`

3. ログイン後、左側のデータベースアイコンをクリックすると、登録されたデータを確認できます

### Streamlit アプリの使い方

1. http://localhost:8501 にアクセス

2. 左側のサイドバーから機能を選択

3. ケース記録を入力して「登録」ボタンをクリック

---

## システムの停止と再起動

### システムを停止する

```bash
# Streamlitは Ctrl+C で停止

# データベースを停止
docker compose down
```

### システムを再起動する

```bash
# データベースを起動
docker compose up -d

# アプリケーションを起動
uv run streamlit run app_case_record.py
```

---

## トラブルシューティング

### 「docker: command not found」と表示される

- **原因**: Docker Desktopがインストールされていないか、起動していない
- **対処法**:
  1. Docker Desktopがインストールされているか確認
  2. Docker Desktopを起動（メニューバー/タスクバーにクジラアイコンが表示されるまで待つ）

### 「Port 7475 is already in use」と表示される

- **原因**: 別のプログラムがポート7475を使用している
- **対処法**:
  ```bash
  # 使用中のポートを確認（Mac/Linux）
  lsof -i :7475

  # 使用中のポートを確認（Windows）
  netstat -ano | findstr 7475
  ```
  該当するプログラムを停止するか、`.env`ファイルでポート番号を変更

### 「Cannot connect to Neo4j」と表示される

- **原因**: データベースが起動していない
- **対処法**:
  ```bash
  # コンテナの状態を確認
  docker compose ps

  # 停止している場合は起動
  docker compose up -d

  # ログを確認
  docker compose logs neo4j
  ```

### 「ModuleNotFoundError」と表示される

- **原因**: Pythonの依存関係がインストールされていない
- **対処法**:
  ```bash
  uv sync
  ```

### Windowsで「スクリプトの実行が無効」エラー

- **原因**: PowerShellの実行ポリシーが制限されている
- **対処法**（管理者としてPowerShellを実行）:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### データをすべて削除してやり直したい

```bash
# コンテナを停止して削除
docker compose down -v

# データディレクトリを削除
rm -rf neo4j_data neo4j_logs neo4j_plugins

# 再度セットアップ
docker compose up -d
uv run python setup_schema.py
```

---

## よくある質問（FAQ）

### Q: Gemini API キーは必須ですか？

**A**: いいえ。AIによるテキスト構造化機能を使わない場合は不要です。手動でデータを入力することは可能です。

### Q: データはどこに保存されますか？

**A**: プロジェクトフォルダ内の `neo4j_data` ディレクトリにデータベースファイルが保存されます。このフォルダをバックアップすれば、データを保護できます。

### Q: 複数のPCで使いたい場合は？

**A**: 各PCでセットアップを行う必要があります。データを共有する場合は、バックアップ・復元機能を使用してください：
```bash
# バックアップ
./scripts/backup.sh

# 復元
./scripts/restore.sh
```

### Q: アップデートはどうすればいいですか？

**A**:
```bash
# 最新版をダウンロード
git pull

# 依存関係を更新
uv sync

# 必要に応じてデータベースを再初期化
uv run python setup_schema.py
```

---

## サポート

問題が解決しない場合は、以下の情報を添えてお問い合わせください：

1. お使いのOS（Mac/Windows）とバージョン
2. エラーメッセージ全文
3. 実行したコマンド
4. `docker compose logs` の出力

---

## 次のステップ

セットアップが完了したら、以下のドキュメントも参照してください：

- `docs/Manifesto_LivelihoodSupport_Graph.md` - システムの理念とデータモデル
- `docs/SPECIFICATION.md` - 機能仕様書
- `docs/OPERATIONS_GUIDE.md` - 運用ガイド
