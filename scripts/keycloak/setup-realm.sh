#!/bin/bash
# Keycloakレルム設定スクリプト
# 生活保護受給者尊厳支援データベース
#
# 使用方法:
#   ./setup-realm.sh [admin_password]
#
# 前提条件:
#   - docker compose -f docker-compose.keycloak.yml up -d が実行済み
#   - Keycloakが起動完了している（ヘルスチェック: http://localhost:8080/health/ready）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REALM_FILE="${SCRIPT_DIR}/livelihood-support-realm.json"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${1:-${KEYCLOAK_ADMIN_PASSWORD:-admin_dev_password}}"

echo "=============================================="
echo "Keycloak レルム設定スクリプト"
echo "=============================================="

# Keycloakの起動確認
echo "Keycloakの起動を確認中..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -sf "${KEYCLOAK_URL}/health/ready" > /dev/null 2>&1; then
        echo "✓ Keycloakが起動しています"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Keycloak起動待機中... (${attempt}/${max_attempts})"
    sleep 5
done

if [ $attempt -eq $max_attempts ]; then
    echo "✗ Keycloakの起動がタイムアウトしました"
    echo "  docker compose -f docker-compose.keycloak.yml logs keycloak で確認してください"
    exit 1
fi

# 管理トークン取得
echo ""
echo "管理者トークンを取得中..."
ACCESS_TOKEN=$(curl -sf -X POST "${KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${KEYCLOAK_ADMIN}" \
    -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=admin-cli" | jq -r '.access_token')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo "✗ 管理者トークンの取得に失敗しました"
    echo "  認証情報を確認してください: KEYCLOAK_ADMIN=${KEYCLOAK_ADMIN}"
    exit 1
fi
echo "✓ 管理者トークンを取得しました"

# 既存レルムの確認
echo ""
echo "既存のレルムを確認中..."
EXISTING_REALM=$(curl -sf -X GET "${KEYCLOAK_URL}/admin/realms/livelihood-support" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" 2>/dev/null || echo "")

if [ -n "$EXISTING_REALM" ] && [ "$EXISTING_REALM" != "null" ]; then
    echo "⚠ livelihood-support レルムは既に存在します"
    read -p "既存のレルムを削除して再作成しますか？ (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "処理を中止しました"
        exit 0
    fi

    echo "既存レルムを削除中..."
    curl -sf -X DELETE "${KEYCLOAK_URL}/admin/realms/livelihood-support" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}"
    echo "✓ 既存レルムを削除しました"
fi

# レルムのインポート
echo ""
echo "レルムをインポート中..."

if [ ! -f "$REALM_FILE" ]; then
    echo "✗ レルム設定ファイルが見つかりません: ${REALM_FILE}"
    exit 1
fi

# クライアントシークレットの生成（環境変数がない場合）
# Base64ではなく、hex形式で生成（sedの特殊文字問題を回避）
API_SECRET="${KEYCLOAK_API_CLIENT_SECRET:-$(openssl rand -hex 32)}"
MCP_SECRET="${KEYCLOAK_MCP_CLIENT_SECRET:-$(openssl rand -hex 32)}"

# テンプレート変数を置換してインポート
# sedの区切り文字を|に変更して特殊文字問題を回避
REALM_JSON=$(cat "$REALM_FILE" | \
    sed "s|\${KEYCLOAK_API_CLIENT_SECRET}|${API_SECRET}|g" | \
    sed "s|\${KEYCLOAK_MCP_CLIENT_SECRET}|${MCP_SECRET}|g")

HTTP_STATUS=$(echo "$REALM_JSON" | curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${KEYCLOAK_URL}/admin/realms" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @-)

if [ "$HTTP_STATUS" == "201" ]; then
    echo "✓ レルムのインポートが完了しました"
else
    echo "✗ レルムのインポートに失敗しました (HTTP ${HTTP_STATUS})"
    exit 1
fi

# 設定情報の出力
echo ""
echo "=============================================="
echo "セットアップ完了"
echo "=============================================="
echo ""
echo "Keycloak管理コンソール: ${KEYCLOAK_URL}/admin"
echo "レルム: livelihood-support"
echo ""
echo "開発用テストユーザー:"
echo "  ケースワーカー: dev-caseworker / DevCaseworker123! (初回ログイン時にパスワード変更必要)"
echo "  スーパーバイザー: dev-supervisor / DevSupervisor123!"
echo "  管理者: dev-admin / DevAdmin123!"
echo ""
echo "クライアント設定:"
echo "  アプリ (livelihood-support-app): Public Client (PKCE)"
echo "  API (livelihood-support-api): Bearer Only"
echo "  MCP (livelihood-support-mcp): Service Account"
echo ""
echo "生成されたクライアントシークレット:"
echo "  KEYCLOAK_API_CLIENT_SECRET=${API_SECRET}"
echo "  KEYCLOAK_MCP_CLIENT_SECRET=${MCP_SECRET}"
echo ""
echo "※ 上記シークレットを .env ファイルに保存してください"
echo ""
