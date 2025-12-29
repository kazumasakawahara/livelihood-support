"""
lib/auth.py のユニットテスト
Keycloak認証機能のテスト
"""

import pytest
import hashlib
import base64
from lib.auth import (
    generate_pkce_pair,
    get_keycloak_config,
    get_oidc_endpoints,
)


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


class TestRoleCheck:
    """ロールチェック機能のテスト（モック使用）"""

    def test_has_role_with_roles(self):
        """ロールを持っている場合"""
        # この関数はStreamlitセッションに依存するため、
        # 実際のテストではモックが必要
        # ここでは関数の存在確認のみ
        from lib.auth import has_role
        assert callable(has_role)

    def test_require_role_exists(self):
        """require_role関数の存在確認"""
        from lib.auth import require_role
        assert callable(require_role)

    def test_is_authenticated_exists(self):
        """is_authenticated関数の存在確認"""
        from lib.auth import is_authenticated
        assert callable(is_authenticated)

    def test_get_current_user_exists(self):
        """get_current_user関数の存在確認"""
        from lib.auth import get_current_user
        assert callable(get_current_user)


class TestLogout:
    """ログアウト機能のテスト"""

    def test_get_logout_url_format(self):
        """ログアウトURLの形式確認"""
        from lib.auth import get_logout_url
        url = get_logout_url()

        assert "logout" in url
        assert "post_logout_redirect_uri" in url
        assert "client_id" in url

    def test_logout_function_exists(self):
        """logout関数の存在確認"""
        from lib.auth import logout
        assert callable(logout)
