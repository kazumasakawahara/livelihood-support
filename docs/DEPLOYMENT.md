# 本番デプロイガイド

生活保護受給者尊厳支援システムの本番環境へのデプロイ手順を説明します。

## 前提条件

### サーバー要件

| 項目 | 最小要件 | 推奨 |
|------|---------|------|
| CPU | 4 コア | 8 コア以上 |
| メモリ | 8 GB | 16 GB以上 |
| ストレージ | 100 GB SSD | 500 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### ソフトウェア要件

- Docker 24.0以上
- Docker Compose 2.20以上
- Git
- certbot（Let's Encrypt証明書用）

## デプロイ手順

### 1. サーバー準備

```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# Docker インストール
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Docker Compose インストール（最新版）
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# certbot インストール
sudo apt install -y certbot
```

### 2. プロジェクト取得

```bash
# プロジェクトクローン
cd /opt
sudo git clone https://github.com/your-org/neo4j-livelihood-support.git
sudo chown -R $USER:$USER neo4j-livelihood-support
cd neo4j-livelihood-support
```

### 3. 環境変数設定

```bash
# 本番環境設定ファイル作成
cp .env.production.example .env.production

# 設定編集（強力なパスワードを設定）
nano .env.production

# パーミッション制限
chmod 600 .env.production
```

### 4. SSL証明書取得

#### Let's Encrypt（推奨）

```bash
# certbot で証明書取得
sudo certbot certonly --standalone -d your-domain.example.com

# 証明書をNginxディレクトリにコピー
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.example.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.example.com/privkey.pem nginx/ssl/
sudo chown -R $USER:$USER nginx/ssl
```

#### 自己署名証明書（開発・テスト用）

```bash
# 開発環境用SSL証明書生成スクリプトを使用（推奨）
./scripts/generate_ssl_certs.sh

# または手動で生成
./scripts/generate_ssl_certs.sh ./nginx/ssl your-domain.local 365
```

このスクリプトは以下を生成します:
- 4096ビットRSA秘密鍵（privkey.pem）
- SHA-256自己署名証明書（fullchain.pem）- SAN対応、localhost含む
- DHパラメータ（dhparam.pem）- Forward Secrecy強化用

### 5. Nginx SSL設定

```bash
# SSL設定を有効化
cp nginx/conf.d/ssl.conf.example nginx/conf.d/ssl.conf

# ドメイン名を編集
sed -i 's/your-domain.example.com/YOUR_ACTUAL_DOMAIN/g' nginx/conf.d/ssl.conf

# デフォルト設定を無効化（SSL使用時）
mv nginx/conf.d/default.conf nginx/conf.d/default.conf.bak
```

### 6. サービス起動

```bash
# 本番環境用Docker Compose起動
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# ログ確認
docker compose -f docker-compose.prod.yml logs -f
```

### 7. 初期設定

```bash
# Neo4jスキーマ初期化
docker compose -f docker-compose.prod.yml exec api python setup_schema.py

# Keycloakレルム確認
# ブラウザで https://your-domain/auth/ にアクセス
```

### 8. 動作確認

```bash
# ヘルスチェック
curl -k https://your-domain.example.com/health
curl -k https://your-domain.example.com/api/health

# SSL確認
openssl s_client -connect your-domain.example.com:443 -servername your-domain.example.com
```

## セキュリティ設定

### ファイアウォール

```bash
# UFW設定
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 確認
sudo ufw status
```

### fail2ban（ブルートフォース対策）

```bash
sudo apt install -y fail2ban

# Nginx用設定
cat << 'EOF' | sudo tee /etc/fail2ban/jail.d/nginx.conf
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600
EOF

sudo systemctl restart fail2ban
```

## ログローテーション

```bash
# logrotate設定をインストール
sudo cp scripts/logrotate.conf /etc/logrotate.d/livelihood-support

# テスト実行
sudo logrotate -d /etc/logrotate.d/livelihood-support
```

## バックアップ設定

### 定期バックアップ

```bash
# バックアップスクリプトに実行権限
chmod +x scripts/backup.sh

# cron設定（毎日3時にバックアップ）
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/neo4j-livelihood-support/scripts/backup.sh --full >> /var/log/backup.log 2>&1") | crontab -
```

### S3バックアップ（オプション）

```bash
# AWS CLI インストール
sudo apt install -y awscli

# 認証情報設定
aws configure

# S3同期スクリプト
cat << 'EOF' > scripts/backup_to_s3.sh
#!/bin/bash
aws s3 sync /opt/neo4j-livelihood-support/neo4j_backup/ s3://${BACKUP_S3_BUCKET}/neo4j/ --delete
EOF
chmod +x scripts/backup_to_s3.sh
```

## 証明書自動更新

```bash
# Let's Encrypt自動更新設定
cat << 'EOF' | sudo tee /etc/cron.d/certbot-renew
0 0,12 * * * root certbot renew --quiet --deploy-hook "/opt/neo4j-livelihood-support/scripts/ssl-renew-hook.sh"
EOF
```

```bash
# 更新フック作成
cat << 'EOF' > scripts/ssl-renew-hook.sh
#!/bin/bash
cp /etc/letsencrypt/live/your-domain.example.com/fullchain.pem /opt/neo4j-livelihood-support/nginx/ssl/
cp /etc/letsencrypt/live/your-domain.example.com/privkey.pem /opt/neo4j-livelihood-support/nginx/ssl/
docker compose -f /opt/neo4j-livelihood-support/docker-compose.prod.yml exec nginx nginx -s reload
EOF
chmod +x scripts/ssl-renew-hook.sh
```

## 監視設定

### Prometheusアラート

```bash
# アラートルール確認
cat monitoring/prometheus/rules/alerts.yml

# アラート設定編集（メール通知先など）
nano monitoring/prometheus/alertmanager.yml
```

### Grafanaダッシュボード

1. https://your-domain/grafana/ にアクセス
2. 初期パスワードでログイン
3. パスワード変更
4. ダッシュボードインポート

## トラブルシューティング

### サービスが起動しない

```bash
# ログ確認
docker compose -f docker-compose.prod.yml logs --tail=100

# 個別サービスログ
docker compose -f docker-compose.prod.yml logs neo4j
docker compose -f docker-compose.prod.yml logs api
docker compose -f docker-compose.prod.yml logs nginx
```

### SSL証明書エラー

```bash
# 証明書確認
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# 証明書更新
sudo certbot renew --force-renewal
```

### メモリ不足

```bash
# メモリ使用状況
docker stats

# Neo4jメモリ設定調整（.env.production）
NEO4J_PAGECACHE_SIZE=1G
NEO4J_HEAP_SIZE=1G
```

## アップデート手順

```bash
# バックアップ
./scripts/backup.sh --full

# コード更新
git pull origin main

# イメージ再ビルド
docker compose -f docker-compose.prod.yml build

# サービス再起動
docker compose -f docker-compose.prod.yml up -d

# 動作確認
curl -k https://your-domain.example.com/health
```

## ロールバック

```bash
# 前バージョンに戻す
git checkout <previous-commit>

# 再デプロイ
docker compose -f docker-compose.prod.yml up -d --build

# 必要に応じてデータベース復元
./scripts/restore.sh <backup-file>
```

## 連絡先

- 緊急時: システム管理者へ連絡
- セキュリティインシデント: 即座にサービス停止、監査ログ保全
