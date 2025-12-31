"""
E2E Test Configuration
Playwright fixtures and shared configuration
"""

import os
import time
import pytest
import subprocess
import socket
from contextlib import closing
from typing import Generator
from playwright.sync_api import Page, Playwright, APIRequestContext


# =============================================================================
# 環境設定
# =============================================================================

# テスト対象URL
API_BASE_URL = os.getenv("E2E_API_URL", "http://localhost:8000")
STREAMLIT_BASE_URL = os.getenv("E2E_STREAMLIT_URL", "http://localhost:8501")
KEYCLOAK_URL = os.getenv("E2E_KEYCLOAK_URL", "http://localhost:8080")

# テストユーザー
TEST_USER = {
    "username": "caseworker1",
    "password": "caseworker123",
    "role": "caseworker",
}


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """ポートが開いているか確認"""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def wait_for_service(host: str, port: int, timeout: float = 30.0) -> bool:
    """サービスの起動を待機"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_open(host, port):
            return True
        time.sleep(0.5)
    return False


# =============================================================================
# サービス状態確認フィクスチャ
# =============================================================================

@pytest.fixture(scope="session")
def api_available() -> bool:
    """APIサーバーが利用可能か確認"""
    return is_port_open("localhost", 8000)


@pytest.fixture(scope="session")
def streamlit_available() -> bool:
    """Streamlitサーバーが利用可能か確認"""
    return is_port_open("localhost", 8501)


@pytest.fixture(scope="session")
def keycloak_available() -> bool:
    """Keycloakサーバーが利用可能か確認"""
    return is_port_open("localhost", 8080)


@pytest.fixture(scope="session")
def neo4j_available() -> bool:
    """Neo4jサーバーが利用可能か確認"""
    return is_port_open("localhost", 7688)


# =============================================================================
# URL フィクスチャ
# =============================================================================

@pytest.fixture(scope="session")
def api_url() -> str:
    """API base URL"""
    return API_BASE_URL


@pytest.fixture(scope="session")
def streamlit_url() -> str:
    """Streamlit base URL"""
    return STREAMLIT_BASE_URL


@pytest.fixture(scope="session")
def keycloak_url() -> str:
    """Keycloak base URL"""
    return KEYCLOAK_URL


# =============================================================================
# APIリクエストコンテキスト
# =============================================================================

@pytest.fixture(scope="session")
def api_context(playwright: Playwright, api_available: bool) -> Generator[APIRequestContext, None, None]:
    """APIリクエストコンテキスト（セッションスコープ）"""
    if not api_available:
        pytest.skip("API server is not running")

    context = playwright.request.new_context(
        base_url=API_BASE_URL,
        extra_http_headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    yield context
    context.dispose()


@pytest.fixture
def auth_api_context(
    playwright: Playwright,
    api_available: bool,
    keycloak_available: bool,
) -> Generator[APIRequestContext, None, None]:
    """認証済みAPIリクエストコンテキスト"""
    if not api_available:
        pytest.skip("API server is not running")

    # 認証トークン取得（Keycloakが利用可能な場合）
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    if keycloak_available:
        try:
            token_context = playwright.request.new_context()
            token_response = token_context.post(
                f"{KEYCLOAK_URL}/realms/livelihood-support/protocol/openid-connect/token",
                form={
                    "grant_type": "password",
                    "client_id": "livelihood-support-app",
                    "username": TEST_USER["username"],
                    "password": TEST_USER["password"],
                },
            )
            if token_response.ok:
                token_data = token_response.json()
                headers["Authorization"] = f"Bearer {token_data['access_token']}"
            token_context.dispose()
        except Exception:
            pass  # 認証なしで続行

    context = playwright.request.new_context(
        base_url=API_BASE_URL,
        extra_http_headers=headers,
    )
    yield context
    context.dispose()


# =============================================================================
# Playwright設定
# =============================================================================

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """ブラウザコンテキスト設定"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
    }


@pytest.fixture
def api_page(page: Page, api_url: str, api_available: bool) -> Page:
    """API用のページ（OpenAPIドキュメント）"""
    if not api_available:
        pytest.skip("API server is not running")
    page.goto(f"{api_url}/docs")
    return page


@pytest.fixture
def streamlit_page(page: Page, streamlit_url: str, streamlit_available: bool) -> Page:
    """Streamlit用のページ"""
    if not streamlit_available:
        pytest.skip("Streamlit server is not running")
    page.goto(streamlit_url)
    # Streamlitの読み込みを待機
    page.wait_for_load_state("networkidle")
    return page


# =============================================================================
# テストデータ
# =============================================================================

@pytest.fixture
def test_recipient_data() -> dict:
    """テスト用受給者データ"""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    return {
        "name": f"テスト太郎_{unique_id}",
        "case_number": f"TEST-{unique_id}",
        "birth_date": "1970-01-01",
        "gender": "男性",
        "address": "東京都テスト区テスト町1-1-1",
    }


@pytest.fixture
def test_record_data(test_recipient_data: dict) -> dict:
    """テスト用ケース記録データ"""
    return {
        "recipient_name": test_recipient_data["name"],
        "date": "2024-12-29",
        "category": "訪問",
        "content": "E2Eテスト用のケース記録です。",
        "worker_name": "テスト担当者",
    }


# =============================================================================
# クリーンアップ
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_data(request, neo4j_available: bool):
    """テスト後のデータクリーンアップ"""
    yield
    # テスト後にテストデータをクリーンアップ（必要に応じて）
    # Note: 本番環境では実行しないこと
    if neo4j_available and os.getenv("E2E_CLEANUP", "false").lower() == "true":
        pass  # クリーンアップロジックをここに追加


# =============================================================================
# スキップ条件
# =============================================================================

def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "requires_api: marks tests as requiring API server"
    )
    config.addinivalue_line(
        "markers", "requires_streamlit: marks tests as requiring Streamlit server"
    )
    config.addinivalue_line(
        "markers", "requires_keycloak: marks tests as requiring Keycloak server"
    )
    config.addinivalue_line(
        "markers", "requires_neo4j: marks tests as requiring Neo4j server"
    )


def pytest_collection_modifyitems(config, items):
    """テスト収集時のフィルタリング"""
    skip_api = pytest.mark.skip(reason="API server is not running")
    skip_streamlit = pytest.mark.skip(reason="Streamlit server is not running")
    skip_keycloak = pytest.mark.skip(reason="Keycloak server is not running")
    skip_neo4j = pytest.mark.skip(reason="Neo4j server is not running")

    api_running = is_port_open("localhost", 8000)
    streamlit_running = is_port_open("localhost", 8501)
    keycloak_running = is_port_open("localhost", 8080)
    neo4j_running = is_port_open("localhost", 7688)

    for item in items:
        if "requires_api" in item.keywords and not api_running:
            item.add_marker(skip_api)
        if "requires_streamlit" in item.keywords and not streamlit_running:
            item.add_marker(skip_streamlit)
        if "requires_keycloak" in item.keywords and not keycloak_running:
            item.add_marker(skip_keycloak)
        if "requires_neo4j" in item.keywords and not neo4j_running:
            item.add_marker(skip_neo4j)
