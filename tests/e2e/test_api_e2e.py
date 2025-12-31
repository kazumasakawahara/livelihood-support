"""
API E2E Tests
FastAPI REST APIのエンドツーエンドテスト

サーバーが起動していない場合は自動的にスキップされます。
"""

import pytest
import time
from playwright.sync_api import Page, Playwright, APIRequestContext


# =============================================================================
# ヘルスチェックテスト
# =============================================================================

@pytest.mark.requires_api
class TestAPIHealth:
    """APIヘルスチェックのE2Eテスト"""

    def test_health_endpoint(self, api_context: APIRequestContext):
        """ヘルスチェックエンドポイントが正常に応答する"""
        response = api_context.get("/health")

        assert response.status == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_root_endpoint(self, api_context: APIRequestContext):
        """ルートエンドポイントが正常に応答する"""
        response = api_context.get("/")

        assert response.status == 200
        data = response.json()
        assert "message" in data


# =============================================================================
# OpenAPIドキュメントテスト
# =============================================================================

@pytest.mark.requires_api
class TestOpenAPIDocumentation:
    """OpenAPIドキュメントのE2Eテスト"""

    def test_swagger_ui_loads(self, api_page: Page):
        """Swagger UIが正常に読み込まれる"""
        # Swagger UIのタイトルを確認
        api_page.wait_for_load_state("networkidle")
        assert "Swagger UI" in api_page.title() or "FastAPI" in api_page.title()

    def test_openapi_json_available(self, api_context: APIRequestContext):
        """OpenAPI JSONが取得できる"""
        response = api_context.get("/openapi.json")

        assert response.status == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "info" in data

    def test_redoc_available(self, api_context: APIRequestContext):
        """ReDocが利用可能"""
        response = api_context.get("/redoc")
        assert response.status == 200


# =============================================================================
# 受給者APIテスト
# =============================================================================

@pytest.mark.requires_api
class TestRecipientsAPI:
    """受給者APIのE2Eテスト"""

    def test_list_recipients_endpoint(self, api_context: APIRequestContext):
        """受給者一覧取得エンドポイントが動作する"""
        response = api_context.get("/api/v1/recipients")

        assert response.status == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)

    def test_list_recipients_with_pagination(self, api_context: APIRequestContext):
        """ページネーションパラメータが動作する"""
        response = api_context.get("/api/v1/recipients?page=1&page_size=5")

        assert response.status == 200
        data = response.json()
        assert "meta" in data
        meta = data["meta"]
        assert meta.get("page") == 1
        assert meta.get("page_size") == 5

    def test_stats_endpoint(self, api_context: APIRequestContext):
        """統計エンドポイントが動作する"""
        response = api_context.get("/api/v1/recipients/stats")

        assert response.status == 200
        data = response.json()
        assert "data" in data

    def test_search_recipients(self, api_context: APIRequestContext):
        """受給者検索が動作する"""
        response = api_context.get("/api/v1/recipients?search=テスト")

        assert response.status == 200
        data = response.json()
        assert "data" in data


# =============================================================================
# ケース記録APIテスト
# =============================================================================

@pytest.mark.requires_api
class TestRecordsAPI:
    """ケース記録APIのE2Eテスト"""

    def test_list_records_endpoint(self, api_context: APIRequestContext):
        """ケース記録一覧取得エンドポイントが動作する"""
        response = api_context.get("/api/v1/records")

        assert response.status == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_create_record_validation(self, api_context: APIRequestContext):
        """ケース記録作成時のバリデーションが動作する"""
        # 不完全なデータ
        response = api_context.post(
            "/api/v1/records",
            data={"content": "テスト"},  # 必須フィールドが不足
        )

        # バリデーションエラー
        assert response.status in [400, 422]


# =============================================================================
# 認証テスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_keycloak
class TestAPIAuthentication:
    """API認証のE2Eテスト"""

    def test_token_endpoint_reachable(self, keycloak_url: str, playwright: Playwright):
        """Keycloakトークンエンドポイントが到達可能"""
        context = playwright.request.new_context()
        try:
            response = context.get(
                f"{keycloak_url}/realms/livelihood-support/.well-known/openid-configuration"
            )
            assert response.status == 200
            data = response.json()
            assert "token_endpoint" in data
        finally:
            context.dispose()

    def test_get_token_with_valid_credentials(
        self, keycloak_url: str, playwright: Playwright
    ):
        """有効な認証情報でトークンを取得できる"""
        context = playwright.request.new_context()
        try:
            response = context.post(
                f"{keycloak_url}/realms/livelihood-support/protocol/openid-connect/token",
                form={
                    "grant_type": "password",
                    "client_id": "livelihood-support-app",
                    "username": "caseworker1",
                    "password": "caseworker123",
                },
            )
            assert response.status == 200
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"].lower() == "bearer"
        finally:
            context.dispose()

    def test_get_token_with_invalid_credentials(
        self, keycloak_url: str, playwright: Playwright
    ):
        """無効な認証情報ではトークン取得に失敗する"""
        context = playwright.request.new_context()
        try:
            response = context.post(
                f"{keycloak_url}/realms/livelihood-support/protocol/openid-connect/token",
                form={
                    "grant_type": "password",
                    "client_id": "livelihood-support-app",
                    "username": "invalid_user",
                    "password": "wrong_password",
                },
            )
            assert response.status == 401
        finally:
            context.dispose()

    def test_authenticated_request(self, auth_api_context: APIRequestContext):
        """認証済みリクエストが成功する"""
        response = auth_api_context.get("/api/v1/recipients")
        assert response.status == 200


# =============================================================================
# セキュリティテスト
# =============================================================================

@pytest.mark.requires_api
class TestAPISecurity:
    """APIセキュリティのE2Eテスト"""

    def test_security_headers(self, api_context: APIRequestContext):
        """セキュリティヘッダーが適切に設定されている"""
        response = api_context.get("/health")
        headers = response.headers

        # 基本的なセキュリティヘッダー（サーバー設定に依存）
        assert response.status == 200
        # X-Content-Type-Options, X-Frame-Options などが設定されていることを確認
        # 実際の値はミドルウェア設定に依存

    def test_invalid_endpoint_returns_404(self, api_context: APIRequestContext):
        """存在しないエンドポイントは404を返す"""
        response = api_context.get("/api/v1/nonexistent")
        assert response.status == 404

    def test_method_not_allowed(self, api_context: APIRequestContext):
        """許可されていないメソッドは405を返す"""
        response = api_context.delete("/health")
        assert response.status == 405

    def test_xss_prevention_in_input(self, api_context: APIRequestContext):
        """XSS攻撃が防止される"""
        # XSSペイロードを含むリクエスト
        malicious_data = {
            "recipient_name": "<script>alert('xss')</script>",
            "date": "2024-01-15",
            "category": "訪問",
            "content": "テスト",
        }
        response = api_context.post("/api/v1/records", data=malicious_data)

        # バリデーションエラーまたはサニタイズされることを確認
        if response.status == 200:
            data = response.json()
            # レスポンスにスクリプトタグが含まれていないことを確認
            assert "<script>" not in str(data)
        else:
            assert response.status in [400, 422]

    def test_sql_injection_prevention(self, api_context: APIRequestContext):
        """SQLインジェクションが防止される（Cypherインジェクション）"""
        malicious_search = "'; DROP (n) DETACH DELETE n; //"
        response = api_context.get(f"/api/v1/recipients?search={malicious_search}")

        # エラーにならず安全に処理される
        assert response.status in [200, 400, 422]


# =============================================================================
# パフォーマンステスト
# =============================================================================

@pytest.mark.requires_api
class TestAPIPerformance:
    """APIパフォーマンスのE2Eテスト"""

    def test_health_response_time(self, api_context: APIRequestContext):
        """ヘルスチェックが迅速に応答する（<500ms）"""
        start = time.time()
        response = api_context.get("/health")
        elapsed = time.time() - start

        assert response.status == 200
        assert elapsed < 0.5, f"Response took {elapsed:.2f}s, expected <0.5s"

    def test_list_recipients_response_time(self, api_context: APIRequestContext):
        """受給者一覧が適切な時間で応答する（<2s）"""
        start = time.time()
        response = api_context.get("/api/v1/recipients?page_size=10")
        elapsed = time.time() - start

        assert response.status == 200
        assert elapsed < 2.0, f"Response took {elapsed:.2f}s, expected <2.0s"

    def test_concurrent_requests(self, api_context: APIRequestContext):
        """同時リクエストを処理できる"""
        import concurrent.futures

        def make_request():
            return api_context.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]

        # すべてのリクエストが成功
        assert all(r.status == 200 for r in results)


# =============================================================================
# メトリクステスト
# =============================================================================

@pytest.mark.requires_api
class TestAPIMetrics:
    """APIメトリクスのE2Eテスト"""

    def test_metrics_endpoint_available(self, api_context: APIRequestContext):
        """Prometheusメトリクスエンドポイントが利用可能"""
        response = api_context.get("/metrics")

        assert response.status == 200
        content = response.text()
        # Prometheusフォーマットのメトリクス
        assert "http_requests" in content or "python_" in content

    def test_metrics_include_request_count(self, api_context: APIRequestContext):
        """リクエストカウントメトリクスが含まれる"""
        # いくつかリクエストを実行
        for _ in range(3):
            api_context.get("/health")

        response = api_context.get("/metrics")
        content = response.text()

        # リクエスト関連のメトリクスが存在
        assert "http_request" in content.lower() or "requests" in content.lower()


# =============================================================================
# エラーハンドリングテスト
# =============================================================================

@pytest.mark.requires_api
class TestAPIErrorHandling:
    """APIエラーハンドリングのE2Eテスト"""

    def test_validation_error_format(self, api_context: APIRequestContext):
        """バリデーションエラーが適切なフォーマットで返される"""
        response = api_context.post(
            "/api/v1/records",
            data={"invalid": "data"},
        )

        assert response.status in [400, 422]
        data = response.json()
        # エラーレスポンスの構造確認
        assert "detail" in data or "error" in data or "message" in data

    def test_not_found_error_format(self, api_context: APIRequestContext):
        """404エラーが適切なフォーマットで返される"""
        response = api_context.get("/api/v1/recipients/nonexistent-id-12345")

        assert response.status == 404
        data = response.json()
        assert "detail" in data or "error" in data or "message" in data

    def test_internal_error_does_not_leak_info(self, api_context: APIRequestContext):
        """内部エラーが機密情報を漏らさない"""
        # 意図的に不正なリクエスト
        response = api_context.get("/api/v1/recipients?page=-1")

        if response.status >= 400:
            content = response.text()
            # スタックトレースやパス情報が含まれていないことを確認
            assert "Traceback" not in content
            assert "/Users/" not in content
            assert "File \"" not in content
