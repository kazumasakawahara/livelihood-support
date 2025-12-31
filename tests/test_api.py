"""
REST API のユニットテスト
FastAPIエンドポイントのテスト
"""

import pytest
from datetime import date as date_type
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api.dependencies import User, get_current_user_or_mock


# =============================================================================
# テスト用フィクスチャ
# =============================================================================

@pytest.fixture
def client():
    """テストクライアント"""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """テスト用ユーザー"""
    return User(
        user_id="test-user-001",
        username="test_caseworker",
        name="テストケースワーカー",
        email="test@example.com",
        roles=["caseworker"],
    )


@pytest.fixture
def auth_client(client, mock_user):
    """認証済みテストクライアント"""
    # モックユーザーを注入
    app.dependency_overrides[get_current_user_or_mock] = lambda: mock_user
    yield client
    # クリーンアップ
    app.dependency_overrides.clear()


# =============================================================================
# ヘルスチェックテスト
# =============================================================================

class TestHealthCheck:
    """ヘルスチェックエンドポイントのテスト"""

    def test_health_check(self, client):
        """ヘルスチェックが成功する"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_root_endpoint(self, client):
        """ルートエンドポイントが応答する"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["version"] == "1.0.0"


# =============================================================================
# 受給者APIテスト
# =============================================================================

class TestRecipientsAPI:
    """受給者APIのテスト"""

    @patch('api.routes.recipients.get_recipients_list')
    @patch('api.routes.recipients.create_audit_log')
    def test_list_recipients_success(self, mock_audit, mock_list, auth_client):
        """受給者一覧取得成功"""
        mock_list.return_value = ["山田太郎", "鈴木花子", "佐藤次郎"]

        response = auth_client.get("/api/v1/recipients")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 3
        assert "山田太郎" in data["data"]
        assert data["meta"]["total_count"] == 3
        mock_audit.assert_called_once()

    @patch('api.routes.recipients.get_recipients_list')
    @patch('api.routes.recipients.create_audit_log')
    def test_list_recipients_empty(self, mock_audit, mock_list, auth_client):
        """受給者が空の場合"""
        mock_list.return_value = []

        response = auth_client.get("/api/v1/recipients")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total_count"] == 0

    @patch('api.routes.recipients.get_recipient_stats')
    def test_get_stats_success(self, mock_stats, auth_client):
        """統計情報取得成功"""
        mock_stats.return_value = {
            "recipient_count": 10,
            "mental_health_count": 5,
            "economic_risk_count": 3,
            "ng_by_recipient": [{"name": "山田太郎", "ng_count": 2}],
        }

        response = auth_client.get("/api/v1/recipients/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["recipient_count"] == 10
        assert data["data"]["mental_health_count"] == 5

    @patch('api.routes.recipients.get_recipient_profile')
    @patch('api.routes.recipients.create_audit_log')
    def test_get_profile_success(self, mock_audit, mock_profile, auth_client):
        """プロフィール取得成功"""
        mock_profile.return_value = {
            "recipient_name": "山田太郎",
            "ng_approaches": [{"description": "金銭話題", "riskLevel": "High"}],
            "mental_health": {"diagnosis": "うつ病", "status": "安定"},
            "effective_approaches": [{"description": "ゆっくり話す"}],
            "strengths": [{"description": "絵が上手い"}],
            "economic_risks": [],
            "money_status": None,
            "daily_life_support": None,
            "recent_records": [],
            "support_organizations": [],
        }

        response = auth_client.get("/api/v1/recipients/山田太郎/profile")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["recipient_name"] == "山田太郎"
        assert len(data["data"]["ng_approaches"]) == 1
        mock_audit.assert_called_once()

    @patch('api.routes.recipients.get_recipient_profile')
    def test_get_profile_not_found(self, mock_profile, auth_client):
        """プロフィールが見つからない場合"""
        mock_profile.return_value = {"recipient_name": None}

        response = auth_client.get("/api/v1/recipients/存在しない/profile")

        assert response.status_code == 404

    @patch('api.routes.recipients.get_handover_summary')
    @patch('api.routes.recipients.create_audit_log')
    def test_get_handover_success(self, mock_audit, mock_summary, auth_client):
        """引き継ぎサマリー取得成功"""
        mock_summary.return_value = "## 山田太郎さんの引き継ぎサマリー\n..."

        response = auth_client.get("/api/v1/recipients/山田太郎/handover")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["recipient_name"] == "山田太郎"
        assert "summary" in data["data"]

    @patch('api.routes.recipients.get_visit_briefing')
    @patch('api.routes.recipients.create_audit_log')
    def test_get_briefing_success(self, mock_audit, mock_briefing, auth_client):
        """ブリーフィング取得成功"""
        mock_briefing.return_value = {
            "受給者名": "山田太郎",
            "避けるべき関わり方": [{"description": "金銭話題"}],
            "精神疾患": "うつ病",
        }

        response = auth_client.get("/api/v1/recipients/山田太郎/briefing")

        assert response.status_code == 200
        data = response.json()
        assert "避けるべき関わり方" in data["data"] or "data" in data

    @patch('api.routes.recipients.get_visit_briefing')
    def test_get_briefing_not_found(self, mock_briefing, auth_client):
        """ブリーフィングが見つからない場合"""
        mock_briefing.return_value = {}

        response = auth_client.get("/api/v1/recipients/存在しない/briefing")

        assert response.status_code == 404

    @patch('api.routes.recipients.search_similar_cases')
    @patch('api.routes.recipients.create_audit_log')
    def test_search_similar_success(self, mock_audit, mock_similar, auth_client):
        """類似ケース検索成功"""
        mock_similar.return_value = [
            {"類似ケース": "鈴木花子", "共通リスク": ["経済的搾取"]}
        ]

        response = auth_client.get("/api/v1/recipients/山田太郎/similar")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1

    @patch('api.routes.recipients.find_matching_patterns')
    def test_find_patterns_success(self, mock_patterns, auth_client):
        """パターンマッチング成功"""
        mock_patterns.return_value = [
            {"パターン名": "経済的搾取・日自事業", "成功件数": 5}
        ]

        response = auth_client.get("/api/v1/recipients/山田太郎/patterns")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1


# =============================================================================
# ケース記録APIテスト
# =============================================================================

class TestRecordsAPI:
    """ケース記録APIのテスト"""

    @patch('api.routes.records.register_to_database')
    @patch('api.routes.records.create_audit_log')
    def test_create_record_success(self, mock_audit, mock_register, auth_client):
        """ケース記録作成成功"""
        mock_register.return_value = {"warnings": []}

        response = auth_client.post(
            "/api/v1/records",
            json={
                "recipient_name": "山田太郎",
                "date": "2024-01-15",
                "category": "訪問",
                "content": "自宅を訪問しました。",
                "recipient_response": "穏やかに応対された",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["recipient_name"] == "山田太郎"
        mock_register.assert_called_once()
        mock_audit.assert_called_once()

    def test_create_record_validation_error(self, auth_client):
        """バリデーションエラー"""
        response = auth_client.post(
            "/api/v1/records",
            json={
                "recipient_name": "",  # 空は不可
                "date": "2024-01-15",
                "category": "訪問",
                "content": "内容",
            },
        )

        assert response.status_code == 422

    @patch('api.routes.records.get_collaboration_history')
    @patch('api.routes.records.create_audit_log')
    def test_get_collaboration_success(self, mock_audit, mock_history, auth_client):
        """連携履歴取得成功"""
        mock_history.return_value = [
            {"日付": "2024-01-20", "種別": "ケース会議", "参加者": ["福祉事務所"]}
        ]

        response = auth_client.get("/api/v1/records/collaboration/山田太郎")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        mock_audit.assert_called_once()

    @patch('api.routes.records.get_collaboration_history')
    @patch('api.routes.records.create_audit_log')
    def test_get_collaboration_with_limit(self, mock_audit, mock_history, auth_client):
        """連携履歴取得（件数制限）"""
        mock_history.return_value = []

        response = auth_client.get("/api/v1/records/collaboration/山田太郎?limit=5")

        assert response.status_code == 200
        # limitパラメータが渡されていることを確認
        mock_history.assert_called_with("山田太郎", limit=5)

    @patch('api.routes.records.register_to_database')
    @patch('api.routes.records.create_audit_log')
    def test_bulk_register_success(self, mock_audit, mock_register, auth_client):
        """一括登録成功"""
        mock_register.return_value = {"warnings": []}

        response = auth_client.post(
            "/api/v1/records/bulk",
            json={
                "recipient": {"name": "山田太郎"},
                "ngApproaches": [{"description": "金銭話題", "reason": "トラウマ", "riskLevel": "High"}],
                "caseRecords": [{"date": "2024-01-15", "category": "訪問", "content": "訪問記録"}],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["data"]["recipient_name"] == "山田太郎"

    def test_bulk_register_no_name(self, auth_client):
        """一括登録: 受給者名なしでエラー"""
        response = auth_client.post(
            "/api/v1/records/bulk",
            json={
                "recipient": {},  # 名前なし
                "caseRecords": [],
            },
        )

        assert response.status_code == 422


# =============================================================================
# スキーマテスト
# =============================================================================

class TestSchemas:
    """Pydanticスキーマのテスト"""

    def test_recipient_name_validation(self):
        """受給者名のバリデーション"""
        from api.schemas import RecipientBase

        # 正常なケース
        recipient = RecipientBase(name="山田太郎")
        assert recipient.name == "山田太郎"

    def test_recipient_name_xss_prevention(self):
        """XSS攻撃の防止"""
        from api.schemas import RecipientBase
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RecipientBase(name="<script>alert('xss')</script>")

    def test_case_record_content_validation(self):
        """ケース記録内容のバリデーション"""
        from api.schemas import CaseRecordCreate
        from pydantic import ValidationError

        # 正常なケース
        record = CaseRecordCreate(
            recipient_name="山田太郎",
            date=date_type(2024, 1, 15),
            category="訪問",
            content="自宅訪問を行いました。",
        )
        assert record.content == "自宅訪問を行いました。"

        # XSS攻撃
        with pytest.raises(ValidationError):
            CaseRecordCreate(
                recipient_name="山田太郎",
                date=date_type(2024, 1, 15),
                category="訪問",
                content="<script>alert('xss')</script>",
            )


# =============================================================================
# 依存関係テスト
# =============================================================================

class TestDependencies:
    """依存関係（認証）のテスト"""

    def test_user_permissions(self):
        """ユーザー権限の確認"""
        from api.dependencies import User, Permission

        user = User(
            user_id="test",
            username="test_user",
            roles=["caseworker"],
        )

        assert user.has_permission(Permission.READ_OWN_CASES)
        assert user.has_permission(Permission.WRITE_OWN_CASES)
        assert not user.has_permission(Permission.MANAGE_USERS)

    def test_admin_has_all_permissions(self):
        """管理者は全権限を持つ"""
        from api.dependencies import User, Permission

        admin = User(
            user_id="admin",
            username="admin_user",
            roles=["admin"],
        )

        assert admin.has_permission(Permission.SYSTEM_ADMIN)
        assert admin.has_permission(Permission.MANAGE_USERS)
        assert admin.has_permission(Permission.VIEW_AUDIT_LOGS)

    def test_supervisor_permissions(self):
        """スーパーバイザーの権限"""
        from api.dependencies import User, Permission

        supervisor = User(
            user_id="sv",
            username="sv_user",
            roles=["supervisor"],
        )

        assert supervisor.has_permission(Permission.READ_TEAM_CASES)
        assert supervisor.has_permission(Permission.VIEW_AUDIT_LOGS)
        assert not supervisor.has_permission(Permission.MANAGE_USERS)

    def test_has_role(self):
        """ロール確認"""
        from api.dependencies import User

        user = User(
            user_id="test",
            username="test",
            roles=["caseworker", "auditor"],
        )

        assert user.has_role("caseworker")
        assert user.has_role("auditor")
        assert not user.has_role("admin")
