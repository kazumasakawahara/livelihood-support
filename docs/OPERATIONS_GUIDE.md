# 運用ガイド

生活保護受給者尊厳支援システムの日常運用、トラブルシューティング、保守手順を説明します。

## 目次

1. [システム起動・停止](#システム起動停止)
2. [日常運用](#日常運用)
3. [監視とアラート](#監視とアラート)
4. [バックアップと復元](#バックアップと復元)
5. [トラブルシューティング](#トラブルシューティング)
6. [セキュリティ運用](#セキュリティ運用)

---

## システム起動・停止

### 全サービス起動（開発環境）

```bash
# プロジェクトディレクトリへ移動
cd ~/Dev-Work/neo4j-livelihood-support

# Neo4jデータベース起動
docker compose up -d

# Keycloak認証基盤起動
docker compose -f docker-compose.keycloak.yml up -d

# 起動確認（各サービスがhealthyになるまで待機）
docker compose ps
docker compose -f docker-compose.keycloak.yml ps
```

### サービス個別起動

```bash
# Streamlitアプリ
uv run streamlit run app_case_record.py

# FastAPI REST API
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# MCPサーバー（Claude Desktop連携）
uv run python mcp/server.py
```

### システム停止

```bash
# アプリケーション停止（Ctrl+C）

# Docker停止
docker compose down
docker compose -f docker-compose.keycloak.yml down

# データを保持したまま停止（ボリューム維持）
docker compose stop
```

### 完全リセット（注意：データ削除）

```bash
# すべてのデータを削除してリセット
docker compose down -v
docker compose -f docker-compose.keycloak.yml down -v
rm -rf neo4j_data neo4j_logs neo4j_plugins

# 再起動
docker compose up -d
uv run python setup_schema.py
```

---

## 日常運用

### ヘルスチェック

```bash
# Neo4jヘルスチェック
curl -s http://localhost:7475 | head -1

# Keycloakヘルスチェック
curl -f http://localhost:8080/health/ready

# FastAPIヘルスチェック
curl http://localhost:8000/health

# 全サービス一括確認
./scripts/health_check.sh  # 要作成
```

### ログ確認

```bash
# Neo4jログ
docker compose logs -f neo4j

# Keycloakログ
docker compose -f docker-compose.keycloak.yml logs -f keycloak

# アプリケーションログ（実行中のターミナルで確認）
```

### データベース統計

Neo4j Browserで以下のクエリを実行：

```cypher
// ノード数確認
MATCH (n) RETURN labels(n) AS label, count(n) AS count;

// リレーションシップ数確認
MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count;

// 受給者数
MATCH (r:Recipient) RETURN count(r);

// 支援記録数
MATCH (l:SupportLog) RETURN count(l);
```

---

## 監視とアラート

### Prometheusメトリクス

```bash
# メトリクス確認
curl http://localhost:8000/metrics

# 主要メトリクス
# - http_requests_total: HTTPリクエスト総数
# - http_request_duration_seconds: レスポンス時間
# - neo4j_connections_active: アクティブDB接続数
```

### Grafanaダッシュボード

```
http://localhost:3000
ユーザー名: admin
パスワード: admin（初回ログイン時に変更）
```

### アラート設定

Prometheusアラートルール（`monitoring/prometheus/rules/alerts.yml`）：

```yaml
groups:
  - name: livelihood-support-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高エラー率検出"

      - alert: DatabaseConnectionFailed
        expr: neo4j_connections_active == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "データベース接続なし"
```

---

## バックアップと復元

### 手動バックアップ

```bash
# 通常バックアップ（オンライン）
./scripts/backup.sh

# フルバックアップ（コンテナ一時停止）
./scripts/backup.sh --full

# バックアップ確認
ls -la neo4j_backup/
```

### 定期バックアップ設定

```bash
# 毎日午前3時に自動バックアップ
./scripts/setup_scheduled_backup.sh install

# 状態確認
./scripts/setup_scheduled_backup.sh status

# 無効化
./scripts/setup_scheduled_backup.sh uninstall
```

### 復元手順

```bash
# 最新バックアップから復元
./scripts/restore.sh

# 指定ファイルから復元
./scripts/restore.sh full_backup_20241228_030000.tar.gz
```

### Keycloakバックアップ

```bash
# レルム設定エクスポート
docker exec livelihood-keycloak \
  /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm livelihood-support

docker cp livelihood-keycloak:/tmp/export ./keycloak_backup/
```

---

## トラブルシューティング

### Neo4jが起動しない

```bash
# ログ確認
docker compose logs neo4j

# よくある原因と対処
# 1. ポート競合
lsof -i :7475
lsof -i :7688

# 2. メモリ不足
docker stats

# 3. データ破損
docker compose down
rm -rf neo4j_data
docker compose up -d
uv run python setup_schema.py
```

### Keycloakが起動しない

```bash
# ログ確認
docker compose -f docker-compose.keycloak.yml logs keycloak

# PostgreSQL接続確認
docker compose -f docker-compose.keycloak.yml logs keycloak-db

# 再起動
docker compose -f docker-compose.keycloak.yml restart keycloak
```

### 認証エラー

```bash
# トークン検証エラー
# → DEBUG=true でログを確認
DEBUG=true uv run uvicorn api.main:app --reload

# JWKSキャッシュクリア
# → アプリケーション再起動

# Keycloakとの接続確認
curl http://localhost:8080/realms/livelihood-support/.well-known/openid_configuration
```

### データベース接続エラー

```bash
# 接続テスト
uv run python -c "
from lib.db_connection import get_driver
driver = get_driver()
with driver.session() as session:
    result = session.run('RETURN 1')
    print('接続成功:', result.single()[0])
"

# 環境変数確認
cat .env | grep NEO4J
```

### パフォーマンス問題

```bash
# Neo4j統計
docker exec -it livelihood-neo4j cypher-shell -u neo4j -p password \
  "CALL dbms.queryJmx('org.neo4j:*')"

# スロークエリ確認（Neo4j Browser）
CALL dbms.listQueries() YIELD query, elapsedTimeMillis
WHERE elapsedTimeMillis > 1000
RETURN query, elapsedTimeMillis;
```

---

## セキュリティ運用

### パスワード変更

#### Neo4j

```cypher
// Neo4j Browserで実行
ALTER USER neo4j SET PASSWORD 'new_secure_password';
```

`.env` も更新：
```env
NEO4J_PASSWORD=new_secure_password
```

#### Keycloak管理者

1. http://localhost:8080 にログイン
2. 右上のユーザー名をクリック
3. 「Manage account」→「Password」で変更

#### アプリケーションユーザー

1. Keycloak管理コンソールにログイン
2. Users → 対象ユーザー選択
3. Credentials タブでパスワードリセット

### アクセスログ監査

```bash
# Keycloak認証イベント確認
# 管理コンソール → Events → Login Events

# APIアクセスログ
# FastAPIログで確認（標準出力）

# Neo4jクエリログ
docker compose logs neo4j | grep "Query"
```

### セキュリティ更新

```bash
# Dockerイメージ更新
docker compose pull
docker compose up -d

docker compose -f docker-compose.keycloak.yml pull
docker compose -f docker-compose.keycloak.yml up -d

# Pythonパッケージ更新
uv sync --upgrade
```

### 本番環境チェックリスト

- [ ] DEBUG=false に設定
- [ ] AUTH_SKIP=false に設定
- [ ] Neo4jパスワードを強力なものに変更
- [ ] Keycloak管理者パスワードを変更
- [ ] HTTPS有効化（リバースプロキシ設定）
- [ ] ファイアウォール設定（必要なポートのみ開放）
- [ ] 定期バックアップ設定
- [ ] 監視アラート設定
- [ ] ログローテーション設定

---

## 連絡先・エスカレーション

### 緊急時対応

1. **データベース障害**:
   - バックアップから復元を試行
   - 復元不可の場合はシステム管理者へ連絡

2. **認証障害**:
   - Keycloakサービス再起動
   - 解決しない場合はDEBUG=true AUTH_SKIP=trueで一時回避（開発環境のみ）

3. **セキュリティインシデント**:
   - 即座にシステム停止
   - 監査ログ保全
   - セキュリティ担当者へ報告

---

## 変更履歴

| 日付 | バージョン | 変更内容 |
|------|-----------|---------|
| 2024-12-29 | 1.0 | 初版作成 |
