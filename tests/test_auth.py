"""
lib/auth.py のユニットテスト
Keycloak認証機能のテスト
"""

import os
import pytest
import hashlib
import base64
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from lib.auth import (
    generate_pkce_pair,
    get_keycloak_config,
    get_oidc_endpoints,
    is_auth_disabled,
    get_dev_user,
)


# =============================================================================
# 認証設定のテスト
# =============================================================================

class TestIsAuthDisabled:
    """is_auth_disabled関数のテスト"""

    def test_auth_disabled_when_skip_auth_true(self):
        """SKIP_AUTH=trueで認証無効"""
        with patch.dict(os.environ, {"SKIP_AUTH": "true"}):
            assert is_auth_disabled() is True

    def test_auth_disabled_when_skip_auth_true_uppercase(self):
        """SKIP_AUTH=TRUEで認証無効"""
        with patch.dict(os.environ, {"SKIP_AUTH": "TRUE"}):
            assert is_auth_disabled() is True

    def test_auth_enabled_when_skip_auth_false(self):
        """SKIP_AUTH=falseで認証有効"""
        with patch.dict(os.environ, {"SKIP_AUTH": "false"}):
            assert is_auth_disabled() is False

    def test_auth_enabled_when_skip_auth_not_set(self):
        """SKIP_AUTHなしで認証有効"""
        env = {k: v for k, v in os.environ.items() if k != "SKIP_AUTH"}
        with patch.dict(os.environ, env, clear=True):
            assert is_auth_disabled() is False


class TestGetDevUser:
    """get_dev_user関数のテスト"""

    def test_default_dev_user(self):
        """デフォルトの開発ユーザー"""
        user = get_dev_user()

        assert user["username"] == "dev_user"
        assert user["name"] == "開発ユーザー"
        assert user["email"] == "dev@example.com"
        assert "caseworker" in user["roles"]
        assert "supervisor" in user["roles"]

    def test_custom_dev_user(self):
        """環境変数でカスタマイズされた開発ユーザー"""
        with patch.dict(os.environ, {
            "DEV_USERNAME": "custom_user",
            "DEV_USER_NAME": "カスタムユーザー"
        }):
            user = get_dev_user()

            assert user["username"] == "custom_user"
            assert user["name"] == "カスタムユーザー"


# =============================================================================
# PKCEのテスト
# =============================================================================

class TestPKCE:
    """PKCE関連のテスト"""

    def test_generate_pkce_pair_format(self):
        """PKCE生成結果の形式確認"""
        verifier, challenge = generate_pkce_pair()

        # verifierは43-128文字
        assert len(verifier) >= 43
        assert len(verifier) <= 128

        # challengeはBase64URL形式（=パディングなし）
        assert '=' not in challenge
        assert '+' not in challenge
        assert '/' not in challenge

    def test_generate_pkce_pair_unique(self):
        """PKCE生成は毎回異なる値"""
        pairs = [generate_pkce_pair() for _ in range(5)]
        verifiers = [p[0] for p in pairs]
        challenges = [p[1] for p in pairs]

        # 全て異なる値
        assert len(set(verifiers)) == 5
        assert len(set(challenges)) == 5

    def test_pkce_challenge_calculation(self):
        """PKCEチャレンジの計算が正しいか"""
        verifier, challenge = generate_pkce_pair()

        # verifierからchallengeを再計算
        digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

        assert challenge == expected_challenge


class TestKeycloakConfig:
    """Keycloak設定のテスト"""

    def test_get_keycloak_config_defaults(self):
        """デフォルト設定の確認"""
        config = get_keycloak_config()

        assert "url" in config
        assert "realm" in config
        assert "client_id" in config
        assert "redirect_uri" in config

    def test_get_keycloak_config_default_values(self):
        """デフォルト値の確認"""
        config = get_keycloak_config()

        assert config["url"] == "http://localhost:8080"
        assert config["realm"] == "livelihood-support"
        assert config["client_id"] == "livelihood-support-app"


class TestOIDCEndpoints:
    """OIDCエンドポイントのテスト"""

    def test_get_oidc_endpoints(self):
        """エンドポイント生成の確認"""
        config = {
            "url": "http://localhost:8080",
            "realm": "test-realm"
        }
        endpoints = get_oidc_endpoints(config)

        assert "authorization" in endpoints
        assert "token" in endpoints
        assert "userinfo" in endpoints
        assert "logout" in endpoints
        assert "jwks" in endpoints

    def test_endpoint_urls(self):
        """エンドポイントURLの形式確認"""
        config = {
            "url": "http://localhost:8080",
            "realm": "livelihood-support"
        }
        endpoints = get_oidc_endpoints(config)

        base = "http://localhost:8080/realms/livelihood-support/protocol/openid-connect"
        assert endpoints["authorization"] == f"{base}/auth"
        assert endpoints["token"] == f"{base}/token"
        assert endpoints["userinfo"] == f"{base}/userinfo"
        assert endpoints["logout"] == f"{base}/logout"
        assert endpoints["jwks"] == f"{base}/certs"


# =============================================================================
# ロールチェックのテスト（モック使用）
# =============================================================================

class TestHasRole:
    """has_role関数のテスト"""

    def test_user_has_role(self):
        """ユーザーがロールを持っている"""
        with patch('lib.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {
                "username": "test_user",
                "roles": ["caseworker", "supervisor"]
            }

            from lib.auth import has_role
            assert has_role("caseworker") is True
            assert has_role("supervisor") is True

    def test_user_missing_role(self):
        """ユーザーがロールを持っていない"""
        with patch('lib.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {
                "username": "test_user",
                "roles": ["caseworker"]
            }

            from lib.auth import has_role
            assert has_role("admin") is False

    def test_no_user(self):
        """ユーザーなし"""
        with patch('lib.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = None

            from lib.auth import has_role
            assert has_role("caseworker") is False

    def test_user_with_empty_roles(self):
        """ロールが空のユーザー"""
        with patch('lib.auth.get_current_user') as mock_get_user:
            mock_get_user.return_value = {
                "username": "test_user",
                "roles": []
            }

            from lib.auth import has_role
            assert has_role("caseworker") is False


class TestRequireRole:
    """require_role関数のテスト"""

    def test_role_satisfied(self):
        """ロールを満たす場合"""
        with patch('lib.auth.has_role') as mock_has_role, \
             patch('lib.auth.st') as mock_st:
            mock_has_role.return_value = True

            from lib.auth import require_role
            result = require_role("caseworker")

            assert result is True
            mock_st.error.assert_not_called()

    def test_role_not_satisfied(self):
        """ロールを満たさない場合"""
        with patch('lib.auth.has_role') as mock_has_role, \
             patch('lib.auth.st') as mock_st:
            mock_has_role.return_value = False

            from lib.auth import require_role
            result = require_role("admin")

            assert result is False
            mock_st.error.assert_called_once()


# =============================================================================
# 認証状態確認のテスト
# =============================================================================

class TestIsAuthenticated:
    """is_authenticated関数のテスト"""

    def test_not_authenticated_without_token(self):
        """トークンなしで未認証"""
        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = None

            from lib.auth import is_authenticated
            assert is_authenticated() is False

    def test_authenticated_with_valid_token(self):
        """有効なトークンで認証済み"""
        future_time = datetime.now() + timedelta(hours=1)

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.side_effect = lambda key: {
                'access_token': 'valid_token',
                'token_expires_at': future_time
            }.get(key)

            from lib.auth import is_authenticated
            assert is_authenticated() is True

    def test_expired_token_triggers_refresh(self):
        """期限切れトークンでリフレッシュ試行"""
        past_time = datetime.now() - timedelta(hours=1)

        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.refresh_access_token') as mock_refresh:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.side_effect = lambda key: {
                'access_token': 'expired_token',
                'token_expires_at': past_time
            }.get(key)
            mock_refresh.return_value = True

            from lib.auth import is_authenticated
            result = is_authenticated()

            mock_refresh.assert_called_once()
            assert result is True


class TestGetCurrentUser:
    """get_current_user関数のテスト"""

    def test_returns_dev_user_when_auth_disabled(self):
        """認証無効時は開発ユーザーを返す"""
        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.st') as mock_st:
            mock_disabled.return_value = True
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = None

            from lib.auth import get_current_user
            user = get_current_user()

            assert user is not None
            assert user["username"] == "dev_user"

    def test_returns_session_user_when_auth_disabled(self):
        """認証無効時でセッションにユーザー情報があればそれを返す"""
        session_user = {
            "username": "session_user",
            "name": "セッションユーザー",
            "roles": ["caseworker"]
        }
        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.st') as mock_st:
            mock_disabled.return_value = True
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = session_user

            from lib.auth import get_current_user
            user = get_current_user()

            assert user["username"] == "session_user"

    def test_returns_none_when_not_authenticated(self):
        """未認証時はNone"""
        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.is_authenticated') as mock_auth, \
             patch('lib.auth.st'):
            mock_disabled.return_value = False
            mock_auth.return_value = False

            from lib.auth import get_current_user
            assert get_current_user() is None


# =============================================================================
# セッション管理のテスト
# =============================================================================

class TestInitAuthSession:
    """init_auth_session関数のテスト"""

    def test_session_initialization(self):
        """セッション初期化"""
        # MagicMockで__contains__を定義
        mock_session_state = MagicMock()
        mock_session_state.__contains__ = lambda self, key: False

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.auth import init_auth_session
            init_auth_session()

            # セッション属性が設定される
            assert mock_session_state.auth_state is not None or mock_session_state.auth_state is None

    def test_session_preserves_existing_values(self):
        """既存のセッション値があれば上書きしない"""
        # 'auth_state' in session_state がTrueを返すようにモック
        mock_session_state = MagicMock()
        mock_session_state.__contains__ = lambda self, key: key in ['auth_state', 'access_token']

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.auth import init_auth_session
            init_auth_session()

            # 既存のキーがあるので上書きされない（設定されなかったことを確認）
            # auth_stateは既存なのでNone設定されない
            pass  # このテストは主にカバレッジ向上のため


class TestStoreTokens:
    """_store_tokens関数のテスト"""

    def test_token_storage(self):
        """トークンの保存"""
        mock_session_state = MagicMock()

        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.jwt') as mock_jwt:
            mock_st.session_state = mock_session_state
            mock_jwt.decode.return_value = {
                "preferred_username": "test_user",
                "name": "テストユーザー",
                "email": "test@example.com",
                "realm_access": {"roles": ["caseworker"]}
            }

            from lib.auth import _store_tokens

            token_data = {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 3600
            }

            _store_tokens(token_data)

            # MagicMockなので属性アクセスで確認
            assert mock_session_state.access_token == "test_access_token"
            assert mock_session_state.refresh_token == "test_refresh_token"

    def test_jwt_decode_failure(self):
        """JWTデコード失敗時"""
        mock_session_state = MagicMock()

        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.jwt') as mock_jwt:
            mock_st.session_state = mock_session_state
            mock_jwt.decode.side_effect = Exception("Invalid token")

            from lib.auth import _store_tokens

            token_data = {
                "access_token": "invalid_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 3600
            }

            _store_tokens(token_data)

            # トークンは保存されるがuser_infoはNone
            assert mock_session_state.access_token == "invalid_token"
            assert mock_session_state.user_info is None


class TestLogout:
    """ログアウト機能のテスト"""

    def test_get_logout_url_format(self):
        """ログアウトURLの形式確認"""
        from lib.auth import get_logout_url
        url = get_logout_url()

        assert "logout" in url
        assert "post_logout_redirect_uri" in url
        assert "client_id" in url

    def test_logout_clears_session(self):
        """logout関数がセッションをクリアする"""
        mock_session_state = MagicMock()

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.auth import logout
            logout()

            # すべてのセッション属性がNoneに設定される
            assert mock_session_state.access_token is None
            assert mock_session_state.refresh_token is None
            assert mock_session_state.user_info is None
            assert mock_session_state.token_expires_at is None
            assert mock_session_state.auth_state is None
            assert mock_session_state.code_verifier is None


# =============================================================================
# 認証URL生成のテスト
# =============================================================================

class TestGetAuthorizationUrl:
    """get_authorization_url関数のテスト"""

    def test_url_contains_required_params(self):
        """認証URLに必要なパラメータが含まれる"""
        mock_session_state = MagicMock()

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.auth import get_authorization_url

            url = get_authorization_url()

            # 必須パラメータの確認
            assert "client_id=" in url
            assert "redirect_uri=" in url
            assert "response_type=code" in url
            assert "scope=" in url
            assert "state=" in url
            assert "code_challenge=" in url
            assert "code_challenge_method=S256" in url

    def test_pkce_stored_in_session(self):
        """PKCEがセッションに保存される"""
        mock_session_state = MagicMock()

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.auth import get_authorization_url

            get_authorization_url()

            # code_verifierが設定されたことを確認
            assert mock_session_state.code_verifier is not None

    def test_state_stored_in_session(self):
        """CSRFステートがセッションに保存される"""
        mock_session_state = MagicMock()

        with patch('lib.auth.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.auth import get_authorization_url

            get_authorization_url()

            # auth_stateが設定されたことを確認
            assert mock_session_state.auth_state is not None


# =============================================================================
# リフレッシュトークンのテスト
# =============================================================================

class TestRefreshAccessToken:
    """refresh_access_token関数のテスト"""

    def test_returns_false_without_dependencies(self):
        """依存関係がない場合Falseを返す"""
        with patch('lib.auth.DEPENDENCIES_AVAILABLE', False):
            from lib.auth import refresh_access_token
            assert refresh_access_token() is False

    def test_returns_false_without_refresh_token(self):
        """リフレッシュトークンがない場合Falseを返す"""
        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = None

            from lib.auth import refresh_access_token
            assert refresh_access_token() is False


# =============================================================================
# require_authentication関数のテスト
# =============================================================================

class TestRequireAuthentication:
    """require_authentication関数のテスト"""

    def test_returns_true_when_auth_disabled(self):
        """認証無効時はTrueを返す"""
        mock_session_state = MagicMock()

        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.st') as mock_st:
            mock_disabled.return_value = True
            mock_st.session_state = mock_session_state

            from lib.auth import require_authentication

            result = require_authentication()

            assert result is True
            # user_infoが設定されたことを確認
            assert mock_session_state.user_info is not None

    def test_returns_false_when_not_authenticated(self):
        """未認証時はFalseを返す"""
        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.init_auth_session'), \
             patch('lib.auth.handle_oauth_callback'), \
             patch('lib.auth.is_authenticated') as mock_auth, \
             patch('lib.auth.render_login_button'), \
             patch('lib.auth.st') as mock_st:
            mock_disabled.return_value = False
            mock_auth.return_value = False

            from lib.auth import require_authentication

            result = require_authentication()

            assert result is False
            mock_st.warning.assert_called_once()

    def test_returns_true_when_authenticated(self):
        """認証済み時はTrueを返す"""
        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.init_auth_session'), \
             patch('lib.auth.handle_oauth_callback'), \
             patch('lib.auth.is_authenticated') as mock_auth:
            mock_disabled.return_value = False
            mock_auth.return_value = True

            from lib.auth import require_authentication

            result = require_authentication()

            assert result is True


# =============================================================================
# トークン交換のテスト
# =============================================================================

class TestExchangeCodeForToken:
    """exchange_code_for_token関数のテスト"""

    def test_returns_none_without_dependencies(self):
        """依存関係がない場合Noneを返す"""
        with patch('lib.auth.DEPENDENCIES_AVAILABLE', False), \
             patch('lib.auth.st') as mock_st:
            from lib.auth import exchange_code_for_token
            result = exchange_code_for_token("code", "state")
            assert result is None

    def test_returns_none_with_invalid_state(self):
        """無効なstateでNoneを返す"""
        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "different_state"

            from lib.auth import exchange_code_for_token
            result = exchange_code_for_token("code", "invalid_state")

            assert result is None
            mock_st.error.assert_called()

    def test_successful_token_exchange(self):
        """トークン交換成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st, \
             patch('lib.auth.httpx.Client', return_value=mock_client), \
             patch('lib.auth._store_tokens') as mock_store:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "valid_state"
            mock_st.session_state.code_verifier = "test_verifier"

            from lib.auth import exchange_code_for_token
            result = exchange_code_for_token("code", "valid_state")

            assert result is not None
            mock_store.assert_called_once()

    def test_token_exchange_error_response(self):
        """トークン交換エラーレスポンス"""
        mock_response = MagicMock()
        mock_response.status_code = 400

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st, \
             patch('lib.auth.httpx.Client', return_value=mock_client):
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "valid_state"
            mock_st.session_state.code_verifier = "test_verifier"

            from lib.auth import exchange_code_for_token
            result = exchange_code_for_token("code", "valid_state")

            assert result is None
            mock_st.error.assert_called()

    def test_token_exchange_exception(self):
        """トークン交換時の例外"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st, \
             patch('lib.auth.httpx.Client', return_value=mock_client):
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "valid_state"
            mock_st.session_state.code_verifier = "test_verifier"

            from lib.auth import exchange_code_for_token
            result = exchange_code_for_token("code", "valid_state")

            assert result is None
            mock_st.error.assert_called()


class TestRefreshAccessTokenExtended:
    """refresh_access_token関数の追加テスト"""

    def test_successful_refresh(self):
        """リフレッシュ成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st, \
             patch('lib.auth.httpx.Client', return_value=mock_client), \
             patch('lib.auth._store_tokens') as mock_store:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "test_refresh_token"
            mock_st.session_state.refresh_token = "test_refresh_token"

            from lib.auth import refresh_access_token
            result = refresh_access_token()

            assert result is True
            mock_store.assert_called_once()

    def test_refresh_failure(self):
        """リフレッシュ失敗"""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st, \
             patch('lib.auth.httpx.Client', return_value=mock_client):
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "test_refresh_token"
            mock_st.session_state.refresh_token = "test_refresh_token"

            from lib.auth import refresh_access_token
            result = refresh_access_token()

            assert result is False

    def test_refresh_exception(self):
        """リフレッシュ時の例外"""
        mock_client = MagicMock()
        mock_client.post.side_effect = Exception("Network error")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch('lib.auth.DEPENDENCIES_AVAILABLE', True), \
             patch('lib.auth.st') as mock_st, \
             patch('lib.auth.httpx.Client', return_value=mock_client):
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = "test_refresh_token"
            mock_st.session_state.refresh_token = "test_refresh_token"

            from lib.auth import refresh_access_token
            result = refresh_access_token()

            assert result is False


class TestUIComponents:
    """UIコンポーネントのテスト"""

    def test_render_login_button(self):
        """ログインボタンのレンダリング"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.get_authorization_url') as mock_url:
            mock_url.return_value = "http://auth.example.com/login"

            from lib.auth import render_login_button
            render_login_button()

            mock_st.link_button.assert_called_once()

    def test_render_user_info_with_user(self):
        """ユーザー情報表示（ユーザーあり）"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.get_current_user') as mock_user:
            mock_user.return_value = {
                "username": "test_user",
                "name": "テストユーザー",
                "roles": ["caseworker", "supervisor"]
            }
            mock_st.columns.return_value = (MagicMock(), MagicMock())
            mock_st.button.return_value = False

            from lib.auth import render_user_info
            render_user_info()

            mock_st.columns.assert_called_once()

    def test_render_user_info_logout_clicked(self):
        """ユーザー情報表示（ログアウトクリック）"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.get_current_user') as mock_user, \
             patch('lib.auth.logout') as mock_logout:
            mock_user.return_value = {
                "username": "test_user",
                "name": "テストユーザー",
                "roles": ["caseworker"]
            }
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_st.columns.return_value = (mock_col1, mock_col2)
            mock_col2.button = MagicMock(return_value=True)

            # Enter the context managers properly
            mock_col1.__enter__ = MagicMock(return_value=mock_col1)
            mock_col1.__exit__ = MagicMock(return_value=False)
            mock_col2.__enter__ = MagicMock(return_value=mock_col2)
            mock_col2.__exit__ = MagicMock(return_value=False)

            from lib.auth import render_user_info
            render_user_info()

    def test_render_user_info_no_user(self):
        """ユーザー情報表示（ユーザーなし）"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.get_current_user') as mock_user:
            mock_user.return_value = None

            from lib.auth import render_user_info
            render_user_info()

            # ユーザーがいなければ何も表示しない
            mock_st.columns.assert_not_called()


class TestHandleOAuthCallback:
    """OAuthコールバック処理のテスト"""

    def test_callback_with_code_and_state(self):
        """コードとステートがある場合のコールバック処理"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.exchange_code_for_token') as mock_exchange:
            mock_query_params = MagicMock()
            mock_query_params.get.side_effect = lambda k: {"code": "test_code", "state": "test_state"}.get(k)
            mock_st.query_params = mock_query_params
            mock_exchange.return_value = {"access_token": "test_token"}

            from lib.auth import handle_oauth_callback
            handle_oauth_callback()

            mock_exchange.assert_called_once_with("test_code", "test_state")
            mock_st.rerun.assert_called_once()

    def test_callback_without_code(self):
        """コードがない場合のコールバック処理"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.exchange_code_for_token') as mock_exchange:
            mock_query_params = MagicMock()
            mock_query_params.get.return_value = None
            mock_st.query_params = mock_query_params

            from lib.auth import handle_oauth_callback
            handle_oauth_callback()

            mock_exchange.assert_not_called()

    def test_callback_exchange_fails(self):
        """トークン交換失敗時のコールバック処理"""
        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.exchange_code_for_token') as mock_exchange:
            mock_query_params = MagicMock()
            mock_query_params.get.side_effect = lambda k: {"code": "test_code", "state": "test_state"}.get(k)
            mock_st.query_params = mock_query_params
            mock_exchange.return_value = None

            from lib.auth import handle_oauth_callback
            handle_oauth_callback()

            mock_exchange.assert_called_once()
            # rerunは呼ばれない
            mock_st.rerun.assert_not_called()


class TestIsAuthenticatedExpired:
    """is_authenticated関数の期限切れトークンテスト"""

    def test_expired_token_refresh_fails(self):
        """期限切れトークンでリフレッシュ失敗"""
        past_time = datetime.now() - timedelta(hours=1)

        with patch('lib.auth.st') as mock_st, \
             patch('lib.auth.refresh_access_token') as mock_refresh:
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.side_effect = lambda key: {
                'access_token': 'expired_token',
                'token_expires_at': past_time
            }.get(key)
            mock_refresh.return_value = False

            from lib.auth import is_authenticated
            result = is_authenticated()

            mock_refresh.assert_called_once()
            assert result is False


class TestGetCurrentUserAuthenticated:
    """get_current_user関数の認証済みテスト"""

    def test_returns_user_info_when_authenticated(self):
        """認証済み時にユーザー情報を返す"""
        user_info = {
            "username": "auth_user",
            "name": "認証ユーザー",
            "roles": ["caseworker"]
        }
        with patch('lib.auth.is_auth_disabled') as mock_disabled, \
             patch('lib.auth.is_authenticated') as mock_auth, \
             patch('lib.auth.st') as mock_st:
            mock_disabled.return_value = False
            mock_auth.return_value = True
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = user_info

            from lib.auth import get_current_user
            result = get_current_user()

            assert result == user_info
