# サーバー構築手順書

Ubuntu Server 22.04 LTS を対象とした、本番環境サーバーの構築手順を説明します。

## 目次

1. [事前準備](#事前準備)
2. [OS初期設定](#os初期設定)
3. [Docker環境構築](#docker環境構築)
4. [SSL/TLS証明書設定](#ssltls証明書設定)
5. [アプリケーションデプロイ](#アプリケーションデプロイ)
6. [Keycloak設定](#keycloak設定)
7. [監視環境構築](#監視環境構築)
8. [バックアップ設定](#バックアップ設定)
9. [セキュリティ設定](#セキュリティ設定)
10. [動作確認](#動作確認)

---

## 事前準備

### 必要な情報

構築前に以下の情報を準備してください。

| 項目 | 例 | 準備状況 |
|------|------|---------|
| サーバーIPアドレス | 10.2.0.21 | [ ] |
| ホスト名（FQDN） | livelihood.city.example.lg.jp | [ ] |
| SSL証明書 | 庁内CA発行 or Let's Encrypt | [ ] |
| Neo4j管理者パスワード | 32文字以上の強力なパスワード | [ ] |
| Keycloak管理者パスワード | 32文字以上の強力なパスワード | [ ] |
| Gemini APIキー（任意） | AITURAFj... | [ ] |
| バックアップ保存先 | /backup または NFS | [ ] |

### サーバー要件

| 項目 | 最小要件 | 推奨要件 |
|------|---------|---------|
| CPU | 4コア | 8コア |
| メモリ | 16GB | 32GB |
| ストレージ | 100GB SSD | 500GB NVMe SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| ネットワーク | 1Gbps | 1Gbps x 2 |

---

## OS初期設定

### 1. システム更新

```bash
# パッケージリスト更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージインストール
sudo apt install -y \
  curl \
  wget \
  git \
  vim \
  htop \
  net-tools \
  gnupg \
  ca-certificates \
  lsb-release \
  software-properties-common \
  ufw \
  fail2ban
```

### 2. ホスト名設定

```bash
# ホスト名設定
sudo hostnamectl set-hostname livelihood-server

# /etc/hosts 編集
sudo vim /etc/hosts
```

以下を追加:
```
127.0.0.1   livelihood-server
10.2.0.21   livelihood.city.example.lg.jp livelihood-server
```

### 3. タイムゾーン設定

```bash
# タイムゾーン設定
sudo timedatectl set-timezone Asia/Tokyo

# NTP同期確認
timedatectl status
```

### 4. ユーザー作成

```bash
# アプリケーション用ユーザー作成
sudo useradd -m -s /bin/bash livelihood
sudo usermod -aG sudo livelihood
sudo usermod -aG docker livelihood

# パスワード設定
sudo passwd livelihood
```

### 5. ファイアウォール設定

```bash
# UFW有効化
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 必要なポートのみ開放
sudo ufw allow ssh
sudo ufw allow 80/tcp    # HTTP（リダイレクト用）
sudo ufw allow 443/tcp   # HTTPS

# UFW有効化
sudo ufw enable

# 状態確認
sudo ufw status verbose
```

### 6. SSH強化

```bash
# SSH設定ファイル編集
sudo vim /etc/ssh/sshd_config
```

以下を設定:
```
# ルートログイン禁止
PermitRootLogin no

# パスワード認証禁止（公開鍵のみ）
PasswordAuthentication no

# 空パスワード禁止
PermitEmptyPasswords no

# 最大認証試行回数
MaxAuthTries 3

# クライアントアライブ
ClientAliveInterval 300
ClientAliveCountMax 2
```

SSH再起動:
```bash
sudo systemctl restart sshd
```

---

## Docker環境構築

### 1. Docker インストール

```bash
# GPGキー追加
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# リポジトリ追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# インストール
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# サービス有効化
sudo systemctl enable docker
sudo systemctl start docker

# 動作確認
docker --version
docker compose version
```

### 2. Docker設定最適化

```bash
# Docker デーモン設定
sudo vim /etc/docker/daemon.json
```

以下を設定:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "5"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
```

Docker再起動:
```bash
sudo systemctl restart docker
```

### 3. ディレクトリ構成作成

```bash
# アプリケーションディレクトリ
sudo mkdir -p /opt/livelihood-support
sudo chown livelihood:livelihood /opt/livelihood-support

# ログディレクトリ
sudo mkdir -p /var/log/livelihood
sudo chown livelihood:livelihood /var/log/livelihood

# バックアップディレクトリ
sudo mkdir -p /backup/{neo4j,keycloak,logs}
sudo chown -R livelihood:livelihood /backup

# SSL証明書ディレクトリ
sudo mkdir -p /etc/ssl/livelihood
sudo chmod 700 /etc/ssl/livelihood
```

---

## SSL/TLS証明書設定

### オプションA: 庁内CA証明書

```bash
# 証明書配置
sudo cp /path/to/certificate.crt /etc/ssl/livelihood/server.crt
sudo cp /path/to/private.key /etc/ssl/livelihood/server.key
sudo cp /path/to/ca-chain.crt /etc/ssl/livelihood/ca-chain.crt

# パーミッション設定
sudo chmod 644 /etc/ssl/livelihood/server.crt
sudo chmod 600 /etc/ssl/livelihood/server.key
sudo chmod 644 /etc/ssl/livelihood/ca-chain.crt
```

### オプションB: Let's Encrypt（インターネット接続環境用）

```bash
# Certbot インストール
sudo apt install -y certbot

# 証明書取得
sudo certbot certonly --standalone \
  -d livelihood.city.example.lg.jp \
  --email admin@city.example.lg.jp \
  --agree-tos

# シンボリックリンク作成
sudo ln -s /etc/letsencrypt/live/livelihood.city.example.lg.jp/fullchain.pem \
  /etc/ssl/livelihood/server.crt
sudo ln -s /etc/letsencrypt/live/livelihood.city.example.lg.jp/privkey.pem \
  /etc/ssl/livelihood/server.key

# 自動更新設定
sudo systemctl enable certbot.timer
```

---

## アプリケーションデプロイ

### 1. リポジトリクローン

```bash
# アプリケーションユーザーに切り替え
su - livelihood

# リポジトリクローン
cd /opt/livelihood-support
git clone https://github.com/your-org/neo4j-livelihood-support.git .
```

### 2. 環境変数設定

```bash
# 本番用環境変数ファイル作成
cp .env.production.example .env.production
vim .env.production
```

以下を設定:
```bash
# =============================================================================
# 本番環境設定
# =============================================================================

# Neo4j
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<32文字以上の強力なパスワード>
NEO4J_PAGECACHE_SIZE=4G
NEO4J_HEAP_SIZE=4G

# Keycloak
KEYCLOAK_URL=https://livelihood.city.example.lg.jp/auth
KEYCLOAK_REALM=livelihood-support
KEYCLOAK_CLIENT_ID=livelihood-support-app
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=<32文字以上の強力なパスワード>

# アプリケーション
LOG_LEVEL=INFO
SKIP_AUTH=false

# AI機能（任意）
GEMINI_API_KEY=<your-api-key>

# ポート設定
HTTP_PORT=80
HTTPS_PORT=443
```

### 3. Nginx設定

```bash
# SSL設定ファイル作成
mkdir -p nginx/conf.d
cp nginx/conf.d/ssl.conf.example nginx/conf.d/ssl.conf
vim nginx/conf.d/ssl.conf
```

`ssl.conf` の内容:
```nginx
# HTTPS サーバー設定
server {
    listen 443 ssl http2;
    server_name livelihood.city.example.lg.jp;

    # SSL証明書
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    # SSL設定（TLS 1.2/1.3のみ）
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # セキュリティヘッダー
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Streamlit UI
    location / {
        proxy_pass http://streamlit:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # API
    location /api/ {
        proxy_pass http://api:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Keycloak（認証サーバー）
    location /auth/ {
        proxy_pass http://keycloak:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTPからHTTPSへリダイレクト
server {
    listen 80;
    server_name livelihood.city.example.lg.jp;
    return 301 https://$server_name$request_uri;
}
```

### 4. SSL証明書をNginxにマウント

```bash
# 証明書ディレクトリにシンボリックリンク作成
mkdir -p nginx/ssl
ln -s /etc/ssl/livelihood/server.crt nginx/ssl/server.crt
ln -s /etc/ssl/livelihood/server.key nginx/ssl/server.key
```

### 5. コンテナ起動

```bash
# イメージビルド
docker compose -f docker-compose.prod.yml build

# コンテナ起動
docker compose -f docker-compose.prod.yml up -d

# ログ確認
docker compose -f docker-compose.prod.yml logs -f
```

### 6. Neo4jスキーマ初期化

```bash
# スキーマ初期化（初回のみ）
docker compose -f docker-compose.prod.yml exec streamlit \
  python setup_schema.py
```

---

## Keycloak設定

### 1. Keycloak起動

```bash
# Keycloak単体で起動（初期設定用）
docker compose -f docker-compose.keycloak.yml up -d

# ログ確認（起動完了まで待機）
docker compose -f docker-compose.keycloak.yml logs -f keycloak
```

### 2. Realm設定確認

`keycloak/realm-export.json` が自動的にインポートされます。
インポートが完了したら、管理画面でRealmを確認:

1. https://livelihood.city.example.lg.jp/auth/admin にアクセス
2. ユーザー名: `admin`、パスワード: 環境変数で設定したもの
3. 左上のドロップダウンから `livelihood-support` を選択

### 3. ユーザー登録

一括登録スクリプトを使用:

```bash
# サンプルCSVを編集
cp scripts/users_sample.csv users.csv
vim users.csv

# ドライラン（確認）
./scripts/import_users.sh users.csv --dry-run

# 実際に登録
./scripts/import_users.sh users.csv
```

詳細は [KEYCLOAK_USER_MANAGEMENT.md](./KEYCLOAK_USER_MANAGEMENT.md) を参照。

---

## 監視環境構築

### 1. 監視スタック起動

```bash
# 監視環境起動
docker compose -f docker-compose.monitoring.yml up -d

# ステータス確認
docker compose -f docker-compose.monitoring.yml ps
```

### 2. Grafanaダッシュボード設定

1. https://livelihood.city.example.lg.jp:3000 にアクセス
2. 初期ログイン: admin / admin
3. パスワード変更
4. Data Sources → Prometheus を追加:
   - URL: http://prometheus:9090
   - Save & Test

### 3. アラート設定

`monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'mail.city.example.lg.jp:25'
  smtp_from: 'livelihood-alert@city.example.lg.jp'

route:
  receiver: 'admin-team'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'admin-team'
    email_configs:
      - to: 'system-admin@city.example.lg.jp'
        send_resolved: true
```

---

## バックアップ設定

### 1. バックアップスクリプト配置

```bash
# スクリプト配置
sudo cp scripts/backup.sh /opt/livelihood-support/backup.sh
sudo chmod +x /opt/livelihood-support/backup.sh
```

### 2. Cron設定

```bash
# crontab編集
crontab -e
```

以下を追加:
```bash
# 毎日02:00にフルバックアップ
0 2 * * * /opt/livelihood-support/backup.sh --full >> /var/log/livelihood/backup.log 2>&1

# 毎時00分に差分バックアップ
0 * * * * /opt/livelihood-support/backup.sh >> /var/log/livelihood/backup.log 2>&1
```

### 3. バックアップ検証

```bash
# 手動バックアップ実行
/opt/livelihood-support/backup.sh --full

# バックアップファイル確認
ls -la /backup/neo4j/
```

---

## セキュリティ設定

### 1. Fail2ban設定

```bash
# Fail2ban設定
sudo vim /etc/fail2ban/jail.local
```

以下を追加:
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
port = http,https
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
```

Fail2ban再起動:
```bash
sudo systemctl restart fail2ban
sudo fail2ban-client status
```

### 2. 不要サービス停止

```bash
# 不要サービスを無効化
sudo systemctl disable cups
sudo systemctl disable avahi-daemon
sudo systemctl disable bluetooth

# 起動中のサービス確認
sudo systemctl list-units --type=service --state=running
```

### 3. ログローテーション設定

```bash
# アプリケーションログのローテーション
sudo vim /etc/logrotate.d/livelihood
```

以下を追加:
```
/var/log/livelihood/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 livelihood livelihood
    sharedscripts
    postrotate
        docker compose -f /opt/livelihood-support/docker-compose.prod.yml kill -s USR1 nginx
    endscript
}
```

---

## 動作確認

### 1. サービス起動確認

```bash
# 全コンテナの状態確認
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.keycloak.yml ps
docker compose -f docker-compose.monitoring.yml ps

# ヘルスチェック
curl -k https://localhost/
curl -k https://localhost/api/health
curl -k https://localhost/auth/
```

### 2. ログイン確認

1. ブラウザで https://livelihood.city.example.lg.jp にアクセス
2. ログインボタンをクリック
3. 登録済みユーザーでログイン
4. ケース記録入力画面が表示されることを確認

### 3. 機能確認チェックリスト

| 項目 | 確認内容 | 結果 |
|------|---------|------|
| ログイン | Keycloak経由でログイン可能か | [ ] |
| ケース記録入力 | 新規ケース記録を入力できるか | [ ] |
| データ保存 | Neo4jにデータが保存されるか | [ ] |
| AI構造化 | Gemini APIでテキストが構造化されるか | [ ] |
| ロール制御 | 権限のない機能にアクセスできないか | [ ] |
| SSL/TLS | HTTPS接続で警告が出ないか | [ ] |
| 監視 | Grafanaでメトリクスが表示されるか | [ ] |
| バックアップ | バックアップが正常に作成されるか | [ ] |

### 4. パフォーマンス確認

```bash
# レスポンスタイム確認
curl -o /dev/null -s -w "Time: %{time_total}s\n" https://localhost/

# リソース使用状況
docker stats

# Neo4j接続確認
docker compose -f docker-compose.prod.yml exec neo4j \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "RETURN 1 AS test"
```

---

## トラブルシューティング

### よくある問題

#### コンテナが起動しない

```bash
# ログ確認
docker compose -f docker-compose.prod.yml logs <service-name>

# 個別にコンテナを起動してデバッグ
docker compose -f docker-compose.prod.yml up neo4j
```

#### Neo4jに接続できない

```bash
# Neo4jの状態確認
docker compose -f docker-compose.prod.yml exec neo4j \
  neo4j status

# ポート確認
docker compose -f docker-compose.prod.yml port neo4j 7687
```

#### Keycloakでログインできない

```bash
# Keycloakログ確認
docker compose -f docker-compose.keycloak.yml logs keycloak

# Realm設定確認
docker compose -f docker-compose.keycloak.yml exec keycloak \
  /opt/keycloak/bin/kcadm.sh get realms/livelihood-support
```

#### SSL証明書エラー

```bash
# 証明書の有効性確認
openssl s_client -connect localhost:443 -servername livelihood.city.example.lg.jp

# 証明書の有効期限確認
openssl x509 -in /etc/ssl/livelihood/server.crt -noout -dates
```

---

## 関連ドキュメント

- [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) - インフラストラクチャ構成ガイド
- [DEPLOYMENT.md](./DEPLOYMENT.md) - デプロイ手順
- [KEYCLOAK_USER_MANAGEMENT.md](./KEYCLOAK_USER_MANAGEMENT.md) - ユーザー管理
- [TECHNICAL_STANDARDS.md](./TECHNICAL_STANDARDS.md) - 技術基準書
