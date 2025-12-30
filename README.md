# 生活保護受給者尊厳支援データベース

**Manifesto: Livelihood Protection Support & Dignity Graph (Version 1.4)**

生活保護受給者を「ケース番号」ではなく「尊厳ある個人」として支援するための、Neo4jグラフデータベースシステムです。

## 🎯 理念

> 「支援とは、相手を変えることではなく、相手が自分の足で歩き出せるよう、伴走する事です。」

このシステムは、**支援者が「善意の加害者」にならないための防波堤**です。

## ✨ 主な機能

### 二次被害防止（最重要）
- ⚠️ **避けるべき関わり方（NgApproach）** の記録と引き継ぎ
- 🏥 精神疾患のある方への適切なアプローチ提示
- 批判的指導の検知と警告

### 経済的安全の確保【Version 1.4 新機能】
- 💰 金銭管理困難の記録と支援
- ⚠️ 経済的搾取（親族等からの金銭搾取）の検出
- 日常生活自立支援事業との連携

### 多機関連携【Version 1.4 新機能】
- 🤝 ケース会議・情報共有の記録
- 類似案件パターンの蓄積と活用
- 効果的な介入方法の組織知化

### ケース記録の資産化
- AI自動構造化（Gemini API）
- 効果的だった関わり方の自動抽出
- 強みの発見と記録

## 🏗️ システム構成

```
┌──────────────────────────────────────────────────────────────┐
│                    フロントエンド                             　│
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Streamlit App (app_case_record.py)                      │ │
│  │   └─→ Gemini API (ai_extractor.py) → 構造化データ抽出   　 │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    REST API (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ api/main.py - 認証・認可・メトリクス                        │ │
│  │   ├─ /api/v1/recipients - 受給者管理                      │ │
│  │   ├─ /api/v1/records - ケース記録                         │ │
│  │   ├─ /metrics - Prometheusメトリクス                      │ │
│  │   └─ /health - ヘルスチェック                             │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│              Neo4j Database (Docker)                          │
│     ★ ポート 7475(Browser) / 7688(Bolt)                      │
│         7本柱のデータモデル（Version 1.4）                    │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    分析・対話・提案                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Claude Desktop + MCP (mcp/server.py)                    │ │
│  │   ・訪問前ブリーフィング                                 │ │
│  │   ・ケース相談（対話的）                                 │ │
│  │   ・引き継ぎサマリー生成                                 │ │
│  │   ・類似案件パターン検索                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    認証・監視                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Keycloak (OIDC認証) + Prometheus/Grafana (監視)         │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## 🐳 ポート構成（Docker）

| サービス | ポート | 用途 |
|---------|--------|------|
| Neo4j Browser | 7475 | グラフデータベースUI |
| Neo4j Bolt | 7688 | データベース接続 |
| Keycloak | 8080 | 認証管理コンソール |
| Streamlit | 8501 | データ入力アプリ |
| FastAPI | 8000 | REST API |
| Prometheus | 9090 | メトリクス収集 |
| Grafana | 3000 | 監視ダッシュボード |

### 他プロジェクトとの共存

| プロジェクト | Browser (HTTP) | Bolt (接続) | 用途 |
|-------------|----------------|-------------|------|
| neo4j-agno-agent | 7474 | 7687 | 親亡き後支援（障害福祉） |
| **neo4j-livelihood-support** | **7475** | **7688** | **生活保護支援** |

両プロジェクトを同時起動して、並行して開発・比較が可能です。

## 📦 インストール

### 前提条件
- Python 3.11以上
- Docker Desktop
- uv (Pythonパッケージマネージャー)

### セットアップ

```bash
# プロジェクトディレクトリへ移動
cd ~/Dev-Work/neo4j-livelihood-support

# 依存関係のインストール
uv sync

# 環境変数の設定（必要に応じて編集）
cp .env.example .env
# .env ファイルを編集してGEMINI_API_KEYを設定

# Neo4j Dockerコンテナの起動
docker compose up -d

# データベーススキーマの初期化
uv run python setup_schema.py
```

### Neo4j Browser へのアクセス

```
http://localhost:7475
ユーザー名: neo4j
パスワード: password
```

### Keycloak（認証基盤）のセットアップ

```bash
# Keycloak環境の起動
docker compose -f docker-compose.keycloak.yml up -d

# 起動確認（1-2分待機）
curl -f http://localhost:8080/health/ready
```

#### Keycloak管理コンソール

```
http://localhost:8080
管理者: admin / admin_dev_password
```

#### テストユーザー（初回ログイン時にパスワード変更必須）

| ユーザー名 | パスワード | ロール | 所属 |
|-----------|-----------|--------|------|
| admin | admin123 | admin | - |
| supervisor1 | supervisor123 | supervisor | 福祉課/第1係 |
| caseworker1 | caseworker123 | caseworker | 福祉課/第1係 |
| caseworker2 | caseworker123 | caseworker | 福祉課/第2係 |
| auditor1 | auditor123 | auditor | - |

詳細は [認証・認可ガイド](docs/AUTHENTICATION.md) を参照してください。

### 環境変数（.env）

```env
# Neo4j接続設定（ポート7688）
NEO4J_URI=bolt://localhost:7688
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Gemini API設定
GEMINI_API_KEY=your-gemini-api-key

# Keycloak認証設定
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=livelihood-support
KEYCLOAK_CLIENT_ID=livelihood-support-app

# 開発環境設定（本番ではfalseに設定）
DEBUG=true
AUTH_SKIP=false
```

## 🚀 使い方

### 1. Neo4j の起動

```bash
cd ~/Dev-Work/neo4j-livelihood-support
docker compose up -d
```

### 2. Streamlit アプリ（データ入力）

```bash
uv run streamlit run app_case_record.py
```

ブラウザで http://localhost:8501 にアクセス

### 3. Claude Desktop + MCP（分析・対話）

Claude Desktop を再起動すると、`livelihood-support-db` が利用可能になります。

#### 利用可能なツール

| ツール名 | 説明 | 重要度 |
|---------|------|-------|
| `search_emergency_info` | 緊急時の安全情報取得 | ★★★★★ |
| `get_visit_briefing_tool` | 訪問前ブリーフィング | ★★★★★ |
| `detect_critical_guidance` | 批判的指導の検知 | ★★★★★ |
| `get_handover_summary_tool` | 引き継ぎサマリー生成 | ★★★★☆ |
| `get_client_profile` | 受給者プロフィール取得 | ★★★★☆ |
| `add_support_log` | 支援記録の追加 | ★★★★☆ |
| `get_support_logs` | 支援記録履歴の取得 | ★★★★☆ |
| `find_similar_cases` | 類似案件の検索 | ★★★★☆ |
| `discover_care_patterns` | 効果的パターンの発見 | ★★★☆☆ |
| `check_renewal_dates` | 更新期限チェック | ★★★☆☆ |
| `list_clients` | 受給者一覧 | ★★★☆☆ |
| `get_audit_logs` | 監査ログ取得 | ★★★☆☆ |

#### 使用例

```
# 訪問前の確認
「山田太郎さんの訪問ブリーフィングをお願いします」

# ケース相談
「山田さんに就労の話を振ったら黙り込んでしまいました。問題でしたか？」

# 支援記録の追加
「山田さんの支援記録: 今日の訪問で『お金がない』との訴え。
 受給日から3日しか経っていない。息子が来てお金を持っていったとのこと。」

# 引き継ぎ
「山田太郎さんの引き継ぎサマリーをお願いします」

# 類似案件の検索
「山田さんと似たケースはありますか？効果的だった介入を教えてください」
```

## 📊 7本柱データモデル

| 柱 | 役割 | 重要度 |
|----|------|-------|
| 第1の柱 | ケース記録（最重要） | ★★★★★ |
| 第2の柱 | 抽出された本人像 | ★★★★☆ |
| 第3の柱 | 関わり方の知恵（効果と禁忌） | ★★★★★ |
| 第4の柱 | 参考情報としての申告歴 | ★★★☆☆ |
| 第5の柱 | 社会的ネットワーク | ★★★★☆ |
| 第6の柱 | 法的・制度的基盤 | ★★★☆☆ |
| 第7の柱 | 金銭的安全と多機関連携【新設】 | ★★★★★ |

## 💾 バックアップと復元

福祉データは失われると取り返しがつきません。定期的なバックアップを推奨します。

### 手動バックアップ

```bash
# 通常バックアップ（オンライン、Cypherエクスポート）
./scripts/backup.sh

# フルバックアップ（コンテナを一時停止、tar.gz圧縮）
./scripts/backup.sh --full
```

バックアップ先: `./neo4j_backup/`

### 復元

```bash
# 最新のフルバックアップから復元
./scripts/restore.sh

# 指定ファイルから復元
./scripts/restore.sh full_backup_20241228_030000.tar.gz
```

⚠️ 復元時は現在のデータが上書きされます。実行前に確認があります。

### 定期バックアップの設定（推奨）

```bash
# 毎日午前3時に自動バックアップを設定
./scripts/setup_scheduled_backup.sh install

# 状態確認
./scripts/setup_scheduled_backup.sh status

# 無効化
./scripts/setup_scheduled_backup.sh uninstall
```

### バックアップの保持期間

- 自動的に**30日以上前**のバックアップは削除されます
- 重要なバックアップは別の場所にコピーしてください

## 📁 ファイル構成

```
neo4j-livelihood-support/
├── docker-compose.yml           # Neo4j Docker設定（ポート7475/7688）
├── docker-compose.keycloak.yml  # Keycloak認証基盤
├── app_case_record.py           # Streamlit データ入力アプリ
├── setup_schema.py              # Neo4j スキーマ初期化
├── pyproject.toml               # プロジェクト設定
├── .env                         # 環境変数（要作成）
├── .env.example                 # 環境変数サンプル
│
├── api/                    # REST API
│   ├── main.py             # FastAPIアプリケーション
│   ├── dependencies.py     # 認証・認可・DI
│   └── routers/            # APIルーター
│       ├── recipients.py   # 受給者管理API
│       └── records.py      # ケース記録API
│
├── lib/                    # ライブラリ
│   ├── db_operations.py    # Neo4j操作（7本柱対応）
│   ├── db_connection.py    # データベース接続管理
│   ├── auth.py             # Streamlit認証
│   ├── ai_extractor.py     # Gemini AI構造化
│   ├── file_readers.py     # ファイル読み込み
│   └── utils.py            # ユーティリティ
│
├── mcp/                    # MCPサーバー
│   └── server.py           # Claude Desktop連携
│
├── keycloak/               # Keycloak設定
│   └── realm-export.json   # レルム設定（自動インポート）
│
├── monitoring/             # 監視スタック
│   ├── prometheus/         # Prometheusルール
│   └── grafana/            # Grafanaダッシュボード
│
├── scripts/                # 運用スクリプト
│   ├── backup.sh           # バックアップ
│   ├── restore.sh          # 復元
│   └── setup_scheduled_backup.sh  # 定期バックアップ設定
│
├── tests/                  # テストスイート
│   ├── test_api_auth.py    # 認証テスト
│   ├── test_db_operations.py
│   └── ...
│
├── docs/                   # ドキュメント
│   ├── Manifesto_LivelihoodSupport_Graph.md
│   └── AUTHENTICATION.md   # 認証・認可ガイド
│
├── neo4j_data/             # Neo4jデータ（Docker volume）
├── neo4j_logs/             # Neo4jログ
└── neo4j_backup/           # バックアップファイル
```

## 🔧 Docker操作

```bash
# 起動
docker compose up -d

# 停止
docker compose down

# ログ確認
docker compose logs -f

# 完全リセット（データ削除）
docker compose down -v
rm -rf neo4j_data neo4j_logs neo4j_plugins
docker compose up -d
```

## 🔒 セキュリティと倫理

- すべての個人情報は暗号化して保存
- アクセスログを記録し、不正利用を防止
- ケース記録の閲覧権限を適切に管理
- 他機関との情報共有は本人同意を原則

## 📜 ライセンス

このプロジェクトは福祉支援の質向上を目的としています。
商用利用の際はご連絡ください。

---

**「一人の人間を傷つけないために。一人の人間が、自分のペースで、自分の足で歩き出せるように。」**
