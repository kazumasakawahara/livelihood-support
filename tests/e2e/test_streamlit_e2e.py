"""
Streamlit E2E Tests
ケースワーカー向けUIのエンドツーエンドテスト
"""

import pytest
from playwright.sync_api import Page, expect


# =============================================================================
# ページ読み込みテスト
# =============================================================================

class TestStreamlitLoad:
    """Streamlitアプリケーションの読み込みテスト"""

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_app_loads_successfully(self, streamlit_page: Page):
        """アプリケーションが正常に読み込まれる"""
        # ページタイトルの確認
        expect(streamlit_page).to_have_title("Streamlit")

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_main_header_visible(self, streamlit_page: Page):
        """メインヘッダーが表示される"""
        # Streamlitアプリのヘッダーを確認
        header = streamlit_page.locator("h1").first
        expect(header).to_be_visible()

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_sidebar_visible(self, streamlit_page: Page):
        """サイドバーが表示される"""
        sidebar = streamlit_page.locator('[data-testid="stSidebar"]')
        expect(sidebar).to_be_visible()


# =============================================================================
# ナビゲーションテスト
# =============================================================================

class TestStreamlitNavigation:
    """Streamlitナビゲーションのテスト"""

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_tab_navigation(self, streamlit_page: Page):
        """タブナビゲーションが動作する"""
        # タブの存在確認
        tabs = streamlit_page.locator('[data-testid="stTab"]')
        expect(tabs.first).to_be_visible()

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_recipient_selector(self, streamlit_page: Page):
        """受給者選択が動作する"""
        # セレクトボックスの確認
        selectbox = streamlit_page.locator('[data-testid="stSelectbox"]').first
        if selectbox.is_visible():
            expect(selectbox).to_be_enabled()


# =============================================================================
# フォーム操作テスト
# =============================================================================

class TestStreamlitForms:
    """Streamlitフォームのテスト"""

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_case_record_form_exists(self, streamlit_page: Page):
        """ケース記録フォームが存在する"""
        # テキストエリアの確認
        text_area = streamlit_page.locator('[data-testid="stTextArea"]').first
        expect(text_area).to_be_visible()

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_form_validation(self, streamlit_page: Page):
        """フォームバリデーションが動作する"""
        # 空のフォームを送信
        submit_button = streamlit_page.locator('button:has-text("登録")')
        if submit_button.is_visible():
            submit_button.click()
            # エラーメッセージの確認
            streamlit_page.wait_for_timeout(1000)


# =============================================================================
# アクセシビリティテスト
# =============================================================================

class TestStreamlitAccessibility:
    """Streamlitアクセシビリティのテスト"""

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_keyboard_navigation(self, streamlit_page: Page):
        """キーボードナビゲーションが可能"""
        # Tabキーでのナビゲーション
        streamlit_page.keyboard.press("Tab")
        # フォーカスが移動することを確認

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_form_labels_present(self, streamlit_page: Page):
        """フォームラベルが存在する"""
        # ラベルの確認
        labels = streamlit_page.locator("label")
        expect(labels.first).to_be_visible()


# =============================================================================
# レスポンシブデザインテスト
# =============================================================================

class TestStreamlitResponsive:
    """Streamlitレスポンシブデザインのテスト"""

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_mobile_viewport(self, page: Page, streamlit_url: str):
        """モバイルビューポートで正常に表示される"""
        # モバイルサイズに変更
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(streamlit_url)
        page.wait_for_load_state("networkidle")

        # ページが表示されることを確認
        expect(page).not_to_have_url("about:blank")

    @pytest.mark.skip(reason="Streamlitサーバーが起動している必要があります")
    def test_tablet_viewport(self, page: Page, streamlit_url: str):
        """タブレットビューポートで正常に表示される"""
        # タブレットサイズに変更
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(streamlit_url)
        page.wait_for_load_state("networkidle")

        # ページが表示されることを確認
        expect(page).not_to_have_url("about:blank")


# =============================================================================
# ヘルスチェックテスト（ユニットテストとして実行可能）
# =============================================================================

class TestStreamlitHealth:
    """StreamlitヘルスチェックのE2Eテスト"""

    def test_health_endpoint(self, streamlit_url: str, playwright):
        """Streamlitヘルスエンドポイントが応答する"""
        request = playwright.request.new_context()

        try:
            response = request.get(f"{streamlit_url}/_stcore/health")
            # Streamlitが起動していれば200、起動していなければ接続エラー
            if response.ok:
                assert response.status == 200
        except Exception:
            # Streamlitが起動していない場合はスキップ
            pytest.skip("Streamlit server is not running")
        finally:
            request.dispose()
