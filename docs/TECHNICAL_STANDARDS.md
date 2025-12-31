# 生活保護受給者尊厳支援システム 技術基準書

**文書番号**: TECH-LVS-2024-001
**バージョン**: 2.0
**作成日**: 2024年12月28日
**ステータス**: ドラフト

---

## 1. 概要

### 1.1 目的

本技術基準書は、生活保護受給者尊厳支援システムの設計・開発・運用において遵守すべき技術的基準を定義する。

### 1.2 適用範囲

- アプリケーション開発
- インフラストラクチャ構築
- セキュリティ実装
- 運用・保守

---

## 2. 技術スタック

### 2.1 採用技術一覧

| レイヤー | 技術 | バージョン | 選定理由 |
|----------|------|-----------|----------|
| **言語** | Python | 3.11+ | 型ヒント、AI/MLエコシステム |
| **Webフレームワーク** | FastAPI | 0.100+ | 高性能、型安全、OpenAPI自動生成 |
| **UIフレームワーク** | Streamlit | 1.30+ | 迅速なプロトタイピング（入力UI） |
| **データベース** | Neo4j | 5.x | グラフDB、関係性表現に最適 |
| **ローカルLLM** | Ollama | 最新 | オンプレミスLLM実行基盤 |
| **LLMモデル** | Llama 3.2 / Gemma 2 | - | 日本語対応、商用利用可能 |
| **コンテナ** | Docker | 24.x+ | 環境統一、デプロイ簡素化 |
| **オーケストレーション** | Docker Compose | 2.x | 開発環境、小規模本番 |
| **シークレット管理** | HashiCorp Vault | 1.15+ | 認証情報の安全な管理 |
| **認証基盤** | Keycloak | 23.x | OIDC/SAML、LDAP連携 |

### 2.2 技術選定基準

1. **オンプレミス運用可能**: クラウド依存を排除
2. **オープンソース優先**: ベンダーロックイン回避
3. **日本語対応**: UIおよびAI処理
4. **セキュリティ**: 認証・暗号化の標準サポート
5. **保守性**: 活発なコミュニティ、長期サポート

---

## 3. アーキテクチャ基準

### 3.1 システム構成図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        オンプレミス環境                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐  │
│  │  クライアント │────→│  Keycloak   │────→│  リバースプロキシ        │  │
│  │  (ブラウザ)  │     │  (認証)     │     │  (Nginx + TLS)          │  │
│  └─────────────┘     └─────────────┘     └───────────┬─────────────┘  │
│                                                       │                 │
│         ┌─────────────────────────────────────────────┼─────────────┐  │
│         │                  内部ネットワーク            │             │  │
│         │                                             ▼             │  │
│  ┌──────┴──────┐  ┌─────────────────┐  ┌─────────────────────────┐  │  │
│  │             │  │                 │  │                         │  │  │
│  │  Streamlit  │  │    FastAPI      │  │     MCP Server          │  │  │
│  │  入力UI     │  │    REST API     │  │     (Claude連携)        │  │  │
│  │  :8501      │  │    :8000        │  │     :8080               │  │  │
│  │             │  │                 │  │                         │  │  │
│  └──────┬──────┘  └────────┬────────┘  └────────────┬────────────┘  │  │
│         │                  │                        │               │  │
│         └──────────────────┼────────────────────────┘               │  │
│                            ▼                                        │  │
│  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │                    サービス層                                │   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │  │
│  │  │ 認証サービス │  │ 監査サービス │  │ 匿名化サービス      │  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │  │
│  └─────────────────────────────────────────────────────────────┘   │  │
│                            │                                        │  │
│         ┌──────────────────┴──────────────────┐                    │  │
│         ▼                                      ▼                    │  │
│  ┌─────────────────┐                  ┌─────────────────────┐      │  │
│  │                 │                  │                     │      │  │
│  │    Neo4j        │                  │     Ollama          │      │  │
│  │    Cluster      │                  │     (ローカルLLM)    │      │  │
│  │    :7687(Bolt)  │                  │     :11434          │      │  │
│  │                 │                  │                     │      │  │
│  └─────────────────┘                  └─────────────────────┘      │  │
│         │                                                          │  │
│         └──────→ 暗号化ストレージ ←── バックアップ                 │  │
│                                                                    │  │
└────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 設計原則

| 原則 | 説明 | 適用例 |
|------|------|--------|
| **Defense in Depth** | 多層防御 | 認証→認可→暗号化→監査 |
| **Least Privilege** | 最小権限 | ロールベースアクセス制御 |
| **Separation of Concerns** | 関心の分離 | UI/API/DB/AIの分離 |
| **Fail Secure** | 安全側に失敗 | エラー時はアクセス拒否 |
| **Zero Trust** | ゼロトラスト | 内部通信も認証・暗号化 |

---

## 4. セキュリティ基準

### 4.1 認証・認可

#### 4.1.1 認証要件

```yaml
# 認証設定基準
authentication:
  method: OIDC  # OpenID Connect
  provider: Keycloak
  mfa:
    required: true
    methods:
      - TOTP (Google Authenticator等)
      - Email OTP (バックアップ)
  session:
    timeout: 1800  # 30分
    absolute_timeout: 28800  # 8時間
    concurrent_sessions: 1  # 同時ログイン禁止
  password_policy:
    min_length: 12
    require_uppercase: true
    require_lowercase: true
    require_number: true
    require_special: true
    max_age_days: 90
    history_count: 12  # 過去12回分は再利用禁止
  lockout:
    max_attempts: 5
    lockout_duration: 900  # 15分
```

#### 4.1.2 認可要件

```python
# RBACポリシー定義例
class Permission(Enum):
    READ_OWN_CASES = "read:own_cases"
    WRITE_OWN_CASES = "write:own_cases"
    READ_TEAM_CASES = "read:team_cases"
    READ_ALL_CASES = "read:all_cases"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT_LOGS = "view:audit_logs"
    SYSTEM_ADMIN = "system:admin"

ROLE_PERMISSIONS = {
    "CW": [Permission.READ_OWN_CASES, Permission.WRITE_OWN_CASES],
    "SV": [Permission.READ_OWN_CASES, Permission.WRITE_OWN_CASES,
           Permission.READ_TEAM_CASES, Permission.VIEW_AUDIT_LOGS],
    "Admin": [Permission.SYSTEM_ADMIN],  # 全権限
    "ReadOnly": []  # 統計のみ（別途実装）
}
```

### 4.2 暗号化基準

#### 4.2.1 保存データ暗号化

| 対象 | アルゴリズム | 鍵長 | 鍵管理 |
|------|-------------|------|--------|
| データベース | AES-256-GCM | 256bit | Vault |
| ファイル添付 | AES-256-GCM | 256bit | Vault |
| バックアップ | AES-256-GCM | 256bit | オフライン鍵 |
| ログファイル | - | - | ディスク暗号化 |

#### 4.2.2 通信暗号化

| 通信経路 | プロトコル | 設定 |
|----------|-----------|------|
| クライアント↔リバプロ | TLS 1.3 | 必須 |
| リバプロ↔アプリ | TLS 1.2+ | 内部CA証明書 |
| アプリ↔Neo4j | Bolt over TLS | 証明書認証 |
| アプリ↔Ollama | HTTPS | API Key + mTLS |

```yaml
# TLS設定基準
tls:
  min_version: TLSv1.2
  preferred_version: TLSv1.3
  cipher_suites:
    - TLS_AES_256_GCM_SHA384
    - TLS_CHACHA20_POLY1305_SHA256
    - TLS_AES_128_GCM_SHA256
  certificate:
    key_size: 4096  # RSA
    validity_days: 365
    auto_renewal: true
```

### 4.3 入力値検証

```python
# 入力値検証基準
from pydantic import BaseModel, Field, validator
import re

class CaseRecordInput(BaseModel):
    """ケース記録入力のバリデーション"""

    client_id: str = Field(..., regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
    narrative: str = Field(..., min_length=1, max_length=50000)
    recorded_by: str = Field(..., min_length=1, max_length=100)

    @validator('narrative')
    def sanitize_narrative(cls, v):
        # XSS対策: HTMLタグ除去（必要に応じてサニタイズ）
        # SQLインジェクション: パラメータ化クエリで対応
        # NoSQLインジェクション: Cypherパラメータで対応
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('不正な文字列が含まれています')
        return v
```

### 4.4 監査ログ

#### 4.4.1 ログ記録項目

| 項目 | 説明 | 必須 |
|------|------|:----:|
| timestamp | ISO 8601形式 | ✓ |
| user_id | 操作ユーザーID | ✓ |
| username | 操作ユーザー名 | ✓ |
| action | 操作種別 | ✓ |
| resource_type | 対象リソース種別 | ✓ |
| resource_id | 対象リソースID | ✓ |
| ip_address | クライアントIP | ✓ |
| user_agent | ブラウザ/クライアント情報 | ✓ |
| result | 成功/失敗 | ✓ |
| details | 追加詳細（変更前後など） | - |

#### 4.4.2 ログフォーマット

```json
{
  "timestamp": "2024-12-28T10:30:00.000Z",
  "level": "INFO",
  "event_type": "AUDIT",
  "user_id": "usr_abc123",
  "username": "yamada.taro",
  "action": "READ",
  "resource_type": "CaseRecord",
  "resource_id": "rec_xyz789",
  "client_id": "cli_def456",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "result": "SUCCESS",
  "session_id": "ses_ghi012",
  "request_id": "req_jkl345"
}
```

#### 4.4.3 ログ保護

```yaml
audit_log:
  storage:
    type: append_only  # 追記のみ
    encryption: true
    integrity: SHA-256  # ハッシュチェーン
  retention:
    period: 7years
    archive: true
  access:
    read: [SV, Admin]
    export: [Admin]
    delete: prohibited  # 削除禁止
```

---

## 5. データベース基準

### 5.1 Neo4j設定

```conf
# neo4j.conf 推奨設定

# セキュリティ
dbms.security.auth_enabled=true
dbms.security.procedures.unrestricted=apoc.*
dbms.security.allow_csv_import_from_file_urls=false

# TLS/SSL
dbms.ssl.policy.bolt.enabled=true
dbms.ssl.policy.bolt.base_directory=certificates
dbms.ssl.policy.bolt.private_key=private.key
dbms.ssl.policy.bolt.public_certificate=public.crt
dbms.ssl.policy.bolt.client_auth=REQUIRE
dbms.connector.bolt.tls_level=REQUIRED

# メモリ設定（8GBサーバーの場合）
server.memory.heap.initial_size=2g
server.memory.heap.max_size=4g
server.memory.pagecache.size=2g

# 接続設定
server.bolt.listen_address=:7687
server.bolt.advertised_address=localhost:7687
dbms.connector.bolt.connection_keep_alive=30s
dbms.connector.bolt.connection_keep_alive_for_requests=ALL

# ログ
dbms.logs.query.enabled=INFO
dbms.logs.query.threshold=1s
```

### 5.2 スキーマ設計基準

```cypher
// インデックス設計
CREATE INDEX client_id_idx FOR (c:Client) ON (c.client_id);
CREATE INDEX record_date_idx FOR (r:CaseRecord) ON (r.recorded_at);
CREATE INDEX user_username_idx FOR (u:User) ON (u.username);

// 制約設計
CREATE CONSTRAINT client_id_unique FOR (c:Client) REQUIRE c.client_id IS UNIQUE;
CREATE CONSTRAINT user_id_unique FOR (u:User) REQUIRE u.user_id IS UNIQUE;
CREATE CONSTRAINT record_id_unique FOR (r:CaseRecord) REQUIRE r.record_id IS UNIQUE;

// 必須プロパティ制約
CREATE CONSTRAINT client_required FOR (c:Client)
  REQUIRE (c.client_id, c.created_at) IS NOT NULL;
```

### 5.3 クエリ基準

```python
# Cypherクエリのセキュリティ基準

# ✓ 正しい: パラメータ化クエリ
def get_client(tx, client_id: str):
    query = """
    MATCH (c:Client {client_id: $client_id})
    RETURN c
    """
    return tx.run(query, client_id=client_id)

# ✗ 禁止: 文字列連結（インジェクション脆弱性）
def get_client_unsafe(tx, client_id: str):
    query = f"MATCH (c:Client {{client_id: '{client_id}'}}) RETURN c"
    return tx.run(query)  # 絶対に禁止
```

---

## 6. API設計基準

### 6.1 RESTful API規約

```yaml
# API設計規約
api:
  version: v1
  base_path: /api/v1

  # HTTPメソッド使用規約
  methods:
    GET: 読み取り（冪等性あり）
    POST: 作成
    PUT: 全体更新
    PATCH: 部分更新
    DELETE: 削除（論理削除推奨）

  # レスポンス形式
  response:
    format: JSON
    envelope: true
    fields:
      - data: リソースデータ
      - meta: メタ情報（ページング等）
      - errors: エラー情報

  # ステータスコード
  status_codes:
    200: 成功
    201: 作成成功
    204: 削除成功
    400: リクエスト不正
    401: 認証エラー
    403: 認可エラー
    404: リソース不存在
    422: バリデーションエラー
    500: サーバーエラー
```

### 6.2 API仕様例

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

app = FastAPI(
    title="Livelihood Support API",
    version="2.0.0",
    docs_url=None,  # 本番では無効化
    redoc_url=None
)

@app.get("/api/v1/clients/{client_id}")
async def get_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Neo4jDriver = Depends(get_db)
):
    """
    クライアント情報取得

    - 認証必須
    - 担当ケースまたはSV以上の権限が必要
    - 監査ログ記録
    """
    # 権限チェック
    if not can_access_client(current_user, client_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このケースへのアクセス権限がありません"
        )

    # 監査ログ
    await audit_log.record(
        user=current_user,
        action="READ",
        resource_type="Client",
        resource_id=client_id
    )

    # データ取得
    client = await db.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404)

    return {"data": client}
```

### 6.3 エラーレスポンス

```json
{
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "入力値が不正です",
      "field": "narrative",
      "detail": "50000文字以内で入力してください"
    }
  ],
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2024-12-28T10:30:00Z"
  }
}
```

---

## 7. AI/LLM基準

### 7.1 ローカルLLM設定

```yaml
# Ollama設定
ollama:
  host: localhost
  port: 11434

  models:
    primary: llama3.2:8b-instruct-q4_K_M
    fallback: gemma2:9b-instruct-q4_K_M

  parameters:
    temperature: 0.3  # 低めで安定した出力
    top_p: 0.9
    max_tokens: 4096
    timeout_seconds: 60

  resource_limits:
    max_concurrent_requests: 4
    gpu_memory_fraction: 0.8
```

### 7.2 プロンプト設計基準

```python
# プロンプトテンプレート基準
CASE_STRUCTURING_PROMPT = """
あなたは福祉支援の専門家です。以下のケース記録を構造化してください。

【入力】
{narrative}

【出力形式】
以下のJSON形式で出力してください：
{{
  "summary": "要約（100字以内）",
  "key_issues": ["課題1", "課題2"],
  "strengths": ["強み1", "強み2"],
  "risks": ["リスク1", "リスク2"],
  "recommended_actions": ["推奨アクション1", "推奨アクション2"]
}}

【注意事項】
- 事実と推測を明確に区別してください
- 批判的・否定的な表現は避けてください
- 受給者の尊厳を尊重した表現を使用してください
"""

# プロンプトインジェクション対策
def sanitize_for_prompt(text: str) -> str:
    """プロンプトインジェクション対策"""
    # 制御文字の除去
    # 指示を上書きする可能性のあるパターンの検出
    dangerous_patterns = [
        r'ignore previous instructions',
        r'disregard above',
        r'new instructions:',
        r'システムプロンプト',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("不正な入力が検出されました")
    return text
```

### 7.3 AI生成コンテンツの管理

```python
# AI生成コンテンツのメタデータ
class AIGeneratedContent(BaseModel):
    content: str
    generated_at: datetime
    model_name: str
    model_version: str
    prompt_hash: str  # プロンプトのハッシュ（再現性確保）
    confidence_score: Optional[float]

    # 必須ラベル
    is_ai_generated: bool = True
    requires_human_review: bool = True
```

---

## 8. 匿名化基準

### 8.1 PII識別と匿名化

```python
# 匿名化対象項目
PII_FIELDS = {
    "name": "氏名",
    "address": "住所",
    "phone": "電話番号",
    "birth_date": "生年月日",
    "client_number": "ケース番号",
    "bank_account": "口座番号",
    "my_number": "マイナンバー",
}

class Anonymizer:
    """データ匿名化サービス"""

    def anonymize_for_external_ai(self, data: dict) -> dict:
        """外部AI送信用の匿名化"""
        anonymized = data.copy()

        # 直接識別子の除去
        for field in PII_FIELDS:
            if field in anonymized:
                anonymized[field] = f"[{PII_FIELDS[field]}]"

        # テキスト内のPII検出と置換
        anonymized["narrative"] = self._anonymize_text(
            anonymized.get("narrative", "")
        )

        return anonymized

    def _anonymize_text(self, text: str) -> str:
        """テキスト内のPII検出と置換"""
        # 正規表現によるパターンマッチング
        patterns = {
            r'\d{3}-\d{4}': '[郵便番号]',
            r'\d{2,4}-\d{2,4}-\d{4}': '[電話番号]',
            r'[ァ-ヶー]+\s*[ァ-ヶー]+': '[氏名]',  # カタカナ名
            # ... 追加パターン
        }
        for pattern, replacement in patterns.items():
            text = re.sub(pattern, replacement, text)
        return text
```

### 8.2 外部AI利用時のフロー

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  元データ    │────→│  匿名化処理   │────→│  外部AI API  │
│  (PII含む)   │     │              │     │  (匿名化済)  │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  保存        │←────│  再識別処理   │←────│  AI応答      │
│  (再識別済)  │     │              │     │  (匿名化済)  │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 9. テスト基準

### 9.1 テスト種別と基準

| テスト種別 | カバレッジ目標 | 実行タイミング |
|-----------|---------------|----------------|
| 単体テスト | 80%以上 | コミット時 |
| 統合テスト | 主要フロー100% | PR時 |
| E2Eテスト | クリティカルパス | リリース前 |
| セキュリティテスト | OWASP Top 10 | リリース前 |
| 性能テスト | NFR基準達成 | リリース前 |

### 9.2 セキュリティテスト項目

```yaml
security_tests:
  authentication:
    - ブルートフォース攻撃への耐性
    - セッション固定攻撃
    - セッションハイジャック
    - MFAバイパス試行

  authorization:
    - 水平権限昇格（他ユーザーデータアクセス）
    - 垂直権限昇格（管理者機能アクセス）
    - IDOR（Insecure Direct Object Reference）

  injection:
    - SQLインジェクション（該当なし：Neo4j使用）
    - NoSQLインジェクション（Cypher）
    - XSS（Stored/Reflected/DOM）
    - コマンドインジェクション
    - プロンプトインジェクション

  data_protection:
    - 機密データの平文保存
    - 通信の暗号化
    - エラーメッセージからの情報漏洩
```

---

## 10. 運用基準

### 10.1 監視項目

| カテゴリ | 項目 | 閾値 | アラート |
|----------|------|------|----------|
| 可用性 | サービス応答 | 5秒超 | 警告 |
| 可用性 | サービス停止 | 1分超 | 緊急 |
| 性能 | CPU使用率 | 80%超 | 警告 |
| 性能 | メモリ使用率 | 85%超 | 警告 |
| 性能 | ディスク使用率 | 80%超 | 警告 |
| セキュリティ | ログイン失敗 | 10回/分 | 警告 |
| セキュリティ | 権限エラー | 5回/分 | 警告 |

### 10.2 バックアップ基準

```yaml
backup:
  database:
    full:
      frequency: daily
      time: "02:00"
      retention: 30days
    incremental:
      frequency: hourly
      retention: 7days

  files:
    frequency: daily
    retention: 30days

  verification:
    restore_test: monthly
    integrity_check: weekly

  storage:
    primary: local_encrypted
    secondary: offsite_encrypted
    encryption: AES-256-GCM
```

---

## 11. 改訂履歴

| バージョン | 日付 | 変更内容 | 承認者 |
|-----------|------|----------|--------|
| 1.0 | - | 初版作成 | - |
| 2.0 | 2024-12-28 | セキュリティ強化版 | - |

---

**文書終了**
