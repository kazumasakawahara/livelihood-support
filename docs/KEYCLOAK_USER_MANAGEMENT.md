# Keycloak ユーザー管理ガイド

本番環境でのユーザー登録・管理手順を説明します。

## 概要

本システムはKeycloak OIDC認証を使用しており、以下の特徴があります：

- **セルフ登録は無効**（`registrationAllowed: false`）
- **管理者がユーザーを登録する運用**
- **ロールベースアクセス制御（RBAC）**

## ロール一覧

| ロール | 権限 | 対象者 |
|--------|------|--------|
| `caseworker` | ケース記録の読み書き | 一般ケースワーカー |
| `supervisor` | チーム閲覧 + caseworker権限 | 係長・主任 |
| `admin` | 全権限 | システム管理者 |
| `auditor` | 監査ログ閲覧のみ | 監査担当 |

## グループ構成

```
福祉課/
├── 第1係
├── 第2係
└── 第3係
```

---

## ユーザー登録手順（管理画面から）

### 1. Keycloak管理画面にアクセス

| 環境 | URL |
|------|-----|
| 開発環境 | http://localhost:8080/admin |
| 本番環境 | https://your-domain.com/auth/admin |

**管理者ログイン情報**:

| 項目 | 開発環境 | 本番環境 |
|------|---------|---------|
| Username | `admin` | 環境変数 `KEYCLOAK_ADMIN` |
| Password | `admin_dev_password` | 環境変数 `KEYCLOAK_ADMIN_PASSWORD` |

### 2. Realmを選択

左上のドロップダウンから **`livelihood-support`** を選択します。

### 3. ユーザー作成

1. 左メニュー「**Users**」をクリック
2. 「**Add user**」ボタンをクリック
3. 必須項目を入力:

| 項目 | 入力例 | 説明 |
|------|--------|------|
| Username | `yamada.taro` | ログインID（変更不可） |
| Email | `yamada@city.example.lg.jp` | メールアドレス |
| First name | `太郎` | 名 |
| Last name | `山田` | 姓 |
| Email verified | ON | メール確認済みにする |

4. 「**Create**」をクリック

### 4. パスワード設定

1. 作成したユーザーの詳細画面で「**Credentials**」タブを開く
2. 「**Set password**」をクリック
3. パスワードを入力:

| 項目 | 設定 |
|------|------|
| Password | 初期パスワード |
| Password confirmation | 同上 |
| Temporary | **ON**（初回ログイン時に変更を強制） |

4. 「**Save**」をクリック

### 5. ロール割り当て

1. 「**Role mapping**」タブを開く
2. 「**Assign role**」をクリック
3. フィルタで「Filter by realm roles」を選択
4. 適切なロールにチェック（例: `caseworker`）
5. 「**Assign**」をクリック

### 6. グループ割り当て（任意）

1. 「**Groups**」タブを開く
2. 「**Join Group**」をクリック
3. 所属を選択（例: `/福祉課/第1係`）
4. 「**Join**」をクリック

---

## ユーザー一括登録（CLI）

大量のユーザーを登録する場合は、Keycloak Admin CLIを使用します。

### 事前準備

```bash
# Keycloakコンテナに入る
docker exec -it livelihood-keycloak bash

# 管理者としてログイン
/opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password "$KEYCLOAK_ADMIN_PASSWORD"
```

### 単一ユーザー作成

```bash
# ユーザー作成
/opt/keycloak/bin/kcadm.sh create users \
  -r livelihood-support \
  -s username=yamada.taro \
  -s email=yamada@city.example.lg.jp \
  -s firstName=太郎 \
  -s lastName=山田 \
  -s enabled=true

# パスワード設定（初回ログイン時に変更を強制）
/opt/keycloak/bin/kcadm.sh set-password \
  -r livelihood-support \
  --username yamada.taro \
  --new-password "InitialPassword123!" \
  --temporary

# ロール割り当て
/opt/keycloak/bin/kcadm.sh add-roles \
  -r livelihood-support \
  --uusername yamada.taro \
  --rolename caseworker
```

### CSVからの一括登録スクリプト

`scripts/import_users.sh` を作成して使用:

```bash
#!/bin/bash
# Usage: ./scripts/import_users.sh users.csv

CSV_FILE=$1
REALM="livelihood-support"

while IFS=, read -r username email firstname lastname role group; do
  # ヘッダー行をスキップ
  [ "$username" = "username" ] && continue

  echo "Creating user: $username"

  # ユーザー作成
  /opt/keycloak/bin/kcadm.sh create users \
    -r "$REALM" \
    -s username="$username" \
    -s email="$email" \
    -s firstName="$firstname" \
    -s lastName="$lastname" \
    -s enabled=true

  # パスワード設定
  /opt/keycloak/bin/kcadm.sh set-password \
    -r "$REALM" \
    --username "$username" \
    --new-password "ChangeMe123!" \
    --temporary

  # ロール割り当て
  /opt/keycloak/bin/kcadm.sh add-roles \
    -r "$REALM" \
    --uusername "$username" \
    --rolename "$role"

  echo "Created: $username with role $role"
done < "$CSV_FILE"
```

**CSVファイル形式** (`users.csv`):
```csv
username,email,firstname,lastname,role,group
yamada.taro,yamada@example.lg.jp,太郎,山田,caseworker,/福祉課/第1係
suzuki.hanako,suzuki@example.lg.jp,花子,鈴木,supervisor,/福祉課/第1係
```

---

## ユーザー管理操作

### ユーザーの無効化

1. 「Users」→ 対象ユーザーを選択
2. 「Enabled」を **OFF** に変更
3. 「Save」をクリック

### パスワードリセット

1. 「Users」→ 対象ユーザーを選択
2. 「Credentials」タブ
3. 「Set password」で新しいパスワードを設定
4. 「Temporary」を **ON** にして保存

### ユーザーの削除

1. 「Users」→ 対象ユーザーを選択
2. 「Action」→「Delete」
3. 確認ダイアログで「Delete」

> **注意**: 削除したユーザーは復元できません。無効化を推奨します。

---

## セキュリティ設定

### 本番環境チェックリスト

| 項目 | 設定 | 確認 |
|------|------|------|
| SSL/TLS | `sslRequired: "external"` または `"all"` | [ ] |
| 管理者パスワード | 強力なパスワードに変更 | [ ] |
| ブルートフォース保護 | 有効（5回失敗で15分ロック） | [ ] |
| セッションタイムアウト | 30分（`ssoSessionIdleTimeout: 1800`） | [ ] |
| `.env` の `SKIP_AUTH` | **必ず `false`** | [ ] |

### パスワードポリシー（推奨）

Keycloak管理画面 → Authentication → Policies → Password policy で設定:

- 最小文字数: 12文字以上
- 大文字・小文字・数字・記号を含む
- パスワード履歴: 過去5回と重複不可

---

## トラブルシューティング

### ログインできない

1. **ユーザーが無効化されていないか確認**
   - Users → 対象ユーザー → Enabled が ON か確認

2. **パスワードが正しいか確認**
   - Credentials タブで新しいパスワードを設定

3. **ロールが割り当てられているか確認**
   - Role mapping タブで `caseworker` 以上のロールがあるか確認

### 「アクセス権限がありません」エラー

- ユーザーに `caseworker`、`supervisor`、または `admin` ロールが必要
- Role mapping タブでロールを確認・追加

### Keycloak管理画面にアクセスできない

```bash
# コンテナの状態確認
docker compose -f docker-compose.keycloak.yml ps

# ログ確認
docker logs livelihood-keycloak

# 再起動
docker compose -f docker-compose.keycloak.yml restart keycloak
```

---

## 関連ドキュメント

- [DEPLOYMENT.md](./DEPLOYMENT.md) - 本番環境デプロイ手順
- [TECHNICAL_STANDARDS.md](./TECHNICAL_STANDARDS.md) - 技術基準書（認証基盤仕様）
