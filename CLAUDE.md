# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

生活保護受給者を「ケース番号」ではなく「尊厳ある個人」として支援するためのNeo4jグラフデータベースシステム。

**核心理念**: 支援者が「善意の加害者」にならないための防波堤 + 経済的搾取からの保護

## 関連ドキュメント

| ドキュメント | 内容 |
|------------|------|
| `docs/Manifesto_LivelihoodSupport_Graph.md` | プロジェクトの理念とデータモデル哲学 |
| `docs/SPECIFICATION.md` | システム要件定義（FR/NFR） |
| `docs/TASKS.md` | フェーズ別開発タスク |
| `docs/TECHNICAL_STANDARDS.md` | 技術基準書（セキュリティ、API設計） |

**重要**: マニフェストはプロジェクトの「憲法」です。すべての実装はマニフェストの理念に準拠すること。

## 開発コマンド

```bash
# 依存関係インストール
uv sync

# Neo4jコンテナ起動（ポート7475/7688）
docker compose up -d

# データベーススキーマ初期化（初回のみ）
uv run python setup_schema.py

# Streamlitアプリ起動（データ入力UI）
uv run streamlit run app_case_record.py

# MCPサーバー起動（Claude Desktop連携）
uv run mcp/server.py

# テスト実行
uv run pytest
```

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│  Streamlit (app_case_record.py)                     │
│    └─→ Gemini API (lib/ai_extractor.py)             │
│          └─→ Neo4j Database (lib/db_operations.py)  │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  Neo4j Database (Docker: ポート7475/7688)           │
│    7本柱データモデル（Manifesto Version 1.4）       │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│  MCP Server (mcp/server.py)                         │
│    Claude Desktop連携用API                          │
└─────────────────────────────────────────────────────┘
```

### コアモジュール

| ファイル | 役割 |
|---------|------|
| `lib/db_operations.py` | Neo4jへのCRUD操作、7本柱データモデル実装 |
| `lib/ai_extractor.py` | Gemini APIによるケース記録→構造化JSON変換 |
| `lib/utils.py` | 日付パース、セッション管理、ユーティリティ |
| `lib/file_readers.py` | Word/Excel/PDF/テキストファイル読み込み |
| `mcp/server.py` | FastMCPベースのClaude Desktop連携サーバー |

### 7本柱データモデル

| 柱 | 主要ノード | 重要度 |
|----|-----------|-------|
| 第1の柱（ケース記録） | `:CaseRecord`, `:HomeVisit` | ★★★★★ |
| 第2の柱（本人像） | `:Strength`, `:Challenge`, `:Pattern` | ★★★★☆ |
| 第3の柱（関わり方の知恵） | `:NgApproach`, `:EffectiveApproach` | ★★★★★ |
| 第4の柱（申告歴） | `:DeclaredHistory`, `:Wish` | ★★★☆☆ |
| 第5の柱（社会的ネットワーク） | `:KeyPerson`, `:FamilyMember` | ★★★★☆ |
| 第6の柱（法的基盤） | `:ProtectionDecision`, `:Certificate` | ★★★☆☆ |
| 第7の柱（金銭的安全・連携） | `:EconomicRisk`, `:DailyLifeSupportService`, `:CollaborationRecord` | ★★★★★ |

## ドメイン固有のルール

### 二次被害防止（最優先）

- **NgApproach（避けるべき関わり方）** を常に最優先で表示
- 精神疾患のある方への「指導」「約束の強要」は二次被害リスク
- 批判的表現（「怠惰」「指導した」等）は尊厳を守る表現に変換

### 経済的安全の確保

- 親族による金銭搾取のサイン検出: 「受給日直後にお金がない」「息子が来て持っていった」
- `EconomicRisk` ノードへの記録と日常生活自立支援事業への連携

### AI構造化プロンプト

`lib/ai_extractor.py` の `EXTRACTION_PROMPT` は7本柱に準拠した抽出ルールを定義。変更時はマニフェスト（`docs/Manifesto_LivelihoodSupport_Graph.md`）との整合性を確認すること。

## 環境変数

```bash
NEO4J_URI=bolt://localhost:7688        # 別プロジェクト(7687)と区別
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
GEMINI_API_KEY=your_gemini_api_key
```

## MCPツール優先度

| 重要度 | ツール名 | 用途 |
|-------|---------|------|
| ★★★★★ | `search_emergency_info` | 緊急時の安全情報取得 |
| ★★★★★ | `get_visit_briefing_tool` | 訪問前ブリーフィング |
| ★★★★★ | `detect_critical_guidance` | 批判的指導の検知 |
| ★★★★☆ | `get_handover_summary_tool` | 引き継ぎサマリー生成 |
| ★★★★☆ | `add_support_log` | 支援記録の自動構造化登録 |
| ★★★★☆ | `find_similar_cases` | 類似案件パターン検索 |

## バックアップ

```bash
# 手動バックアップ
./scripts/backup.sh

# フルバックアップ（コンテナ停止してtar.gz圧縮）
./scripts/backup.sh --full

# 復元
./scripts/restore.sh
```

## セキュリティ基準

### 入力値検証

- すべてのユーザー入力は検証必須
- Cypherクエリは必ずパラメータ化（文字列連結禁止）
- XSSパターン、プロンプトインジェクションの検出と拒否

```python
# NG: 文字列連結（インジェクション脆弱性）
query = f"MATCH (c:Client {{name: '{name}'}}) RETURN c"

# OK: パラメータ化クエリ
query = "MATCH (c:Client {name: $name}) RETURN c"
result = session.run(query, name=name)
```

### 監査ログ要件（TECHNICAL_STANDARDS.md 4.4準拠）

監査ログには以下の項目を記録:
- `timestamp`: ISO 8601形式
- `user_id` / `username`: 操作ユーザー
- `action`: 操作種別（CREATE/READ/UPDATE/DELETE）
- `resource_type`: 対象リソース種別
- `resource_id`: 対象リソースID
- `ip_address`: クライアントIP
- `result`: SUCCESS/FAILURE

### プロンプトインジェクション対策

AI構造化処理への入力は以下のパターンを検出・拒否:
- `ignore previous instructions`
- `disregard above`
- `new instructions:`
- `システムプロンプト`

## 開発ロードマップ

### Phase 0: 現状維持（完了）
- 現行機能の整理と動作確認

### Phase 1: 基盤整備（進行中）
- コード品質向上
- 監査ログ強化
- 入力値検証

### Phase 2以降（計画）
- FastAPI RESTful API追加
- Keycloak認証基盤
- HashiCorp Vault秘密管理
- Ollama（ローカルLLM）移行

詳細は `docs/TASKS.md` を参照。

## コーディング規約

- Python 3.11+、型ヒント推奨
- docstring必須（関数・クラス）
- テストは `tests/` ディレクトリに配置
- 批判的表現は使用禁止（マニフェスト準拠）
