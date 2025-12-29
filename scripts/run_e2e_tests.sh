#!/bin/bash
# E2Eテスト実行スクリプト
# 必要なサービスを起動してテストを実行し、終了後にクリーンアップ

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# クリーンアップ関数
cleanup() {
    log_info "クリーンアップ中..."

    # バックグラウンドプロセスを停止
    if [ -n "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    if [ -n "$STREAMLIT_PID" ]; then
        kill $STREAMLIT_PID 2>/dev/null || true
    fi

    log_info "クリーンアップ完了"
}

# シグナルハンドラ
trap cleanup EXIT

# サービス起動確認
check_service() {
    local host=$1
    local port=$2
    local timeout=${3:-30}
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

# ヘルプ表示
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --api-only      APIテストのみ実行"
    echo "  --streamlit-only Streamlitテストのみ実行"
    echo "  --no-start      サービスを起動せずにテスト実行"
    echo "  --verbose       詳細出力"
    echo "  -h, --help      このヘルプを表示"
    echo ""
    echo "Examples:"
    echo "  $0                  # 全E2Eテストを実行"
    echo "  $0 --api-only       # APIテストのみ"
    echo "  $0 --no-start       # 既存サービスを使用"
}

# オプション解析
API_ONLY=false
STREAMLIT_ONLY=false
NO_START=false
VERBOSE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-only)
            API_ONLY=true
            shift
            ;;
        --streamlit-only)
            STREAMLIT_ONLY=true
            shift
            ;;
        --no-start)
            NO_START=true
            shift
            ;;
        --verbose)
            VERBOSE="-v"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "不明なオプション: $1"
            show_help
            exit 1
            ;;
    esac
done

log_info "E2Eテスト開始"

# Playwrightブラウザ確認
if ! uv run playwright install --dry-run chromium >/dev/null 2>&1; then
    log_warn "Playwrightブラウザをインストール中..."
    uv run playwright install chromium
fi

# Neo4j確認
if ! check_service localhost 7688 5; then
    log_error "Neo4jが起動していません。docker compose up -d を実行してください"
    exit 1
fi
log_info "Neo4j: OK"

# サービス起動（必要な場合）
if [ "$NO_START" = false ]; then
    # API起動
    if ! check_service localhost 8000 1; then
        log_info "FastAPI を起動中..."
        uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 &
        API_PID=$!

        if ! check_service localhost 8000 30; then
            log_error "FastAPIの起動に失敗しました"
            exit 1
        fi
        log_info "FastAPI: 起動完了"
    else
        log_info "FastAPI: 既に起動中"
    fi

    # Streamlit起動（必要な場合）
    if [ "$API_ONLY" = false ] && [ "$STREAMLIT_ONLY" = true ]; then
        if ! check_service localhost 8501 1; then
            log_info "Streamlit を起動中..."
            uv run streamlit run app_case_record.py --server.headless true &
            STREAMLIT_PID=$!

            if ! check_service localhost 8501 30; then
                log_error "Streamlitの起動に失敗しました"
                exit 1
            fi
            log_info "Streamlit: 起動完了"
        else
            log_info "Streamlit: 既に起動中"
        fi
    fi
fi

# テスト実行
log_info "テスト実行中..."

TEST_ARGS="tests/e2e/ $VERBOSE"

if [ "$API_ONLY" = true ]; then
    TEST_ARGS="tests/e2e/test_api_e2e.py $VERBOSE"
elif [ "$STREAMLIT_ONLY" = true ]; then
    TEST_ARGS="tests/e2e/test_streamlit_e2e.py $VERBOSE"
fi

uv run pytest $TEST_ARGS --tb=short

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    log_info "テスト完了: 全テスト成功"
else
    log_error "テスト完了: 一部テスト失敗"
fi

exit $TEST_EXIT_CODE
