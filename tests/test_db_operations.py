"""
lib/db_operations.py のユニットテスト
モックを使用したデータ登録機能のテスト
"""

import pytest
from datetime import date
from unittest.mock import MagicMock, patch


class TestRegisterRecipient:
    """受給者基本情報登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_recipient_success(self, mock_run_query, mock_audit):
        """受給者登録成功"""
        from lib.db_operations import register_recipient

        mock_run_query.return_value = [{"name": "山田太郎"}]

        result = register_recipient({
            "name": "山田太郎",
            "caseNumber": "2024-001",
            "dob": "1970-01-15",
            "gender": "男性",
            "address": "東京都千代田区"
        }, user_name="test_user")

        assert result["status"] == "success"
        assert result["data"]["name"] == "山田太郎"
        mock_run_query.assert_called_once()
        mock_audit.assert_called_once()

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_recipient_minimal_data(self, mock_run_query, mock_audit):
        """最小限のデータでの登録"""
        from lib.db_operations import register_recipient

        mock_run_query.return_value = [{"name": "鈴木花子"}]

        result = register_recipient({"name": "鈴木花子"}, user_name="system")

        assert result["status"] == "success"


class TestRegisterCaseRecord:
    """ケース記録登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_case_record_success(self, mock_run_query, mock_audit):
        """ケース記録登録成功"""
        from lib.db_operations import register_case_record

        mock_run_query.return_value = [{"date": "2024-01-15", "category": "訪問"}]

        result = register_case_record(
            record_data={
                "date": "2024-01-15",
                "category": "訪問",
                "content": "自宅訪問を実施",
                "caseworker": "担当者A",
                "recipientResponse": "良好",
                "observations": ["室内清潔", "表情明るい"]
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        assert result["data"]["category"] == "訪問"
        mock_audit.assert_called_once()

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_case_record_with_defaults(self, mock_run_query, mock_audit):
        """デフォルト値でのケース記録登録"""
        from lib.db_operations import register_case_record

        mock_run_query.return_value = [{"date": date.today().isoformat(), "category": "その他"}]

        result = register_case_record(
            record_data={"content": "電話対応"},
            recipient_name="山田太郎"
        )

        assert result["status"] == "success"


class TestRegisterNgApproach:
    """避けるべき関わり方登録のテスト"""

    @patch('lib.db_operations.log')
    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_ng_approach_high_risk(self, mock_run_query, mock_audit, mock_log):
        """高リスクのNG関わり方登録"""
        from lib.db_operations import register_ng_approach

        mock_run_query.return_value = [{"description": "突然の金銭話題", "risk": "High"}]

        result = register_ng_approach(
            ng_data={
                "description": "突然の金銭話題",
                "reason": "金銭トラブルの経験あり",
                "riskLevel": "High",
                "consequence": "パニック発作の可能性"
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        assert result["data"]["risk"] == "High"
        mock_audit.assert_called_once()
        mock_log.assert_called()

    @patch('lib.db_operations.log')
    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_ng_approach_medium_risk(self, mock_run_query, mock_audit, mock_log):
        """中リスクのNG関わり方登録"""
        from lib.db_operations import register_ng_approach

        mock_run_query.return_value = [{"description": "長時間の面談", "risk": "Medium"}]

        result = register_ng_approach(
            ng_data={
                "description": "長時間の面談",
                "reason": "集中力が続かない",
                "riskLevel": "Medium"
            },
            recipient_name="山田太郎"
        )

        assert result["status"] == "success"


class TestRegisterEconomicRisk:
    """経済的リスク登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.log')
    @patch('lib.db_operations.run_query')
    def test_register_economic_risk_exploitation(self, mock_run_query, mock_log, mock_audit):
        """経済的搾取リスク登録"""
        from lib.db_operations import register_economic_risk

        mock_run_query.return_value = [{"type": "経済的搾取", "severity": "High"}]

        result = register_economic_risk(
            risk_data={
                "type": "経済的搾取",
                "perpetrator": "長男",
                "perpetratorRelationship": "息子",
                "severity": "High",
                "description": "保護費の無断使用",
                "status": "Active",
                "interventions": ["分離検討", "日自事業利用"]
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        assert result["data"]["type"] == "経済的搾取"
        assert result["data"]["severity"] == "High"
        mock_audit.assert_called_once()
        mock_log.assert_called()


class TestRegisterMentalHealthStatus:
    """精神疾患状況登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_mental_health_status_success(self, mock_run_query, mock_audit):
        """精神疾患状況登録成功"""
        from lib.db_operations import register_mental_health_status

        mock_run_query.return_value = [{"diagnosis": "統合失調症"}]

        result = register_mental_health_status(
            mh_data={
                "diagnosis": "統合失調症",
                "currentStatus": "安定",
                "symptoms": ["幻聴（軽度）"],
                "treatmentStatus": "通院中"
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        assert result["data"]["diagnosis"] == "統合失調症"
        mock_audit.assert_called_once()

    @patch('lib.db_operations.run_query')
    def test_register_mental_health_status_no_diagnosis(self, mock_run_query):
        """診断名なしの場合スキップ"""
        from lib.db_operations import register_mental_health_status

        result = register_mental_health_status(
            mh_data={"currentStatus": "不明"},
            recipient_name="山田太郎"
        )

        assert result["status"] == "skipped"
        assert "診断名なし" in result["message"]
        mock_run_query.assert_not_called()


class TestRegisterMoneyManagementStatus:
    """金銭管理状況登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.log')
    @patch('lib.db_operations.run_query')
    def test_register_money_management_high_risk(self, mock_run_query, mock_log, mock_audit):
        """高リスク金銭管理状況登録"""
        from lib.db_operations import register_money_management_status

        mock_run_query.return_value = [{"capability": "要支援", "riskLevel": "High"}]

        result = register_money_management_status(
            mms_data={
                "capability": "要支援",
                "pattern": "浪費傾向",
                "riskLevel": "High",
                "triggers": ["給料日直後"],
                "observations": "月末に困窮することが多い"
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        mock_log.assert_called()
        mock_audit.assert_called_once()

    @patch('lib.db_operations.run_query')
    def test_register_money_management_low_risk(self, mock_run_query):
        """低リスク金銭管理状況登録（監査ログなし）"""
        from lib.db_operations import register_money_management_status

        mock_run_query.return_value = [{"capability": "自立", "riskLevel": "Low"}]

        result = register_money_management_status(
            mms_data={
                "capability": "自立",
                "riskLevel": "Low"
            },
            recipient_name="山田太郎"
        )

        assert result["status"] == "success"


class TestRegisterDailyLifeSupportService:
    """日常生活自立支援事業登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.log')
    @patch('lib.db_operations.run_query')
    def test_register_daily_life_support_service(self, mock_run_query, mock_log, mock_audit):
        """日自事業登録成功"""
        from lib.db_operations import register_daily_life_support_service

        mock_run_query.return_value = [{"services": ["金銭管理", "書類管理"], "status": "利用中"}]

        result = register_daily_life_support_service(
            dlss_data={
                "socialWelfareCouncil": "○○市社会福祉協議会",
                "services": ["金銭管理", "書類管理"],
                "frequency": "週1回",
                "specialist": "担当者B",
                "status": "利用中",
                "referralRoute": "福祉事務所紹介"
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        mock_audit.assert_called_once()


class TestRegisterCollaborationRecord:
    """多機関連携記録登録のテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.log')
    @patch('lib.db_operations.run_query')
    def test_register_collaboration_record(self, mock_run_query, mock_log, mock_audit):
        """連携記録登録成功"""
        from lib.db_operations import register_collaboration_record

        mock_run_query.return_value = [{"date": "2024-01-20", "type": "ケース会議"}]

        result = register_collaboration_record(
            collab_data={
                "date": "2024-01-20",
                "type": "ケース会議",
                "participants": ["福祉事務所", "社協", "医療機関"],
                "agenda": "金銭管理支援の検討",
                "decisions": ["日自事業利用開始"],
                "nextActions": ["契約手続き"],
                "involvedOrganizations": ["○○市社協"]
            },
            recipient_name="山田太郎",
            user_name="test_user"
        )

        assert result["status"] == "success"
        mock_audit.assert_called_once()


class TestRegisterToDatabase:
    """統合登録関数のテスト"""

    @patch('lib.db_operations.register_collaboration_record')
    @patch('lib.db_operations.register_support_goal')
    @patch('lib.db_operations.register_certificate')
    @patch('lib.db_operations.register_protection_decision')
    @patch('lib.db_operations.register_medical_institution')
    @patch('lib.db_operations.register_support_organization')
    @patch('lib.db_operations.register_family_member')
    @patch('lib.db_operations.register_key_person')
    @patch('lib.db_operations.register_wish')
    @patch('lib.db_operations.register_pathway_to_protection')
    @patch('lib.db_operations.register_declared_history')
    @patch('lib.db_operations.register_pattern')
    @patch('lib.db_operations.register_challenge')
    @patch('lib.db_operations.register_strength')
    @patch('lib.db_operations.register_case_record')
    @patch('lib.db_operations.register_trigger_situation')
    @patch('lib.db_operations.register_effective_approach')
    @patch('lib.db_operations.register_daily_life_support_service')
    @patch('lib.db_operations.register_money_management_status')
    @patch('lib.db_operations.register_economic_risk')
    @patch('lib.db_operations.register_ng_approach')
    @patch('lib.db_operations.register_mental_health_status')
    @patch('lib.db_operations.register_recipient')
    @patch('lib.db_operations.log')
    def test_register_to_database_full_data(self, mock_log, mock_recipient, mock_mh,
                                            mock_ng, mock_er, mock_mms, mock_dlss,
                                            mock_ea, mock_ts, mock_cr, mock_strength,
                                            mock_challenge, mock_pattern, mock_dh,
                                            mock_pathway, mock_wish, mock_kp, mock_fm,
                                            mock_so, mock_mi, mock_pd, mock_cert,
                                            mock_sg, mock_collab):
        """フルデータでの統合登録"""
        from lib.db_operations import register_to_database

        # 各モック関数の戻り値を設定
        mock_recipient.return_value = {"status": "success"}
        mock_mh.return_value = {"status": "success"}
        mock_ng.return_value = {"status": "success"}
        mock_er.return_value = {"status": "success"}

        data = {
            "recipient": {"name": "山田太郎", "caseNumber": "2024-001"},
            "mentalHealthStatus": {"diagnosis": "うつ病"},
            "ngApproaches": [{"description": "急かす対応"}],
            "economicRisks": [{"type": "経済的搾取"}],
        }

        result = register_to_database(data, user_name="test_user")

        assert result["status"] == "success"
        assert result["recipient_name"] == "山田太郎"
        assert result["registered_count"] >= 4
        mock_recipient.assert_called_once()
        mock_mh.assert_called_once()
        mock_ng.assert_called_once()
        mock_er.assert_called_once()

    def test_register_to_database_invalid_name(self):
        """無効な受給者名でエラー"""
        from lib.db_operations import register_to_database

        result = register_to_database({"recipient": {"name": ""}})

        assert result["status"] == "error"
        assert "受給者名" in result["message"] or "空" in result["message"]

    @patch('lib.db_operations.register_recipient')
    @patch('lib.db_operations.register_mental_health_status')
    @patch('lib.db_operations.log')
    def test_register_to_database_warning_no_ng_with_mental_health(
            self, mock_log, mock_mh, mock_recipient):
        """精神疾患あり・NGなしで警告"""
        from lib.db_operations import register_to_database

        mock_recipient.return_value = {"status": "success"}
        mock_mh.return_value = {"status": "success"}

        data = {
            "recipient": {"name": "山田太郎"},
            "mentalHealthStatus": {"diagnosis": "統合失調症"},
            # ngApproaches なし
        }

        result = register_to_database(data)

        assert result["status"] == "success"
        assert len(result["warnings"]) > 0
        assert "避けるべき関わり方" in result["warnings"][0]


class TestRegisterSupportOrganization:
    """支援機関登録のテスト"""

    @patch('lib.db_operations.run_query')
    def test_register_support_organization(self, mock_run_query):
        """支援機関登録成功"""
        from lib.db_operations import register_support_organization

        mock_run_query.return_value = [{"name": "○○地域包括支援センター"}]

        result = register_support_organization(
            org_data={
                "name": "○○地域包括支援センター",
                "type": "地域包括支援センター",
                "contactPerson": "担当者C",
                "phone": "03-1234-5678",
                "services": "生活支援",
                "utilizationStatus": "利用中"
            },
            recipient_name="山田太郎"
        )

        assert result["status"] == "success"


class TestRegisterKeyPerson:
    """キーパーソン登録のテスト"""

    @patch('lib.db_operations.run_query')
    def test_register_key_person(self, mock_run_query):
        """キーパーソン登録成功"""
        from lib.db_operations import register_key_person

        mock_run_query.return_value = [{"name": "佐藤次郎", "rank": 1}]

        result = register_key_person(
            kp_data={
                "name": "佐藤次郎",
                "relationship": "弟",
                "role": "緊急連絡先",
                "rank": 1
            },
            recipient_name="山田太郎"
        )

        assert result["status"] == "success"
        assert result["data"]["rank"] == 1


class TestRegisterProtectionDecision:
    """保護決定登録のテスト"""

    @patch('lib.db_operations.run_query')
    def test_register_protection_decision(self, mock_run_query):
        """保護決定登録成功"""
        from lib.db_operations import register_protection_decision

        mock_run_query.return_value = [{"type": "開始決定", "date": "2024-01-01"}]

        result = register_protection_decision(
            decision_data={
                "decisionDate": "2024-01-01",
                "type": "開始決定",
                "protectionCategory": "生活扶助",
                "monthlyAmount": 80000
            },
            recipient_name="山田太郎"
        )

        assert result["status"] == "success"

    @patch('lib.db_operations.run_query')
    def test_register_protection_decision_no_date(self, mock_run_query):
        """決定日なしでスキップ"""
        from lib.db_operations import register_protection_decision

        result = register_protection_decision(
            decision_data={"type": "開始決定"},
            recipient_name="山田太郎"
        )

        assert result["status"] == "skipped"
        mock_run_query.assert_not_called()


class TestEmptyResults:
    """空の結果を返すケースのテスト"""

    @patch('lib.db_operations.create_audit_log')
    @patch('lib.db_operations.run_query')
    def test_register_with_empty_result(self, mock_run_query, mock_audit):
        """クエリが空の結果を返す場合"""
        from lib.db_operations import register_recipient

        mock_run_query.return_value = []  # 空の結果

        result = register_recipient({"name": "山田太郎"})

        assert result["status"] == "success"
        assert result["data"] == {}  # 空の辞書
