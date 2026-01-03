"""
api/dependencies.py のユニットテスト
FastAPI依存関係（認証・権限）のテスト
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import uuid

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.dependencies import (
    Settings,
    get_settings,
    JWKSCache,
    Permission,
    ROLE_PERMISSIONS,
    User,
    verify_token,
    get_current_user,
    require_permission,
    require_role,
    require_any_role,
    get_request_id,
    get_mock_user,
    get_current_user_or_mock,
)


class TestSettings:
    """Settingsクラスのテスト"""

    def test_default_settings(self):
        """デフォルト設定値"""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings()
            assert settings.keycloak_url == "http://localhost:8080"
            assert settings.keycloak_realm == "livelihood-support"
            assert settings.keycloak_client_id == "livelihood-support-app"
            assert settings.debug is False
            assert settings.auth_skip is False

    def test_custom_settings(self):
        """カスタム設定値"""
        env = {
            "KEYCLOAK_URL": "https://keycloak.example.com",
            "KEYCLOAK_REALM": "custom-realm",
            "KEYCLOAK_CLIENT_ID": "custom-client",
            "DEBUG": "true",
            "AUTH_SKIP": "true",
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings()
            assert settings.keycloak_url == "https://keycloak.example.com"
            assert settings.keycloak_realm == "custom-realm"
            assert settings.keycloak_client_id == "custom-client"
            assert settings.debug is True
            assert settings.auth_skip is True

    def test_jwks_url_property(self):
        """JWKSのURLプロパティ"""
        settings = Settings()
        expected = "http://localhost:8080/realms/livelihood-support/protocol/openid-connect/certs"
        assert settings.jwks_url == expected

    def test_issuer_property(self):
        """issuerプロパティ"""
        settings = Settings()
        expected = "http://localhost:8080/realms/livelihood-support"
        assert settings.issuer == expected


class TestGetSettings:
    """get_settings関数のテスト"""

    def test_returns_settings_instance(self):
        """Settingsインスタンスを返す"""
        get_settings.cache_clear()
        result = get_settings()
        assert isinstance(result, Settings)

    def test_cached(self):
        """キャッシュされる"""
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
        assert first is second


class TestJWKSCache:
    """JWKSCacheクラスのテスト"""

    def test_initial_state_is_expired(self):
        """初期状態は期限切れ"""
        cache = JWKSCache()
        assert cache._is_expired() is True

    def test_clear_cache(self):
        """キャッシュクリア"""
        cache = JWKSCache()
        cache._keys = {"kid1": {"key": "value"}}
        cache._expires_at = datetime.now() + timedelta(hours=1)

        cache.clear()

        assert cache._keys == {}
        assert cache._expires_at is None

    def test_is_expired_when_set(self):
        """期限が設定されている場合の判定"""
        cache = JWKSCache()

        # 未来の期限
        cache._expires_at = datetime.now() + timedelta(hours=1)
        assert cache._is_expired() is False

        # 過去の期限
        cache._expires_at = datetime.now() - timedelta(hours=1)
        assert cache._is_expired() is True


class TestPermission:
    """Permissionエナムのテスト"""

    def test_permission_values(self):
        """権限値の確認"""
        assert Permission.READ_OWN_CASES.value == "read:own_cases"
        assert Permission.WRITE_OWN_CASES.value == "write:own_cases"
        assert Permission.READ_TEAM_CASES.value == "read:team_cases"
        assert Permission.READ_ALL_CASES.value == "read:all_cases"
        assert Permission.MANAGE_USERS.value == "manage:users"
        assert Permission.VIEW_AUDIT_LOGS.value == "view:audit_logs"
        assert Permission.SYSTEM_ADMIN.value == "system:admin"


class TestRolePermissions:
    """ロール権限マッピングのテスト"""

    def test_caseworker_permissions(self):
        """ケースワーカーの権限"""
        perms = ROLE_PERMISSIONS["caseworker"]
        assert Permission.READ_OWN_CASES in perms
        assert Permission.WRITE_OWN_CASES in perms
        assert len(perms) == 2

    def test_supervisor_permissions(self):
        """スーパーバイザーの権限"""
        perms = ROLE_PERMISSIONS["supervisor"]
        assert Permission.READ_OWN_CASES in perms
        assert Permission.READ_TEAM_CASES in perms
        assert Permission.VIEW_AUDIT_LOGS in perms

    def test_admin_permissions(self):
        """管理者の権限"""
        perms = ROLE_PERMISSIONS["admin"]
        assert Permission.SYSTEM_ADMIN in perms

    def test_auditor_permissions(self):
        """監査人の権限"""
        perms = ROLE_PERMISSIONS["auditor"]
        assert Permission.VIEW_AUDIT_LOGS in perms
        assert len(perms) == 1


class TestUser:
    """Userクラスのテスト"""

    def test_user_creation(self):
        """ユーザー作成"""
        user = User(
            user_id="user-001",
            username="testuser",
            name="Test User",
            email="test@example.com",
            roles=["caseworker"],
        )
        assert user.user_id == "user-001"
        assert user.username == "testuser"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.roles == ["caseworker"]

    def test_user_default_name(self):
        """nameがない場合はusernameが使用される"""
        user = User(user_id="user-001", username="testuser")
        assert user.name == "testuser"

    def test_user_default_roles(self):
        """rolesがない場合は空リスト"""
        user = User(user_id="user-001", username="testuser")
        assert user.roles == []

    def test_caseworker_permissions(self):
        """ケースワーカーの権限セット"""
        user = User(user_id="1", username="cw", roles=["caseworker"])
        perms = user.permissions
        assert Permission.READ_OWN_CASES in perms
        assert Permission.WRITE_OWN_CASES in perms
        assert Permission.VIEW_AUDIT_LOGS not in perms

    def test_supervisor_permissions(self):
        """スーパーバイザーの権限セット"""
        user = User(user_id="1", username="sv", roles=["supervisor"])
        perms = user.permissions
        assert Permission.READ_TEAM_CASES in perms
        assert Permission.VIEW_AUDIT_LOGS in perms

    def test_admin_has_all_permissions(self):
        """管理者は全権限を持つ"""
        user = User(user_id="1", username="admin", roles=["admin"])
        perms = user.permissions
        assert perms == set(Permission)

    def test_has_permission(self):
        """権限チェック"""
        user = User(user_id="1", username="cw", roles=["caseworker"])
        assert user.has_permission(Permission.READ_OWN_CASES) is True
        assert user.has_permission(Permission.VIEW_AUDIT_LOGS) is False

    def test_has_role(self):
        """ロールチェック"""
        user = User(user_id="1", username="cw", roles=["caseworker"])
        assert user.has_role("caseworker") is True
        assert user.has_role("admin") is False

    def test_multiple_roles(self):
        """複数ロールの権限統合"""
        user = User(user_id="1", username="u", roles=["caseworker", "auditor"])
        perms = user.permissions
        assert Permission.READ_OWN_CASES in perms
        assert Permission.VIEW_AUDIT_LOGS in perms


class TestGetRequestId:
    """get_request_id関数のテスト"""

    def test_returns_header_if_present(self):
        """ヘッダーにX-Request-IDがある場合"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "existing-request-id"

        result = get_request_id(mock_request)
        assert result == "existing-request-id"

    def test_generates_uuid_if_missing(self):
        """ヘッダーにX-Request-IDがない場合"""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None

        result = get_request_id(mock_request)

        # UUID形式の確認
        assert len(result) == 36
        uuid.UUID(result)  # 有効なUUIDか確認


class TestGetMockUser:
    """get_mock_user関数のテスト"""

    def test_returns_mock_user(self):
        """モックユーザーを返す"""
        user = get_mock_user()
        assert user.user_id == "dev-user-001"
        assert user.username == "dev_caseworker"
        assert user.name == "開発用ケースワーカー"
        assert "caseworker" in user.roles


class TestVerifyToken:
    """verify_token関数のテスト"""

    @pytest.mark.asyncio
    async def test_no_credentials(self):
        """認証情報なしでエラー"""
        settings = Settings()

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(None, settings)

        assert exc_info.value.status_code == 401
        assert "認証が必要です" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_debug_mode_skips_verification(self):
        """デバッグモードでは署名検証をスキップ"""
        with patch.dict("os.environ", {"DEBUG": "true"}, clear=True):
            settings = Settings()

            # 有効なJWTペイロードをモック
            mock_jwt = MagicMock()
            mock_jwt.decode.return_value = {
                "sub": "user-123",
                "preferred_username": "testuser",
                "name": "Test User",
                "email": "test@example.com",
                "realm_access": {"roles": ["caseworker"]},
            }

            with patch("api.dependencies.jwt", mock_jwt):
                with patch("api.dependencies.JWT_AVAILABLE", True):
                    credentials = HTTPAuthorizationCredentials(
                        scheme="Bearer", credentials="fake.jwt.token"
                    )
                    user = await verify_token(credentials, settings)

                    assert user.user_id == "user-123"
                    assert user.username == "testuser"


class TestRequirePermission:
    """require_permission関数のテスト"""

    def test_user_has_permission(self):
        """ユーザーが権限を持っている場合"""
        user = User(user_id="1", username="cw", roles=["caseworker"])

        # require_permissionは権限を持っているか直接チェック
        assert user.has_permission(Permission.READ_OWN_CASES) is True

    def test_user_lacks_permission(self):
        """ユーザーが権限を持っていない場合"""
        user = User(user_id="1", username="cw", roles=["caseworker"])

        # VIEW_AUDIT_LOGSはcaseworkerにはない
        assert user.has_permission(Permission.VIEW_AUDIT_LOGS) is False

    def test_require_permission_returns_callable(self):
        """require_permissionは呼び出し可能なオブジェクトを返す"""
        check_fn = require_permission(Permission.READ_OWN_CASES)
        assert callable(check_fn)


class TestRequireRole:
    """require_role関数のテスト"""

    def test_user_has_role(self):
        """ユーザーがロールを持っている場合"""
        user = User(user_id="1", username="sv", roles=["supervisor"])
        assert user.has_role("supervisor") is True

    def test_user_lacks_role(self):
        """ユーザーがロールを持っていない場合"""
        user = User(user_id="1", username="cw", roles=["caseworker"])
        assert user.has_role("admin") is False

    def test_require_role_returns_callable(self):
        """require_roleは呼び出し可能なオブジェクトを返す"""
        check_fn = require_role("supervisor")
        assert callable(check_fn)


class TestRequireAnyRole:
    """require_any_role関数のテスト"""

    def test_user_has_one_of_roles(self):
        """ユーザーがいずれかのロールを持っている場合"""
        user = User(user_id="1", username="sv", roles=["supervisor"])
        roles_to_check = ["supervisor", "admin"]
        assert any(user.has_role(role) for role in roles_to_check) is True

    def test_user_lacks_all_roles(self):
        """ユーザーがどのロールも持っていない場合"""
        user = User(user_id="1", username="cw", roles=["caseworker"])
        roles_to_check = ["supervisor", "admin"]
        assert any(user.has_role(role) for role in roles_to_check) is False

    def test_require_any_role_returns_callable(self):
        """require_any_roleは呼び出し可能なオブジェクトを返す"""
        check_fn = require_any_role(["supervisor", "admin"])
        assert callable(check_fn)


class TestGetCurrentUserOrMock:
    """get_current_user_or_mock関数のテスト"""

    @pytest.mark.asyncio
    async def test_debug_mode_no_credentials(self):
        """デバッグモードで認証情報なしの場合、モックユーザー"""
        with patch.dict("os.environ", {"DEBUG": "true"}, clear=True):
            settings = Settings()

            user = await get_current_user_or_mock(None, settings)

            assert user.username == "dev_caseworker"
            assert "caseworker" in user.roles

    @pytest.mark.asyncio
    async def test_with_credentials(self):
        """認証情報がある場合、verify_tokenを呼び出す"""
        settings = Settings()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid.token"
        )

        mock_user = User(user_id="1", username="real_user", roles=["caseworker"])

        with patch("api.dependencies.verify_token", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = mock_user

            user = await get_current_user_or_mock(credentials, settings)

            mock_verify.assert_called_once()
            assert user.username == "real_user"
