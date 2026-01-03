"""
API認証モジュールのテスト
api/dependencies.py の認証機能をテスト
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from api.dependencies import (
    User,
    Permission,
    ROLE_PERMISSIONS,
    Settings,
    JWKSCache,
    get_mock_user,
    require_permission,
    require_role,
    require_any_role,
    get_request_id,
)


# =============================================================================
# Userクラスのテスト
# =============================================================================

class TestAPIUser:
    """API Userクラスのテスト"""

    def test_user_creation(self):
        """ユーザー作成"""
        user = User(
            user_id="test-001",
            username="test_user",
            name="テストユーザー",
            email="test@example.com",
            roles=["caseworker"],
        )

        assert user.user_id == "test-001"
        assert user.username == "test_user"
        assert user.name == "テストユーザー"
        assert user.email == "test@example.com"
        assert user.roles == ["caseworker"]

    def test_user_without_name(self):
        """名前なしでユーザー作成"""
        user = User(
            user_id="test-001",
            username="test_user",
        )

        assert user.name == "test_user"  # usernameがデフォルト

    def test_caseworker_permissions(self):
        """ケースワーカーの権限"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker"],
        )

        assert user.has_permission(Permission.READ_OWN_CASES)
        assert user.has_permission(Permission.WRITE_OWN_CASES)
        assert not user.has_permission(Permission.READ_TEAM_CASES)
        assert not user.has_permission(Permission.SYSTEM_ADMIN)

    def test_supervisor_permissions(self):
        """スーパーバイザーの権限"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["supervisor"],
        )

        assert user.has_permission(Permission.READ_OWN_CASES)
        assert user.has_permission(Permission.READ_TEAM_CASES)
        assert user.has_permission(Permission.VIEW_AUDIT_LOGS)
        assert not user.has_permission(Permission.SYSTEM_ADMIN)

    def test_admin_has_all_permissions(self):
        """管理者は全権限を持つ"""
        user = User(
            user_id="test-001",
            username="admin_user",
            roles=["admin"],
        )

        # adminは全権限を持つ
        for permission in Permission:
            assert user.has_permission(permission)

    def test_auditor_permissions(self):
        """監査者の権限"""
        user = User(
            user_id="test-001",
            username="auditor_user",
            roles=["auditor"],
        )

        assert user.has_permission(Permission.VIEW_AUDIT_LOGS)
        assert not user.has_permission(Permission.READ_OWN_CASES)
        assert not user.has_permission(Permission.SYSTEM_ADMIN)

    def test_multiple_roles(self):
        """複数ロールを持つユーザー"""
        user = User(
            user_id="test-001",
            username="multi_role_user",
            roles=["caseworker", "supervisor"],
        )

        # 両方のロールの権限を持つ
        assert user.has_permission(Permission.READ_OWN_CASES)
        assert user.has_permission(Permission.WRITE_OWN_CASES)
        assert user.has_permission(Permission.READ_TEAM_CASES)
        assert user.has_permission(Permission.VIEW_AUDIT_LOGS)

    def test_has_role(self):
        """ロールチェック"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker", "supervisor"],
        )

        assert user.has_role("caseworker")
        assert user.has_role("supervisor")
        assert not user.has_role("admin")


# =============================================================================
# Settingsクラスのテスト
# =============================================================================

class TestAPISettings:
    """API Settingsクラスのテスト"""

    def test_default_settings(self):
        """デフォルト設定"""
        settings = Settings()

        assert settings.keycloak_url == "http://localhost:8080"
        assert settings.keycloak_realm == "livelihood-support"
        assert settings.debug is False
        assert settings.auth_skip is False

    def test_jwks_url(self):
        """JWKS URLの生成"""
        settings = Settings()
        expected = "http://localhost:8080/realms/livelihood-support/protocol/openid-connect/certs"

        assert settings.jwks_url == expected

    def test_issuer(self):
        """Issuer URLの生成"""
        settings = Settings()
        expected = "http://localhost:8080/realms/livelihood-support"

        assert settings.issuer == expected


# =============================================================================
# JWKSCacheのテスト
# =============================================================================

class TestAPIJWKSCache:
    """API JWKSCacheクラスのテスト"""

    def test_cache_initialization(self):
        """キャッシュ初期化"""
        cache = JWKSCache()

        assert cache._keys == {}
        assert cache._expires_at is None

    def test_cache_is_expired_initially(self):
        """初期状態では期限切れ"""
        cache = JWKSCache()

        assert cache._is_expired() is True

    def test_cache_not_expired_after_refresh(self):
        """リフレッシュ後は期限切れでない"""
        cache = JWKSCache()
        cache._expires_at = datetime.now() + timedelta(hours=1)

        assert cache._is_expired() is False

    def test_cache_expired_after_time(self):
        """時間経過後は期限切れ"""
        cache = JWKSCache()
        cache._expires_at = datetime.now() - timedelta(hours=1)

        assert cache._is_expired() is True

    def test_cache_clear(self):
        """キャッシュクリア"""
        cache = JWKSCache()
        cache._keys = {"test_kid": {"kty": "RSA"}}
        cache._expires_at = datetime.now()

        cache.clear()

        assert cache._keys == {}
        assert cache._expires_at is None


# =============================================================================
# モックユーザーのテスト
# =============================================================================

class TestAPIMockUser:
    """APIモックユーザーのテスト"""

    def test_get_mock_user(self):
        """モックユーザーの取得"""
        user = get_mock_user()

        assert user.user_id == "dev-user-001"
        assert user.username == "dev_caseworker"
        assert user.has_role("caseworker")


# =============================================================================
# 権限チェック関数のテスト
# =============================================================================

class TestAPIPermissionChecks:
    """API権限チェック関数のテスト

    Note: require_permission等はFastAPI Dependsを使用するため、
    直接呼び出しではテストできない。代わりにUserの権限チェックメソッドを
    テストし、FastAPI統合はE2Eテストでカバーする。
    """

    def test_require_permission_success(self):
        """権限チェック成功（User.has_permission経由）"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker"],
        )

        # require_permissionの内部ロジックをテスト
        assert user.has_permission(Permission.READ_OWN_CASES) is True

    def test_require_permission_failure(self):
        """権限チェック失敗（User.has_permission経由）"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker"],
        )

        # SYSTEM_ADMIN権限はcaseworkerにはない
        assert user.has_permission(Permission.SYSTEM_ADMIN) is False

    def test_require_role_success(self):
        """ロールチェック成功（User.has_role経由）"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["supervisor"],
        )

        assert user.has_role("supervisor") is True

    def test_require_role_failure(self):
        """ロールチェック失敗（User.has_role経由）"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker"],
        )

        assert user.has_role("admin") is False

    def test_require_any_role_success(self):
        """いずれかのロールチェック成功"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker"],
        )

        # caseworkerはリストに含まれる
        has_any = any(user.has_role(role) for role in ["caseworker", "supervisor", "admin"])
        assert has_any is True

    def test_require_any_role_failure(self):
        """いずれかのロールチェック失敗"""
        user = User(
            user_id="test-001",
            username="test_user",
            roles=["caseworker"],
        )

        # caseworkerはsupervisorでもadminでもない
        has_any = any(user.has_role(role) for role in ["supervisor", "admin"])
        assert has_any is False


# =============================================================================
# リクエストコンテキストのテスト
# =============================================================================

class TestAPIRequestContext:
    """APIリクエストコンテキストのテスト"""

    def test_get_request_id_from_header(self):
        """ヘッダーからリクエストID取得"""
        mock_request = Mock()
        mock_request.headers = {"X-Request-ID": "test-request-123"}

        request_id = get_request_id(mock_request)

        assert request_id == "test-request-123"

    def test_get_request_id_generated(self):
        """リクエストID生成"""
        mock_request = Mock()
        mock_request.headers = {}

        request_id = get_request_id(mock_request)

        # UUID形式であることを確認
        assert len(request_id) == 36
        assert request_id.count("-") == 4


# =============================================================================
# ロールと権限のマッピングテスト
# =============================================================================

class TestAPIRolePermissionMapping:
    """APIロールと権限のマッピングテスト"""

    def test_caseworker_role_mapping(self):
        """ケースワーカーロールのマッピング"""
        permissions = ROLE_PERMISSIONS["caseworker"]

        assert Permission.READ_OWN_CASES in permissions
        assert Permission.WRITE_OWN_CASES in permissions
        assert len(permissions) == 2

    def test_supervisor_role_mapping(self):
        """スーパーバイザーロールのマッピング"""
        permissions = ROLE_PERMISSIONS["supervisor"]

        assert Permission.READ_OWN_CASES in permissions
        assert Permission.WRITE_OWN_CASES in permissions
        assert Permission.READ_TEAM_CASES in permissions
        assert Permission.VIEW_AUDIT_LOGS in permissions
        assert len(permissions) == 4

    def test_admin_role_mapping(self):
        """管理者ロールのマッピング"""
        permissions = ROLE_PERMISSIONS["admin"]

        assert Permission.SYSTEM_ADMIN in permissions

    def test_auditor_role_mapping(self):
        """監査者ロールのマッピング"""
        permissions = ROLE_PERMISSIONS["auditor"]

        assert Permission.VIEW_AUDIT_LOGS in permissions
        assert len(permissions) == 1
