#!/bin/bash
# =============================================================================
# 生活保護受給者尊厳支援データベース - 復元スクリプト
# =============================================================================
#
# 使用方法:
#   ./scripts/restore.sh                           # 最新のフルバックアップから復元
#   ./scripts/restore.sh full_backup_20241228.tar.gz  # 指定ファイルから復元
#
# ⚠️ 警告: 現在のデータは上書きされます！
# =============================================================================

set -e

# 設定
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/neo4j_backup"
DATA_DIR="${PROJECT_DIR}/neo4j_data"
CONTAINER_NAME="livelihood-support-neo4j"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=============================================="
echo "生活保護受給者尊厳支援DB - 復元"
echo "=============================================="
echo "日時: $(date)"
echo ""

# 引数チェック
if [ -n "$1" ]; then
    BACKUP_FILE="${BACKUP_DIR}/$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        BACKUP_FILE="$1"  # フルパスで指定された場合
    fi
else
    # 最新のフルバックアップを探す
    BACKUP_FILE=$(ls -t "${BACKUP_DIR}"/full_backup_*.tar.gz 2>/dev/null | head -1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    log_error "バックアップファイルが見つかりません"
    echo ""
    echo "利用可能なバックアップ:"
    ls -lh "${BACKUP_DIR}"/*.tar.gz 2>/dev/null || echo "  (なし)"
    echo ""
    echo "使用方法:"
    echo "  ./scripts/restore.sh                           # 最新から復元"
    echo "  ./scripts/restore.sh full_backup_YYYYMMDD.tar.gz  # 指定ファイル"
    exit 1
fi

echo "復元元ファイル: ${BACKUP_FILE}"
echo ""

# 確認
log_warn "⚠️  警告: 現在のデータは完全に上書きされます！"
echo ""
read -p "本当に復元しますか? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "復元をキャンセルしました"
    exit 0
fi

# コンテナ停止
log_info "コンテナを停止中..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true
sleep 3

# 現在のデータをバックアップ（念のため）
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SAFETY_BACKUP="${BACKUP_DIR}/pre_restore_${TIMESTAMP}.tar.gz"
log_info "現在のデータを安全のためバックアップ中..."
tar -czf "${SAFETY_BACKUP}" -C "${PROJECT_DIR}" neo4j_data 2>/dev/null || true

# データディレクトリを削除
log_info "既存データを削除中..."
rm -rf "${DATA_DIR}"

# 復元
log_info "バックアップから復元中..."
tar -xzf "${BACKUP_FILE}" -C "${PROJECT_DIR}"

# コンテナ起動
log_info "コンテナを起動中..."
cd "${PROJECT_DIR}"
docker compose up -d

# 起動待ち
log_info "Neo4jの起動を待機中..."
sleep 10

# 接続テスト
log_info "接続テスト中..."
for i in {1..10}; do
    if docker exec ${CONTAINER_NAME} cypher-shell -u neo4j -p password "RETURN 1" >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

# 復元確認
log_info "データ確認中..."
PATTERN_COUNT=$(docker exec ${CONTAINER_NAME} cypher-shell -u neo4j -p password \
    "MATCH (cp:CasePattern) RETURN count(cp) as c" 2>/dev/null | grep -E "^[0-9]+" || echo "0")

echo ""
echo "=============================================="
log_info "復元が完了しました!"
echo "=============================================="
echo ""
echo "  復元元: ${BACKUP_FILE}"
echo "  安全バックアップ: ${SAFETY_BACKUP}"
echo "  CasePattern数: ${PATTERN_COUNT}"
echo ""
echo "Neo4j Browser: http://localhost:7475"
