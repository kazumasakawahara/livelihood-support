"""
生活保護受給者尊厳支援データベース - 認証モジュール
Keycloak OIDC認証のStreamlit統合

TECHNICAL_STANDARDS.md 4.1 認証基盤準拠
- OpenID Connect (OIDC) 認証
- PKCE対応
- ロールベースアクセス制御 (RBAC)
"""

import os
import secrets
import hashlib
import base64
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional
import streamlit as st

try:
    import httpx
    import jwt
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


# =============================================================================
# 設定
# =============================================================================

def get_keycloak_config() -> dict:
    """Keycloak設定を環境変数から取得"""
    return {
        "url": os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
        "realm": os.getenv("KEYCLOAK_REALM", "livelihood-support"),
        "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "livelihood-support-app"),
        "redirect_uri": os.getenv("KEYCLOAK_REDIRECT_URI", "http://localhost:8501/"),
    }


def get_oidc_endpoints(config: dict) -> dict:
    """OIDCエンドポイントURLを生成"""
    base = f"{config['url']}/realms/{config['realm']}"
    return {
        "authorization": f"{base}/protocol/openid-connect/auth",
        "token": f"{base}/protocol/openid-connect/token",
        "userinfo": f"{base}/protocol/openid-connect/userinfo",
        "logout": f"{base}/protocol/openid-connect/logout",
        "jwks": f"{base}/protocol/openid-connect/certs",
    }


# =============================================================================
# PKCE (Proof Key for Code Exchange)
# =============================================================================

def generate_pkce_pair() -> tuple[str, str]:
    """
    PKCE用のcode_verifierとcode_challengeを生成

    Returns:
        tuple: (code_verifier, code_challenge)
    """
    # code_verifier: 43-128文字のランダム文字列
    code_verifier = secrets.token_urlsafe(64)

    # code_challenge: code_verifierのSHA-256ハッシュをBase64URLエンコード
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

    return code_verifier, code_challenge


# =============================================================================
# 認証フロー
# =============================================================================

def init_auth_session():
    """認証セッションの初期化"""
    if 'auth_state' not in st.session_state:
        st.session_state.auth_state = None
    if 'code_verifier' not in st.session_state:
        st.session_state.code_verifier = None
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    if 'refresh_token' not in st.session_state:
        st.session_state.refresh_token = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'token_expires_at' not in st.session_state:
        st.session_state.token_expires_at = None


def get_authorization_url() -> str:
    """
    認証URLを生成（PKCE対応）

    Returns:
        str: Keycloak認証ページへのURL
    """
    config = get_keycloak_config()
    endpoints = get_oidc_endpoints(config)

    # PKCE生成
    code_verifier, code_challenge = generate_pkce_pair()
    st.session_state.code_verifier = code_verifier

    # CSRF対策用state
    state = secrets.token_urlsafe(32)
    st.session_state.auth_state = state

    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": "openid profile email roles",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"{endpoints['authorization']}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str, state: str) -> Optional[dict]:
    """
    認証コードをトークンに交換

    Args:
        code: 認証コード
        state: CSRF検証用state

    Returns:
        トークン情報、または認証失敗時None
    """
    if not DEPENDENCIES_AVAILABLE:
        st.error("認証ライブラリがインストールされていません: uv sync を実行してください")
        return None

    # State検証（CSRF対策）
    if state != st.session_state.get('auth_state'):
        st.error("認証エラー: 不正なリクエストです")
        return None

    config = get_keycloak_config()
    endpoints = get_oidc_endpoints(config)

    data = {
        "grant_type": "authorization_code",
        "client_id": config["client_id"],
        "code": code,
        "redirect_uri": config["redirect_uri"],
        "code_verifier": st.session_state.code_verifier,
    }

    try:
        with httpx.Client() as client:
            response = client.post(
                endpoints["token"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                token_data = response.json()
                _store_tokens(token_data)
                return token_data
            else:
                st.error(f"トークン取得エラー: {response.status_code}")
                return None

    except Exception as e:
        st.error(f"認証エラー: {e}")
        return None


def _store_tokens(token_data: dict):
    """トークンをセッションに保存"""
    st.session_state.access_token = token_data.get("access_token")
    st.session_state.refresh_token = token_data.get("refresh_token")

    expires_in = token_data.get("expires_in", 1800)
    st.session_state.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

    # ユーザー情報をトークンからデコード
    try:
        # 署名検証なしでデコード（開発環境用）
        # 本番環境ではJWKSを使用して署名検証を行うこと
        payload = jwt.decode(
            token_data["access_token"],
            options={"verify_signature": False}
        )
        st.session_state.user_info = {
            "username": payload.get("preferred_username"),
            "name": payload.get("name"),
            "email": payload.get("email"),
            "roles": payload.get("realm_access", {}).get("roles", []),
        }
    except Exception:
        st.session_state.user_info = None


def refresh_access_token() -> bool:
    """
    リフレッシュトークンを使用してアクセストークンを更新

    Returns:
        bool: 更新成功時True
    """
    if not DEPENDENCIES_AVAILABLE:
        return False

    if not st.session_state.get('refresh_token'):
        return False

    config = get_keycloak_config()
    endpoints = get_oidc_endpoints(config)

    data = {
        "grant_type": "refresh_token",
        "client_id": config["client_id"],
        "refresh_token": st.session_state.refresh_token,
    }

    try:
        with httpx.Client() as client:
            response = client.post(
                endpoints["token"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                _store_tokens(response.json())
                return True

    except Exception:
        pass

    return False


def is_authenticated() -> bool:
    """
    認証済みかどうかを確認

    Returns:
        bool: 認証済みの場合True
    """
    if not st.session_state.get('access_token'):
        return False

    # トークン有効期限チェック
    expires_at = st.session_state.get('token_expires_at')
    if expires_at and datetime.now() >= expires_at:
        # トークンリフレッシュを試行
        if not refresh_access_token():
            return False

    return True


def get_current_user() -> Optional[dict]:
    """
    現在のユーザー情報を取得

    Returns:
        ユーザー情報、または未認証時None
    """
    if not is_authenticated():
        return None
    return st.session_state.get('user_info')


def has_role(role: str) -> bool:
    """
    ユーザーが指定ロールを持っているか確認

    Args:
        role: 確認するロール名

    Returns:
        bool: ロールを持っている場合True
    """
    user = get_current_user()
    if not user:
        return False
    return role in user.get("roles", [])


def require_role(role: str) -> bool:
    """
    指定ロールを要求（なければエラー表示）

    Args:
        role: 必要なロール名

    Returns:
        bool: ロールを持っている場合True
    """
    if not has_role(role):
        st.error(f"アクセス権限がありません。必要なロール: {role}")
        return False
    return True


# =============================================================================
# ログアウト
# =============================================================================

def logout():
    """ログアウト処理"""
    config = get_keycloak_config()
    endpoints = get_oidc_endpoints(config)

    # セッションクリア
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user_info = None
    st.session_state.token_expires_at = None
    st.session_state.auth_state = None
    st.session_state.code_verifier = None


def get_logout_url() -> str:
    """Keycloakログアウト画面のURLを取得"""
    config = get_keycloak_config()
    endpoints = get_oidc_endpoints(config)

    params = {
        "post_logout_redirect_uri": config["redirect_uri"],
        "client_id": config["client_id"],
    }

    return f"{endpoints['logout']}?{urllib.parse.urlencode(params)}"


# =============================================================================
# Streamlit UIコンポーネント
# =============================================================================

def render_login_button():
    """ログインボタンを表示"""
    auth_url = get_authorization_url()
    st.markdown(
        f'<a href="{auth_url}" target="_self">'
        '<button style="background-color: #4CAF50; color: white; '
        'padding: 10px 24px; border: none; cursor: pointer; '
        'border-radius: 4px; font-size: 16px;">'
        'ログイン'
        '</button></a>',
        unsafe_allow_html=True
    )


def render_user_info():
    """ユーザー情報とログアウトボタンを表示"""
    user = get_current_user()
    if user:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"ログイン中: **{user.get('name', user.get('username'))}**")
            roles = user.get('roles', [])
            app_roles = [r for r in roles if r in ['caseworker', 'supervisor', 'admin', 'auditor']]
            if app_roles:
                st.caption(f"ロール: {', '.join(app_roles)}")
        with col2:
            if st.button("ログアウト"):
                logout()
                st.rerun()


def handle_oauth_callback():
    """OAuthコールバックを処理"""
    query_params = st.query_params
    code = query_params.get("code")
    state = query_params.get("state")

    if code and state:
        token = exchange_code_for_token(code, state)
        if token:
            # クエリパラメータをクリア
            st.query_params.clear()
            st.rerun()


def require_authentication():
    """
    認証を要求（認証されていない場合はログイン画面を表示）

    Returns:
        bool: 認証済みの場合True
    """
    init_auth_session()
    handle_oauth_callback()

    if not is_authenticated():
        st.warning("このページにアクセスするにはログインが必要です。")
        render_login_button()
        return False

    return True
