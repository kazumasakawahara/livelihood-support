#!/bin/bash
# ==============================================================================
# デプロイスクリプト - 生活保護受給者尊厳支援データベース
# ==============================================================================
set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ログ関数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ヘルプ
show_help() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start       本番環境を起動"
    echo "  stop        本番環境を停止"
    echo "  restart     本番環境を再起動"
    echo "  build       Dockerイメージをビルド"
    echo "  logs        ログを表示"
    echo "  status      サービス状態を確認"
    echo "  backup      Neo4jバックアップを作成"
    echo "  health      ヘルスチェックを実行"
    echo ""
    echo "Options:"
    echo "  --dev       開発モードで起動"
    echo "  -h, --help  ヘルプを表示"
}

# 環境変数チェック
check_env() {
    if [ ! -f .env ]; then
        log_error ".env ファイルが見つかりません"
        log_info ".env.example を .env にコピーして設定してください"
        exit 1
    fi

    # 必須変数チェック
    source .env
    if [ -z "$NEO4J_PASSWORD" ] || [ "$NEO4J_PASSWORD" = "your_secure_password_here" ]; then
        log_error "NEO4J_PASSWORD が設定されていません"
        exit 1
    fi
}

# Dockerイメージをビルド
build() {
    log_info "Dockerイメージをビルド中..."
    docker compose -f docker-compose.prod.yml build --no-cache
    log_info "ビルド完了"
}

# 本番環境を起動
start() {
    check_env
    log_info "本番環境を起動中..."
    docker compose -f docker-compose.prod.yml up -d
    log_info "起動完了"
    log_info "ステータスを確認中..."
    sleep 5
    status
}

# 本番環境を停止
stop() {
    log_info "本番環境を停止中..."
    docker compose -f docker-compose.prod.yml down
    log_info "停止完了"
}

# 本番環境を再起動
restart() {
    stop
    start
}

# ログを表示
logs() {
    docker compose -f docker-compose.prod.yml logs -f "$@"
}

# サービス状態を確認
status() {
    echo ""
    log_info "=== サービス状態 ==="
    docker compose -f docker-compose.prod.yml ps
    echo ""
}

# Neo4jバックアップ
backup() {
    log_info "Neo4jバックアップを作成中..."
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="./backups/${BACKUP_DATE}"
    mkdir -p "$BACKUP_DIR"

    # Neo4j停止
    docker compose -f docker-compose.prod.yml stop neo4j

    # データディレクトリをコピー
    cp -r ./neo4j_data "$BACKUP_DIR/"

    # Neo4j再起動
    docker compose -f docker-compose.prod.yml start neo4j

    log_info "バックアップ完了: $BACKUP_DIR"
}

# ヘルスチェック
health() {
    echo ""
    log_info "=== ヘルスチェック ==="

    # Neo4j
    echo -n "Neo4j: "
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}NG${NC}"
    fi

    # API
    echo -n "API: "
    if curl -s http://localhost/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}OK${NC} (direct)"
        else
            echo -e "${RED}NG${NC}"
        fi
    fi

    # Streamlit
    echo -n "Streamlit: "
    if curl -s http://localhost/_stcore/health > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            echo -e "${GREEN}OK${NC} (direct)"
        else
            echo -e "${RED}NG${NC}"
        fi
    fi

    # Nginx
    echo -n "Nginx: "
    if curl -s http://localhost/health > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}NG${NC}"
    fi

    echo ""
}

# メイン処理
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    build)
        build
        ;;
    logs)
        shift
        logs "$@"
        ;;
    status)
        status
        ;;
    backup)
        backup
        ;;
    health)
        health
        ;;
    -h|--help)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
