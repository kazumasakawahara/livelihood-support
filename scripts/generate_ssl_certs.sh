#!/bin/bash
# ==============================================================================
# 開発環境用SSL証明書生成スクリプト
# TECHNICAL_STANDARDS.md Section 4.2 準拠
# ==============================================================================

set -e

# 設定
SSL_DIR="${1:-./nginx/ssl}"
DOMAIN="${2:-localhost}"
DAYS="${3:-365}"

# 色定義
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

# ディレクトリ作成
mkdir -p "$SSL_DIR"

log_info "開発環境用SSL証明書を生成します"
log_info "ディレクトリ: $SSL_DIR"
log_info "ドメイン: $DOMAIN"
log_info "有効期限: ${DAYS}日"

# 既存の証明書があるか確認
if [ -f "$SSL_DIR/privkey.pem" ] || [ -f "$SSL_DIR/fullchain.pem" ]; then
    log_warn "既存の証明書が見つかりました"
    read -p "上書きしますか？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "中止しました"
        exit 0
    fi
fi

# OpenSSL設定ファイル作成
CONFIG_FILE="$SSL_DIR/openssl.cnf"
cat > "$CONFIG_FILE" << EOF
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req
x509_extensions = v3_ca

[dn]
C = JP
ST = Tokyo
L = Shinjuku
O = Development
OU = Livelihood Support System
CN = $DOMAIN

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[v3_ca]
basicConstraints = critical, CA:TRUE
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
subjectAltName = @alt_names

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = *.$DOMAIN
DNS.3 = localhost
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

log_info "秘密鍵を生成中..."
openssl genrsa -out "$SSL_DIR/privkey.pem" 4096

log_info "自己署名証明書を生成中..."
openssl req -new -x509 \
    -key "$SSL_DIR/privkey.pem" \
    -out "$SSL_DIR/fullchain.pem" \
    -days "$DAYS" \
    -config "$CONFIG_FILE"

# 証明書情報を表示
log_info "証明書情報:"
openssl x509 -in "$SSL_DIR/fullchain.pem" -noout -subject -dates | sed 's/^/  /'

# DH パラメータ生成（オプション）
if [ ! -f "$SSL_DIR/dhparam.pem" ]; then
    log_info "DHパラメータを生成中（時間がかかる場合があります）..."
    openssl dhparam -out "$SSL_DIR/dhparam.pem" 2048
fi

# パーミッション設定
chmod 600 "$SSL_DIR/privkey.pem"
chmod 644 "$SSL_DIR/fullchain.pem"
chmod 644 "$SSL_DIR/dhparam.pem" 2>/dev/null || true

# 設定ファイル削除
rm -f "$CONFIG_FILE"

log_info "SSL証明書の生成が完了しました"
echo ""
echo "生成されたファイル:"
ls -la "$SSL_DIR"/*.pem
echo ""
log_warn "注意: これは開発環境用の自己署名証明書です"
log_warn "本番環境では Let's Encrypt などの信頼された証明書を使用してください"
echo ""
log_info "次のステップ:"
echo "  1. nginx/conf.d/ssl.conf.example を ssl.conf にコピー"
echo "  2. ドメイン名を your-domain.example.com から $DOMAIN に変更"
echo "  3. docker compose up -d で再起動"
