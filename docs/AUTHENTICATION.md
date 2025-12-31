# 認証・認可ガイド

生活保護受給者尊厳支援システムの認証・認可システムについて説明します。

## 概要

本システムでは、Keycloak OIDC認証を使用してユーザー認証を行います。

### 認証方式

- **プロトコル**: OpenID Connect (OIDC)
- **認証サーバー**: Keycloak
- **トークン形式**: JWT (JSON Web Token)
- **署名アルゴリズム**: RS256

## ロールと権限

### ロール定義

| ロール | 説明 |
|--------|------|
| `caseworker` | ケースワーカー。担当ケースの読み書きが可能 |
| `supervisor` | スーパーバイザー。チーム全体の閲覧、監査ログ閲覧が可能 |
| `admin` | 管理者。全権限を持つ |
| `auditor` | 監査者。監査ログ閲覧のみ可能 |

### 権限マッピング

```
caseworker:
  - read:own_cases    # 担当ケースの読み取り
  - write:own_cases   # 担当ケースの書き込み

supervisor:
  - read:own_cases    # 担当ケースの読み取り
  - write:own_cases   # 担当ケースの書き込み
  - read:team_cases   # チームケースの読み取り
  - view:audit_logs   # 監査ログの閲覧

admin:
  - system:admin      # 全権限（全ての操作が可能）

auditor:
  - view:audit_logs   # 監査ログの閲覧
```

## API認証

### 認証ヘッダー

すべての保護されたAPIエンドポイントには、Authorizationヘッダーが必要です。

```http
Authorization: Bearer <access_token>
```

### トークン取得

Keycloakからトークンを取得するには：

```bash
curl -X POST \
  http://localhost:8080/realms/livelihood-support/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=password' \
  -d 'client_id=livelihood-support-app' \
  -d 'username=YOUR_USERNAME' \
  -d 'password=YOUR_PASSWORD'
```

### レスポンス例

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR...",
  "expires_in": 1800,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR...",
  "token_type": "Bearer"
}
```

## 環境変数設定

### Keycloak設定

```bash
# Keycloakサーバー
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=livelihood-support
KEYCLOAK_CLIENT_ID=livelihood-support-app

# 開発環境設定
DEBUG=true           # デバッグモード（署名検証をスキップ）
AUTH_SKIP=false      # 認証スキップ（開発環境のみ）
```

### 本番環境設定

```bash
DEBUG=false          # 署名検証を有効化
AUTH_SKIP=false      # 認証を有効化
```

## Streamlit認証

Streamlitアプリケーションでは、PKCE（Proof Key for Code Exchange）対応のOAuth 2.0認証フローを使用します。

### 認証フロー

1. ユーザーがログインボタンをクリック
2. Keycloakの認証ページにリダイレクト
3. ユーザーが認証情報を入力
4. 認証成功後、アプリにリダイレクト
5. 認証コードをトークンに交換
6. セッションにトークンを保存

### 使用例

```python
from lib.auth import require_authentication, get_current_user, has_role

# 認証を要求
if not require_authentication():
    st.stop()

# ユーザー情報を取得
user = get_current_user()
st.write(f"ログイン中: {user['name']}")

# ロールチェック
if has_role("supervisor"):
    st.write("スーパーバイザー機能が利用可能です")
```

## FastAPI認証

### 依存性注入

```python
from fastapi import Depends
from api.dependencies import (
    get_current_user,
    get_current_user_or_mock,
    require_permission,
    require_role,
    require_any_role,
    User,
    Permission,
)

# 認証必須エンドポイント
@app.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"user": user.username}

# 開発環境でモックユーザーを使用
@app.get("/dev-friendly")
async def dev_route(user: User = Depends(get_current_user_or_mock)):
    return {"user": user.username}

# 特定の権限を要求
@app.get("/admin-only")
async def admin_route(
    user: User = Depends(require_permission(Permission.SYSTEM_ADMIN))
):
    return {"message": "Admin access"}

# 特定のロールを要求
@app.get("/supervisor-only")
async def supervisor_route(
    user: User = Depends(require_role("supervisor"))
):
    return {"message": "Supervisor access"}

# いずれかのロールを要求
@app.get("/staff-only")
async def staff_route(
    user: User = Depends(require_any_role(["caseworker", "supervisor"]))
):
    return {"message": "Staff access"}
```

## JWKSキャッシュ

本番環境では、Keycloakの公開鍵（JWKS）を使用してJWTの署名を検証します。

### キャッシュ動作

- キャッシュ期間: 1時間
- 自動更新: キャッシュ期限切れ時に自動取得
- フォールバック: 取得失敗時は既存キャッシュを使用

### 手動キャッシュクリア

```python
from api.dependencies import _jwks_cache

# キャッシュをクリア
_jwks_cache.clear()
```

## エラーレスポンス

### 認証エラー (401)

```json
{
  "detail": "認証が必要です",
  "headers": {"WWW-Authenticate": "Bearer"}
}
```

### 権限エラー (403)

```json
{
  "detail": "必要なロール: supervisor"
}
```

### トークン期限切れ (401)

```json
{
  "detail": "トークンの有効期限が切れています"
}
```

## セキュリティ考慮事項

1. **HTTPS必須**: 本番環境ではHTTPSを使用
2. **トークン管理**: アクセストークンは安全に保管
3. **リフレッシュトークン**: 長期セッションにはリフレッシュトークンを使用
4. **ログアウト**: セッション終了時にトークンを無効化
5. **監査ログ**: すべての認証イベントを記録

## トラブルシューティング

### 認証サーバーに接続できない

```
HTTPException: 認証サーバーに接続できません
```

→ Keycloakが起動しているか確認

### トークンのaudienceが不正

```
HTTPException: トークンのaudienceが不正です
```

→ KEYCLOAK_CLIENT_ID が正しいか確認

### 公開鍵が見つからない

```
HTTPException: 公開鍵が見つかりません
```

→ JWKSエンドポイントが正しいか確認
→ トークンのkidがJWKSに存在するか確認

## 開発環境でのテスト

開発環境では、DEBUG=true を設定することで署名検証をスキップできます。

```bash
DEBUG=true uv run uvicorn api.main:app --reload
```

認証なしでAPIをテストする場合は、モックユーザーが自動的に使用されます。
