#!/bin/bash
# =============================================================================
# Keycloak ユーザー一括登録スクリプト
# =============================================================================
# Usage: ./scripts/import_users.sh <csv_file>
#
# CSVファイル形式:
#   username,email,firstname,lastname,role,group
#   yamada.taro,yamada@example.lg.jp,太郎,山田,caseworker,/福祉課/第1係
#
# 必須列: username, email, firstname, lastname, role
# オプション列: group
# =============================================================================

set -euo pipefail

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 設定
REALM="${KEYCLOAK_REALM:-livelihood-support}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin_dev_password}"
DEFAULT_PASSWORD="${DEFAULT_PASSWORD:-ChangeMe123!}"
KCADM="/opt/keycloak/bin/kcadm.sh"

# Docker内で実行するかどうか
USE_DOCKER="${USE_DOCKER:-true}"
CONTAINER_NAME="${KEYCLOAK_CONTAINER:-livelihood-keycloak}"

# カウンター
SUCCESS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# =============================================================================
# ヘルプ表示
# =============================================================================
show_help() {
    cat << EOF
Keycloak ユーザー一括登録スクリプト

Usage:
    $0 <csv_file> [options]

Options:
    -h, --help          このヘルプを表示
    -d, --dry-run       実際には登録せず、処理内容を表示
    -p, --password PWD  初期パスワード (デフォルト: ${DEFAULT_PASSWORD})
    --no-docker         Dockerを使用せずローカルで実行

CSVファイル形式:
    username,email,firstname,lastname,role,group

    - username: ログインID（必須）
    - email: メールアドレス（必須）
    - firstname: 名（必須）
    - lastname: 姓（必須）
    - role: ロール名（必須）caseworker/supervisor/admin/auditor
    - group: グループパス（オプション）例: /福祉課/第1係

例:
    $0 users.csv
    $0 users.csv --dry-run
    $0 users.csv -p "SecurePassword123!"

環境変数:
    KEYCLOAK_URL            Keycloak URL (デフォルト: http://localhost:8080)
    KEYCLOAK_REALM          Realm名 (デフォルト: livelihood-support)
    KEYCLOAK_ADMIN          管理者ユーザー名 (デフォルト: admin)
    KEYCLOAK_ADMIN_PASSWORD 管理者パスワード
    DEFAULT_PASSWORD        初期パスワード (デフォルト: ChangeMe123!)
    KEYCLOAK_CONTAINER      Dockerコンテナ名 (デフォルト: livelihood-keycloak)

EOF
}

# =============================================================================
# kcadmコマンド実行
# =============================================================================
run_kcadm() {
    if [ "$USE_DOCKER" = "true" ]; then
        docker exec "$CONTAINER_NAME" "$KCADM" "$@"
    else
        "$KCADM" "$@"
    fi
}

# =============================================================================
# Keycloakにログイン
# =============================================================================
keycloak_login() {
    log_info "Keycloakに管理者としてログイン中..."

    if ! run_kcadm config credentials \
        --server "$KEYCLOAK_URL" \
        --realm master \
        --user "$KEYCLOAK_ADMIN" \
        --password "$KEYCLOAK_ADMIN_PASSWORD" 2>/dev/null; then
        log_error "Keycloakへのログインに失敗しました"
        log_error "環境変数 KEYCLOAK_ADMIN_PASSWORD を確認してください"
        exit 1
    fi

    log_success "Keycloakにログインしました"
}

# =============================================================================
# ユーザーが存在するかチェック
# =============================================================================
user_exists() {
    local username="$1"
    local result

    result=$(run_kcadm get users -r "$REALM" -q username="$username" 2>/dev/null)

    if echo "$result" | grep -q "\"username\" : \"$username\""; then
        return 0  # exists
    else
        return 1  # not exists
    fi
}

# =============================================================================
# ユーザー作成
# =============================================================================
create_user() {
    local username="$1"
    local email="$2"
    local firstname="$3"
    local lastname="$4"
    local role="$5"
    local group="${6:-}"

    log_info "ユーザー作成中: $username ($lastname $firstname)"

    # ユーザーが既に存在するかチェック
    if user_exists "$username"; then
        log_warn "ユーザー '$username' は既に存在します。スキップします。"
        ((SKIP_COUNT++))
        return 0
    fi

    # ドライランモード
    if [ "${DRY_RUN:-false}" = "true" ]; then
        log_info "[DRY-RUN] 作成予定: $username, ロール: $role, グループ: ${group:-なし}"
        return 0
    fi

    # ユーザー作成
    if ! run_kcadm create users -r "$REALM" \
        -s username="$username" \
        -s email="$email" \
        -s firstName="$firstname" \
        -s lastName="$lastname" \
        -s enabled=true \
        -s emailVerified=true 2>/dev/null; then
        log_error "ユーザー '$username' の作成に失敗しました"
        ((FAIL_COUNT++))
        return 1
    fi

    # パスワード設定（初回ログイン時に変更を強制）
    if ! run_kcadm set-password -r "$REALM" \
        --username "$username" \
        --new-password "$DEFAULT_PASSWORD" \
        --temporary 2>/dev/null; then
        log_error "ユーザー '$username' のパスワード設定に失敗しました"
        ((FAIL_COUNT++))
        return 1
    fi

    # ロール割り当て
    if ! run_kcadm add-roles -r "$REALM" \
        --uusername "$username" \
        --rolename "$role" 2>/dev/null; then
        log_warn "ユーザー '$username' へのロール '$role' の割り当てに失敗しました"
    fi

    # グループ割り当て（指定がある場合）
    if [ -n "$group" ]; then
        # グループIDを取得
        local group_id
        group_id=$(run_kcadm get groups -r "$REALM" 2>/dev/null | \
            grep -B2 "\"path\" : \"$group\"" | \
            grep '"id"' | \
            sed 's/.*: "\(.*\)".*/\1/' | head -1)

        if [ -n "$group_id" ]; then
            local user_id
            user_id=$(run_kcadm get users -r "$REALM" -q username="$username" 2>/dev/null | \
                grep '"id"' | head -1 | sed 's/.*: "\(.*\)".*/\1/')

            if [ -n "$user_id" ]; then
                run_kcadm update "users/$user_id/groups/$group_id" -r "$REALM" -s realm="$REALM" -n 2>/dev/null || \
                    log_warn "グループ '$group' への割り当てに失敗しました"
            fi
        else
            log_warn "グループ '$group' が見つかりません"
        fi
    fi

    log_success "ユーザー '$username' を作成しました (ロール: $role)"
    ((SUCCESS_COUNT++))
    return 0
}

# =============================================================================
# CSVファイル処理
# =============================================================================
process_csv() {
    local csv_file="$1"
    local line_num=0

    log_info "CSVファイルを処理中: $csv_file"
    echo ""

    while IFS=, read -r username email firstname lastname role group; do
        ((line_num++))

        # ヘッダー行をスキップ
        if [ $line_num -eq 1 ]; then
            if [ "$username" = "username" ]; then
                continue
            fi
        fi

        # 空行をスキップ
        if [ -z "$username" ]; then
            continue
        fi

        # 前後の空白とCRを除去
        username=$(echo "$username" | tr -d '\r' | xargs)
        email=$(echo "$email" | tr -d '\r' | xargs)
        firstname=$(echo "$firstname" | tr -d '\r' | xargs)
        lastname=$(echo "$lastname" | tr -d '\r' | xargs)
        role=$(echo "$role" | tr -d '\r' | xargs)
        group=$(echo "$group" | tr -d '\r' | xargs)

        # 必須フィールドのチェック
        if [ -z "$username" ] || [ -z "$email" ] || [ -z "$firstname" ] || [ -z "$lastname" ] || [ -z "$role" ]; then
            log_error "行 $line_num: 必須フィールドが不足しています"
            ((FAIL_COUNT++))
            continue
        fi

        # ロールの検証
        case "$role" in
            caseworker|supervisor|admin|auditor)
                ;;
            *)
                log_error "行 $line_num: 無効なロール '$role' (有効値: caseworker, supervisor, admin, auditor)"
                ((FAIL_COUNT++))
                continue
                ;;
        esac

        # ユーザー作成
        create_user "$username" "$email" "$firstname" "$lastname" "$role" "$group"

    done < "$csv_file"
}

# =============================================================================
# メイン処理
# =============================================================================
main() {
    local csv_file=""
    DRY_RUN="false"

    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--dry-run)
                DRY_RUN="true"
                shift
                ;;
            -p|--password)
                DEFAULT_PASSWORD="$2"
                shift 2
                ;;
            --no-docker)
                USE_DOCKER="false"
                shift
                ;;
            -*)
                log_error "不明なオプション: $1"
                show_help
                exit 1
                ;;
            *)
                csv_file="$1"
                shift
                ;;
        esac
    done

    # CSVファイルのチェック
    if [ -z "$csv_file" ]; then
        log_error "CSVファイルを指定してください"
        show_help
        exit 1
    fi

    if [ ! -f "$csv_file" ]; then
        log_error "CSVファイルが見つかりません: $csv_file"
        exit 1
    fi

    # ヘッダー表示
    echo ""
    echo "=============================================="
    echo "  Keycloak ユーザー一括登録"
    echo "=============================================="
    echo ""
    log_info "Realm: $REALM"
    log_info "Keycloak URL: $KEYCLOAK_URL"
    log_info "CSVファイル: $csv_file"
    log_info "初期パスワード: $DEFAULT_PASSWORD"
    log_info "ドライラン: $DRY_RUN"
    echo ""

    # Dockerコンテナの確認
    if [ "$USE_DOCKER" = "true" ]; then
        if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_error "Keycloakコンテナ '$CONTAINER_NAME' が起動していません"
            log_info "起動コマンド: docker compose -f docker-compose.keycloak.yml up -d"
            exit 1
        fi
    fi

    # Keycloakにログイン
    keycloak_login
    echo ""

    # CSVファイル処理
    process_csv "$csv_file"

    # 結果表示
    echo ""
    echo "=============================================="
    echo "  処理完了"
    echo "=============================================="
    log_success "成功: $SUCCESS_COUNT 件"
    if [ $SKIP_COUNT -gt 0 ]; then
        log_warn "スキップ: $SKIP_COUNT 件（既存ユーザー）"
    fi
    if [ $FAIL_COUNT -gt 0 ]; then
        log_error "失敗: $FAIL_COUNT 件"
    fi
    echo ""

    if [ $FAIL_COUNT -gt 0 ]; then
        exit 1
    fi
}

# スクリプト実行
main "$@"
