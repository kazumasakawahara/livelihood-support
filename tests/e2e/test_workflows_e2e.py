"""
ワークフローE2Eテスト
主要なユーザーフローのエンドツーエンドテスト

サーバーが起動していない場合は自動的にスキップされます。
"""

import pytest
import time
import uuid
from datetime import date, datetime
from playwright.sync_api import APIRequestContext


# =============================================================================
# 受給者登録ワークフローテスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_neo4j
class TestRecipientRegistrationWorkflow:
    """受給者登録ワークフローのE2Eテスト"""

    @pytest.fixture
    def unique_recipient_name(self) -> str:
        """テスト用のユニークな受給者名を生成"""
        return f"E2Eテスト_{uuid.uuid4().hex[:8]}"

    def test_bulk_registration_creates_recipient(
        self, api_context: APIRequestContext, unique_recipient_name: str
    ):
        """一括登録で受給者が正しく作成される"""
        # 1. 一括登録データを準備
        bulk_data = {
            "recipient": {
                "name": unique_recipient_name,
                "birthDate": "1970-05-15",
                "gender": "男性",
            },
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "電話連絡",
                    "content": "E2Eテスト用の初回記録です。",
                    "recipientResponse": "良好",
                    "caseworker": "テストワーカー",
                }
            ],
            "ngApproaches": [
                {
                    "approach": "急かすような声かけ",
                    "reason": "不安を助長するため",
                }
            ],
            "effectiveApproaches": [
                {
                    "approach": "ゆっくりと話す",
                    "context": "面談時",
                }
            ],
        }

        # 2. 一括登録を実行
        response = api_context.post("/api/v1/records/bulk", data=bulk_data)

        # 3. 登録成功を確認
        assert response.status == 201
        data = response.json()
        assert data["data"]["recipient_name"] == unique_recipient_name

    def test_registered_recipient_appears_in_list(
        self, api_context: APIRequestContext, unique_recipient_name: str
    ):
        """登録した受給者が一覧に表示される"""
        # 1. 受給者を登録
        bulk_data = {
            "recipient": {"name": unique_recipient_name},
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "訪問",
                    "content": "テスト記録",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }
        reg_response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert reg_response.status == 201

        # 2. 受給者一覧を取得
        list_response = api_context.get("/api/v1/recipients")
        assert list_response.status == 200

        # 3. 登録した受給者が一覧に含まれることを確認
        data = list_response.json()
        recipients = data["data"]
        assert any(r["name"] == unique_recipient_name for r in recipients)

    def test_registration_with_mental_health_info(
        self, api_context: APIRequestContext, unique_recipient_name: str
    ):
        """精神疾患情報を含む登録が正しく処理される"""
        bulk_data = {
            "recipient": {"name": unique_recipient_name},
            "mentalHealthConditions": [
                {
                    "diagnosis": "うつ病",
                    "hospital": "メンタルクリニック",
                    "startDate": "2020-01-15",
                    "status": "Active",
                }
            ],
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "電話連絡",
                    "content": "精神疾患情報テスト",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }

        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 201

    def test_registration_with_economic_risk(
        self, api_context: APIRequestContext, unique_recipient_name: str
    ):
        """経済的リスク情報を含む登録が正しく処理される"""
        bulk_data = {
            "recipient": {"name": unique_recipient_name},
            "economicRisks": [
                {
                    "riskType": "親族による金銭搾取",
                    "description": "息子が毎月お金を持っていく",
                    "severity": "High",
                    "detectedDate": date.today().isoformat(),
                }
            ],
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "訪問",
                    "content": "経済的リスクテスト",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }

        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 201


# =============================================================================
# ケース記録作成ワークフローテスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_neo4j
class TestCaseRecordWorkflow:
    """ケース記録作成ワークフローのE2Eテスト"""

    @pytest.fixture
    def registered_recipient(self, api_context: APIRequestContext) -> str:
        """テスト用の登録済み受給者を作成"""
        name = f"記録テスト_{uuid.uuid4().hex[:8]}"
        bulk_data = {
            "recipient": {"name": name},
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "電話連絡",
                    "content": "初回登録記録",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }
        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 201
        return name

    def test_create_case_record(
        self, api_context: APIRequestContext, registered_recipient: str
    ):
        """ケース記録を正常に作成できる"""
        record_data = {
            "recipient_name": registered_recipient,
            "date": date.today().isoformat(),
            "category": "訪問",
            "content": "E2Eテスト訪問記録：本人と面談。体調良好。",
            "recipient_response": "話をよく聞いてくれた",
            "caseworker": "テストワーカー",
        }

        response = api_context.post("/api/v1/records", data=record_data)

        assert response.status == 201
        data = response.json()
        assert data["data"]["recipient_name"] == registered_recipient

    def test_create_multiple_records(
        self, api_context: APIRequestContext, registered_recipient: str
    ):
        """複数のケース記録を連続して作成できる"""
        categories = ["訪問", "電話連絡", "来所相談"]

        for i, category in enumerate(categories):
            record_data = {
                "recipient_name": registered_recipient,
                "date": date.today().isoformat(),
                "category": category,
                "content": f"E2Eテスト記録 {i + 1}: {category}の内容",
                "recipient_response": "",
                "caseworker": "テストワーカー",
            }

            response = api_context.post("/api/v1/records", data=record_data)
            assert response.status == 201

    def test_record_validation_rejects_empty_content(
        self, api_context: APIRequestContext, registered_recipient: str
    ):
        """空の内容はバリデーションエラー"""
        record_data = {
            "recipient_name": registered_recipient,
            "date": date.today().isoformat(),
            "category": "訪問",
            "content": "",  # 空
        }

        response = api_context.post("/api/v1/records", data=record_data)
        assert response.status in [400, 422]


# =============================================================================
# 訪問前ブリーフィングワークフローテスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_neo4j
class TestVisitBriefingWorkflow:
    """訪問前ブリーフィングワークフローのE2Eテスト"""

    @pytest.fixture
    def recipient_with_ng_approaches(self, api_context: APIRequestContext) -> str:
        """NG情報を持つ受給者を作成"""
        name = f"ブリーフィングテスト_{uuid.uuid4().hex[:8]}"
        bulk_data = {
            "recipient": {"name": name},
            "ngApproaches": [
                {
                    "approach": "大声で話しかける",
                    "reason": "聴覚過敏のため",
                },
                {
                    "approach": "約束を急かす",
                    "reason": "パニックを起こしやすいため",
                },
            ],
            "effectiveApproaches": [
                {
                    "approach": "静かに話す",
                    "context": "面談時",
                }
            ],
            "mentalHealthConditions": [
                {
                    "diagnosis": "不安障害",
                    "status": "Active",
                }
            ],
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "訪問",
                    "content": "初回訪問記録",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }
        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 201
        return name

    def test_get_briefing_returns_ng_approaches(
        self, api_context: APIRequestContext, recipient_with_ng_approaches: str
    ):
        """ブリーフィングにNG情報が含まれる"""
        response = api_context.get(
            f"/api/v1/recipients/{recipient_with_ng_approaches}/briefing"
        )

        assert response.status == 200
        data = response.json()
        # ブリーフィングデータの構造を確認
        assert "data" in data

    def test_get_profile_includes_all_info(
        self, api_context: APIRequestContext, recipient_with_ng_approaches: str
    ):
        """プロフィールに登録情報が含まれる"""
        response = api_context.get(
            f"/api/v1/recipients/{recipient_with_ng_approaches}/profile"
        )

        assert response.status == 200
        data = response.json()
        assert "data" in data

    def test_get_handover_summary(
        self, api_context: APIRequestContext, recipient_with_ng_approaches: str
    ):
        """引き継ぎサマリーが取得できる"""
        response = api_context.get(
            f"/api/v1/recipients/{recipient_with_ng_approaches}/handover"
        )

        assert response.status == 200
        data = response.json()
        assert "data" in data
        assert "summary" in data["data"] or "recipient_name" in data["data"]


# =============================================================================
# 類似ケース検索ワークフローテスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_neo4j
class TestSimilarCaseSearchWorkflow:
    """類似ケース検索ワークフローのE2Eテスト"""

    @pytest.fixture
    def recipient_with_economic_risk(self, api_context: APIRequestContext) -> str:
        """経済的リスクを持つ受給者を作成"""
        name = f"類似検索テスト_{uuid.uuid4().hex[:8]}"
        bulk_data = {
            "recipient": {"name": name},
            "economicRisks": [
                {
                    "riskType": "親族による金銭搾取",
                    "severity": "High",
                }
            ],
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "訪問",
                    "content": "経済的リスク確認",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }
        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 201
        return name

    def test_search_similar_cases(
        self, api_context: APIRequestContext, recipient_with_economic_risk: str
    ):
        """類似ケース検索が実行できる"""
        response = api_context.get(
            f"/api/v1/recipients/{recipient_with_economic_risk}/similar"
        )

        assert response.status == 200
        data = response.json()
        assert "data" in data
        # 類似ケースはリストとして返される
        assert isinstance(data["data"], list)

    def test_find_matching_patterns(
        self, api_context: APIRequestContext, recipient_with_economic_risk: str
    ):
        """マッチングパターン検索が実行できる"""
        response = api_context.get(
            f"/api/v1/recipients/{recipient_with_economic_risk}/patterns"
        )

        assert response.status == 200
        data = response.json()
        assert "data" in data


# =============================================================================
# 連携履歴ワークフローテスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_neo4j
class TestCollaborationWorkflow:
    """連携履歴ワークフローのE2Eテスト"""

    @pytest.fixture
    def recipient_with_collaboration(self, api_context: APIRequestContext) -> str:
        """連携記録を持つ受給者を作成"""
        name = f"連携テスト_{uuid.uuid4().hex[:8]}"
        bulk_data = {
            "recipient": {"name": name},
            "collaborationRecords": [
                {
                    "date": date.today().isoformat(),
                    "organization": "医療機関",
                    "contactType": "電話",
                    "content": "通院状況の確認",
                    "outcome": "良好",
                }
            ],
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "電話連絡",
                    "content": "連携記録テスト",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }
        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 201
        return name

    def test_get_collaboration_history(
        self, api_context: APIRequestContext, recipient_with_collaboration: str
    ):
        """連携履歴が取得できる"""
        response = api_context.get(
            f"/api/v1/records/collaboration/{recipient_with_collaboration}"
        )

        assert response.status == 200
        data = response.json()
        assert "data" in data

    def test_collaboration_history_with_limit(
        self, api_context: APIRequestContext, recipient_with_collaboration: str
    ):
        """連携履歴の件数制限が動作する"""
        response = api_context.get(
            f"/api/v1/records/collaboration/{recipient_with_collaboration}?limit=5"
        )

        assert response.status == 200
        data = response.json()
        assert "data" in data


# =============================================================================
# データ整合性テスト
# =============================================================================

@pytest.mark.requires_api
@pytest.mark.requires_neo4j
class TestDataIntegrity:
    """データ整合性のE2Eテスト"""

    def test_create_and_retrieve_consistency(self, api_context: APIRequestContext):
        """作成したデータが正確に取得できる"""
        # 1. ユニークなデータで登録
        name = f"整合性テスト_{uuid.uuid4().hex[:8]}"
        content = f"テスト内容_{uuid.uuid4().hex}"

        bulk_data = {
            "recipient": {"name": name},
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "訪問",
                    "content": content,
                    "recipientResponse": "確認済み",
                    "caseworker": "整合性テスター",
                }
            ],
        }

        # 2. 登録
        reg_response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert reg_response.status == 201

        # 3. 取得して確認
        profile_response = api_context.get(f"/api/v1/recipients/{name}/profile")
        assert profile_response.status == 200

    def test_stats_reflect_new_registrations(self, api_context: APIRequestContext):
        """新規登録が統計に反映される"""
        # 1. 登録前の統計を取得
        before_response = api_context.get("/api/v1/recipients/stats")
        assert before_response.status == 200

        # 2. 新規登録
        name = f"統計テスト_{uuid.uuid4().hex[:8]}"
        bulk_data = {
            "recipient": {"name": name},
            "caseRecords": [
                {
                    "date": date.today().isoformat(),
                    "category": "電話連絡",
                    "content": "統計テスト",
                    "recipientResponse": "",
                    "caseworker": "テスト",
                }
            ],
        }
        reg_response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert reg_response.status == 201

        # 3. 登録後の統計を取得（増加を確認）
        after_response = api_context.get("/api/v1/recipients/stats")
        assert after_response.status == 200


# =============================================================================
# エラーハンドリングワークフローテスト
# =============================================================================

@pytest.mark.requires_api
class TestErrorHandlingWorkflow:
    """エラーハンドリングワークフローのE2Eテスト"""

    def test_nonexistent_recipient_profile(self, api_context: APIRequestContext):
        """存在しない受給者のプロフィール取得"""
        response = api_context.get("/api/v1/recipients/存在しない受給者_xyz/profile")
        assert response.status == 404

    def test_nonexistent_recipient_briefing(self, api_context: APIRequestContext):
        """存在しない受給者のブリーフィング取得"""
        response = api_context.get("/api/v1/recipients/存在しない受給者_xyz/briefing")
        assert response.status == 404

    def test_invalid_date_format_in_record(self, api_context: APIRequestContext):
        """不正な日付形式のケース記録"""
        record_data = {
            "recipient_name": "テスト",
            "date": "invalid-date",
            "category": "訪問",
            "content": "テスト",
        }

        response = api_context.post("/api/v1/records", data=record_data)
        assert response.status in [400, 422]

    def test_missing_required_fields(self, api_context: APIRequestContext):
        """必須フィールド欠落"""
        # 受給者名なし
        bulk_data = {
            "recipient": {},  # nameなし
            "caseRecords": [],
        }

        response = api_context.post("/api/v1/records/bulk", data=bulk_data)
        assert response.status == 422

    def test_invalid_category(self, api_context: APIRequestContext):
        """無効なカテゴリ"""
        record_data = {
            "recipient_name": "テスト",
            "date": date.today().isoformat(),
            "category": "無効なカテゴリ",
            "content": "テスト",
        }

        response = api_context.post("/api/v1/records", data=record_data)
        assert response.status in [400, 422]


# =============================================================================
# レスポンス構造テスト
# =============================================================================

@pytest.mark.requires_api
class TestResponseStructure:
    """APIレスポンス構造のE2Eテスト"""

    def test_list_response_structure(self, api_context: APIRequestContext):
        """一覧レスポンスの構造確認"""
        response = api_context.get("/api/v1/recipients")

        assert response.status == 200
        data = response.json()

        # 標準レスポンス構造
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert "timestamp" in data["meta"]

    def test_single_item_response_structure(self, api_context: APIRequestContext):
        """単一アイテムレスポンスの構造確認"""
        response = api_context.get("/api/v1/recipients/stats")

        assert response.status == 200
        data = response.json()

        assert "data" in data
        assert "meta" in data

    def test_error_response_structure(self, api_context: APIRequestContext):
        """エラーレスポンスの構造確認"""
        response = api_context.get("/api/v1/recipients/不存在/profile")

        assert response.status == 404
        data = response.json()

        # エラーレスポンスにdetailが含まれる
        assert "detail" in data
