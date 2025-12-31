#!/bin/bash
# =============================================================================
# 生活保護受給者尊厳支援データベース - 定期バックアップ設定
# =============================================================================
#
# このスクリプトは、macOSのlaunchdを使って毎日自動バックアップを設定します。
#
# 使用方法:
#   ./scripts/setup_scheduled_backup.sh install   # 自動バックアップを有効化
#   ./scripts/setup_scheduled_backup.sh uninstall # 自動バックアップを無効化
#   ./scripts/setup_scheduled_backup.sh status    # 状態確認
#
# =============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_NAME="com.livelihood-support.backup"
PLIST_FILE="${HOME}/Library/LaunchAgents/${PLIST_NAME}.plist"
BACKUP_SCRIPT="${PROJECT_DIR}/scripts/backup.sh"
LOG_DIR="${PROJECT_DIR}/neo4j_logs"

# 色付き出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

install_schedule() {
    echo "=============================================="
    echo "定期バックアップの設定"
    echo "=============================================="
    
    # LaunchAgentsディレクトリ作成
    mkdir -p "${HOME}/Library/LaunchAgents"
    mkdir -p "${LOG_DIR}"
    
    # plistファイル作成
    cat > "${PLIST_FILE}" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>${BACKUP_SCRIPT}</string>
        <string>--full</string>
    </array>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/backup_stdout.log</string>
    
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/backup_stderr.log</string>
    
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
EOF
    
    # 権限設定
    chmod +x "${BACKUP_SCRIPT}"
    
    # launchdに登録
    launchctl unload "${PLIST_FILE}" 2>/dev/null || true
    launchctl load "${PLIST_FILE}"
    
    log_info "定期バックアップを設定しました"
    echo ""
    echo "  スケジュール: 毎日 午前3時"
    echo "  バックアップ先: ${PROJECT_DIR}/neo4j_backup/"
    echo "  ログ: ${LOG_DIR}/backup_*.log"
    echo ""
    echo "設定ファイル: ${PLIST_FILE}"
}

uninstall_schedule() {
    echo "=============================================="
    echo "定期バックアップの解除"
    echo "=============================================="
    
    if [ -f "${PLIST_FILE}" ]; then
        launchctl unload "${PLIST_FILE}" 2>/dev/null || true
        rm -f "${PLIST_FILE}"
        log_info "定期バックアップを解除しました"
    else
        log_warn "設定ファイルが見つかりません"
    fi
}

show_status() {
    echo "=============================================="
    echo "定期バックアップの状態"
    echo "=============================================="
    
    if [ -f "${PLIST_FILE}" ]; then
        echo "設定ファイル: ${PLIST_FILE}"
        echo ""
        
        # launchdの状態確認
        if launchctl list | grep -q "${PLIST_NAME}"; then
            log_info "状態: 有効（次回実行: 午前3時）"
        else
            log_warn "状態: 設定ファイルはあるが無効"
            echo "  有効化: launchctl load ${PLIST_FILE}"
        fi
        
        echo ""
        echo "最新のバックアップ:"
        ls -lht "${PROJECT_DIR}/neo4j_backup/"*.tar.gz 2>/dev/null | head -3 || echo "  (なし)"
    else
        log_warn "定期バックアップは設定されていません"
        echo ""
        echo "設定方法:"
        echo "  ./scripts/setup_scheduled_backup.sh install"
    fi
}

# メイン処理
case "$1" in
    install)
        install_schedule
        ;;
    uninstall)
        uninstall_schedule
        ;;
    status)
        show_status
        ;;
    *)
        echo "使用方法:"
        echo "  $0 install   - 自動バックアップを有効化（毎日午前3時）"
        echo "  $0 uninstall - 自動バックアップを無効化"
        echo "  $0 status    - 状態確認"
        ;;
esac
