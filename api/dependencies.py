"""
FastAPI依存関係（認証・DB接続）
TECHNICAL_STANDARDS.md 4.1 認証・認可準拠
"""

import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from functools import lru_cache
import uuid

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    import jwt
    import jwt.algorithms
    import httpx
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from lib.db_connection import get_driver


# =============================================================================
# 設定
# =============================================================================

class Settings:
    """アプリケーション設定"""

    def __init__(self):
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
        self.keycloak_realm = os.getenv("KEYCLOAK_REALM", "livelihood-support")
        self.keycloak_client_id = os.getenv("KEYCLOAK_CLIENT_ID", "livelihood-support-app")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.auth_skip = os.getenv("AUTH_SKIP", "false").lower() == "true"

    @property
    def jwks_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# =============================================================================
# JWKSキャッシュ
# =============================================================================

class JWKSCache:
    """
    JWKS (JSON Web Key Set) キャッシュ

    Keycloakの公開鍵をキャッシュして、
    毎リクエストでの取得を避ける
    """

    def __init__(self, cache_duration: timedelta = timedelta(hours=1)):
        self._keys: dict = {}
        self._expires_at: Optional[datetime] = None
        self._cache_duration = cache_duration

    def get_key(self, kid: str, settings: Settings) -> Optional[dict]:
        """
        指定されたkidの公開鍵を取得

        Args:
            kid: Key ID (JWTヘッダーから取得)
            settings: アプリケーション設定

        Returns:
            JWK辞書、または見つからない場合None
        """
        if self._is_expired():
            self._refresh_keys(settings)

        return self._keys.get(kid)

    def _is_expired(self) -> bool:
        """キャッシュが期限切れかどうか"""
        if self._expires_at is None:
            return True
        return datetime.now() >= self._expires_at

    def _refresh_keys(self, settings: Settings):
        """JWKSを再取得してキャッシュを更新"""
        if not JWT_AVAILABLE:
            return

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(settings.jwks_url)
                response.raise_for_status()
                jwks = response.json()

                self._keys = {key["kid"]: key for key in jwks.get("keys", [])}
                self._expires_at = datetime.now() + self._cache_duration

        except Exception as e:
            # JWKSの取得に失敗した場合、既存のキャッシュがあれば使用
            if not self._keys:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"認証サーバーに接続できません: {e}",
                )

    def clear(self):
        """キャッシュをクリア"""
        self._keys = {}
        self._expires_at = None


# グローバルJWKSキャッシュインスタンス
_jwks_cache = JWKSCache()


# =============================================================================
# 権限定義
# =============================================================================

class Permission(str, Enum):
    """権限種別"""
    READ_OWN_CASES = "read:own_cases"
    WRITE_OWN_CASES = "write:own_cases"
    READ_TEAM_CASES = "read:team_cases"
    READ_ALL_CASES = "read:all_cases"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT_LOGS = "view:audit_logs"
    SYSTEM_ADMIN = "system:admin"


# ロール → 権限マッピング
ROLE_PERMISSIONS = {
    "caseworker": [Permission.READ_OWN_CASES, Permission.WRITE_OWN_CASES],
    "supervisor": [
        Permission.READ_OWN_CASES,
        Permission.WRITE_OWN_CASES,
        Permission.READ_TEAM_CASES,
        Permission.VIEW_AUDIT_LOGS,
    ],
    "admin": [Permission.SYSTEM_ADMIN],  # 全権限
    "auditor": [Permission.VIEW_AUDIT_LOGS],  # 監査ログ閲覧のみ
}


# =============================================================================
# ユーザーモデル
# =============================================================================

class User:
    """認証済みユーザー"""

    def __init__(
        self,
        user_id: str,
        username: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ):
        self.user_id = user_id
        self.username = username
        self.name = name or username
        self.email = email
        self.roles = roles or []

    @property
    def permissions(self) -> set[Permission]:
        """ユーザーの権限セットを取得"""
        perms = set()
        for role in self.roles:
            if role in ROLE_PERMISSIONS:
                perms.update(ROLE_PERMISSIONS[role])
        # adminは全権限
        if "admin" in self.roles:
            perms = set(Permission)
        return perms

    def has_permission(self, permission: Permission) -> bool:
        """権限チェック"""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """ロールチェック"""
        return role in self.roles


# =============================================================================
# JWT認証
# =============================================================================

security = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    JWTトークンを検証してユーザー情報を返す

    本番環境ではJWKSを使用して署名検証を行う。
    開発環境(debug=True)では署名検証をスキップ。

    Raises:
        HTTPException: 認証エラー
    """
    if not JWT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証ライブラリが利用できません",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        if settings.debug:
            # 開発環境: 署名検証をスキップ
            payload = jwt.decode(token, options={"verify_signature": False})
        else:
            # 本番環境: JWKSから公開鍵を取得して署名検証
            # ヘッダーからkidを取得
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="トークンにkidがありません",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # JWKSから公開鍵を取得
            jwk = _jwks_cache.get_key(kid, settings)
            if not jwk:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="公開鍵が見つかりません",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # JWKをPEM形式の公開鍵に変換
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)

            # トークンを検証してデコード
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=settings.issuer,
                audience=settings.keycloak_client_id,
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

        # ユーザー情報を抽出
        user_id = payload.get("sub", "")
        username = payload.get("preferred_username", "")
        name = payload.get("name")
        email = payload.get("email")
        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])

        # リソースアクセスからもロールを取得
        resource_access = payload.get("resource_access", {})
        for resource_roles in resource_access.values():
            roles.extend(resource_roles.get("roles", []))

        # アプリケーション固有のロールのみ抽出（重複排除）
        app_roles = list(set(r for r in roles if r in ROLE_PERMISSIONS.keys()))

        return User(
            user_id=user_id,
            username=username,
            name=name,
            email=email,
            roles=app_roles,
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの有効期限が切れています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンのaudienceが不正です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンのissuerが不正です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"無効なトークンです: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(user: User = Depends(verify_token)) -> User:
    """現在の認証済みユーザーを取得"""
    return user


# =============================================================================
# 権限チェック依存関係
# =============================================================================

def require_permission(permission: Permission):
    """特定の権限を要求するDependency"""

    async def check_permission(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限がありません: {permission.value}",
            )
        return user

    return check_permission


def require_role(role: str):
    """特定のロールを要求するDependency"""

    async def check_role(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"必要なロール: {role}",
            )
        return user

    return check_role


def require_any_role(roles: list[str]):
    """いずれかのロールを要求するDependency"""

    async def check_role(user: User = Depends(get_current_user)) -> User:
        if not any(user.has_role(role) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"必要なロール: {', '.join(roles)}",
            )
        return user

    return check_role


# =============================================================================
# リクエストコンテキスト
# =============================================================================

def get_request_id(request: Request) -> str:
    """リクエストIDを取得または生成"""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    return request_id


# =============================================================================
# 開発用: モックユーザー
# =============================================================================

def get_mock_user() -> User:
    """開発用モックユーザー"""
    return User(
        user_id="dev-user-001",
        username="dev_caseworker",
        name="開発用ケースワーカー",
        email="dev@example.com",
        roles=["caseworker"],
    )


async def get_current_user_or_mock(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> User:
    """
    認証ユーザーを取得、または開発モードでモックユーザーを返す
    """
    if settings.debug and credentials is None:
        # デバッグモードで認証なしの場合はモックユーザー
        return get_mock_user()

    return await verify_token(credentials, settings)
