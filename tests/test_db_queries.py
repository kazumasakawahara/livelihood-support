"""
lib/db_queries.py のユニットテスト
モックを使用したデータ取得・検索機能のテスト
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetRecipientsList:
    """受給者一覧取得のテスト"""

    @patch('lib.db_queries.run_query')
    def test_get_recipients_list_success(self, mock_run_query):
        """受給者一覧取得成功"""
        from lib.db_queries import get_recipients_list

        mock_run_query.return_value = [
            {"name": "山田太郎"},
            {"name": "鈴木花子"},
            {"name": "佐藤次郎"}
        ]

        result = get_recipients_list()

        assert len(result) == 3
        assert "山田太郎" in result
        assert "鈴木花子" in result
        mock_run_query.assert_called_once()

    @patch('lib.db_queries.run_query')
    def test_get_recipients_list_empty(self, mock_run_query):
        """受給者なしの場合"""
        from lib.db_queries import get_recipients_list

        mock_run_query.return_value = []

        result = get_recipients_list()

        assert result == []


class TestGetRecipientStats:
    """受給者統計取得のテスト"""

    @patch('lib.db_queries.run_query')
    def test_get_recipient_stats_success(self, mock_run_query):
        """統計情報取得成功"""
        from lib.db_queries import get_recipient_stats

        # 各クエリの戻り値をシーケンスで設定
        mock_run_query.side_effect = [
            [{"c": 10}],  # recipient_count
            [{"name": "山田太郎", "ng_count": 2}, {"name": "鈴木花子", "ng_count": 1}],  # ng_by_recipient
            [{"c": 5}],  # mental_health_count
            [{"c": 3}],  # economic_risk_count
        ]

        result = get_recipient_stats()

        assert result["recipient_count"] == 10
        assert len(result["ng_by_recipient"]) == 2
        assert result["mental_health_count"] == 5
        assert result["economic_risk_count"] == 3
        assert mock_run_query.call_count == 4


class TestGetRecipientProfile:
    """受給者プロフィール取得のテスト"""

    @patch('lib.db_queries.run_query')
    def test_get_recipient_profile_full(self, mock_run_query):
        """フルプロフィール取得"""
        from lib.db_queries import get_recipient_profile

        # 各クエリの戻り値を設定
        mock_run_query.side_effect = [
            # ng_approaches
            [{"description": "金銭話題を急に出す", "reason": "トラウマ", "riskLevel": "High", "consequence": "パニック"}],
            # economic_risks
            [{"type": "経済的搾取", "perpetrator": "長男", "relationship": "息子", "severity": "High", "description": "保護費の無断使用"}],
            # mental_health
            [{"diagnosis": "うつ病", "status": "安定", "symptoms": ["不眠"], "treatment": "通院中"}],
            # money_status
            [{"capability": "要支援", "pattern": "浪費傾向", "riskLevel": "Medium", "observations": "月末困窮"}],
            # daily_life_support
            [{"swc": "○○市社協", "services": ["金銭管理"], "status": "利用中", "specialist": "担当A"}],
            # effective_approaches
            [{"description": "ゆっくり話す", "context": "面談時"}],
            # strengths
            [{"description": "絵を描くのが得意", "context": "趣味"}],
            # recent_records
            [{"date": "2024-01-15", "category": "訪問", "content": "自宅訪問", "response": "良好"}],
            # support_orgs
            [{"name": "地域包括支援センター", "type": "包括", "contact": "担当B"}],
        ]

        result = get_recipient_profile("山田太郎")

        assert result["recipient_name"] == "山田太郎"
        assert len(result["ng_approaches"]) == 1
        assert result["ng_approaches"][0]["riskLevel"] == "High"
        assert len(result["economic_risks"]) == 1
        assert result["mental_health"]["diagnosis"] == "うつ病"
        assert result["money_status"]["capability"] == "要支援"
        assert result["daily_life_support"]["services"] == ["金銭管理"]
        assert mock_run_query.call_count == 9

    @patch('lib.db_queries.run_query')
    def test_get_recipient_profile_minimal(self, mock_run_query):
        """最小限のプロフィール（データなし）"""
        from lib.db_queries import get_recipient_profile

        # すべて空を返す
        mock_run_query.return_value = []

        result = get_recipient_profile("新規受給者")

        assert result["recipient_name"] == "新規受給者"
        assert result["ng_approaches"] == []
        assert result["mental_health"] is None
        assert result["money_status"] is None


class TestGetHandoverSummary:
    """引き継ぎサマリー生成のテスト"""

    @patch('lib.db_queries.get_recipient_profile')
    def test_get_handover_summary_full(self, mock_profile):
        """フルサマリー生成"""
        from lib.db_queries import get_handover_summary

        mock_profile.return_value = {
            "recipient_name": "山田太郎",
            "ng_approaches": [
                {"description": "金銭話題", "reason": "トラウマ", "riskLevel": "High", "consequence": None}
            ],
            "economic_risks": [
                {"type": "経済的搾取", "perpetrator": "長男", "relationship": "息子", "severity": "High", "description": "保護費の無断使用"}
            ],
            "mental_health": {"diagnosis": "うつ病", "status": "安定", "treatment": "通院中"},
            "effective_approaches": [
                {"description": "ゆっくり話す", "context": "面談時"}
            ],
            "strengths": [
                {"description": "絵を描くのが得意"}
            ],
            "money_status": {"capability": "要支援", "pattern": "浪費傾向"},
            "daily_life_support": {"swc": "○○市社協", "services": ["金銭管理"], "status": "利用中", "specialist": "担当A"},
            "support_organizations": [
                {"name": "地域包括支援センター", "type": "包括", "contact": "担当B"}
            ],
            "recent_records": []
        }

        result = get_handover_summary("山田太郎")

        assert "山田太郎" in result
        assert "避けるべき関わり方" in result
        assert "金銭話題" in result
        assert "経済的リスク" in result
        assert "経済的搾取" in result
        assert "精神疾患" in result
        assert "うつ病" in result
        assert "効果的だった関わり方" in result
        assert "発見された強み" in result
        assert "金銭管理と支援サービス" in result
        assert "連携機関" in result

    @patch('lib.db_queries.get_recipient_profile')
    def test_get_handover_summary_minimal(self, mock_profile):
        """最小限のサマリー（データなし）"""
        from lib.db_queries import get_handover_summary

        mock_profile.return_value = {
            "recipient_name": "新規受給者",
            "ng_approaches": [],
            "economic_risks": [],
            "mental_health": None,
            "effective_approaches": [],
            "strengths": [],
            "money_status": None,
            "daily_life_support": None,
            "support_organizations": [],
            "recent_records": []
        }

        result = get_handover_summary("新規受給者")

        assert "新規受給者" in result
        # 各セクションは含まれない
        assert "避けるべき関わり方" not in result
        assert "経済的リスク" not in result


class TestSearchSimilarCases:
    """類似案件検索のテスト"""

    @patch('lib.db_queries.run_query')
    def test_search_similar_cases_found(self, mock_run_query):
        """類似ケース発見"""
        from lib.db_queries import search_similar_cases

        mock_run_query.return_value = [
            {"類似ケース": "鈴木花子", "共通リスク": ["経済的搾取"], "利用サービス": ["金銭管理"], "リスク状態": "Resolved"}
        ]

        result = search_similar_cases("山田太郎")

        assert len(result) == 1
        assert result[0]["類似ケース"] == "鈴木花子"
        mock_run_query.assert_called_once()

    @patch('lib.db_queries.run_query')
    def test_search_similar_cases_none(self, mock_run_query):
        """類似ケースなし"""
        from lib.db_queries import search_similar_cases

        mock_run_query.return_value = []

        result = search_similar_cases("山田太郎")

        assert result == []


class TestFindMatchingPatterns:
    """パターンマッチングのテスト"""

    @patch('lib.db_queries.run_query')
    def test_find_matching_patterns_found(self, mock_run_query):
        """マッチするパターン発見"""
        from lib.db_queries import find_matching_patterns

        mock_run_query.return_value = [
            {
                "パターン名": "経済的搾取・日自事業",
                "説明": "家族からの経済的搾取があり日常生活自立支援事業を利用",
                "推奨介入": ["分離検討", "日自事業利用"],
                "関連サービス": ["社協金銭管理"],
                "成功件数": 5
            }
        ]

        result = find_matching_patterns("山田太郎")

        assert len(result) == 1
        assert result[0]["パターン名"] == "経済的搾取・日自事業"
        assert result[0]["成功件数"] == 5

    @patch('lib.db_queries.run_query')
    def test_find_matching_patterns_none(self, mock_run_query):
        """マッチするパターンなし"""
        from lib.db_queries import find_matching_patterns

        mock_run_query.return_value = []

        result = find_matching_patterns("山田太郎")

        assert result == []


class TestGetVisitBriefing:
    """訪問前ブリーフィング取得のテスト"""

    @patch('lib.db_queries.run_query')
    def test_get_visit_briefing_success(self, mock_run_query):
        """ブリーフィング取得成功"""
        from lib.db_queries import get_visit_briefing

        mock_run_query.return_value = [{
            "受給者名": "山田太郎",
            "避けるべき関わり方": [{"description": "金銭話題", "reason": "トラウマ", "risk": "High"}],
            "経済的リスク": [{"type": "経済的搾取", "perpetrator": "長男", "severity": "High"}],
            "精神疾患": "うつ病",
            "疾患の状態": "安定",
            "金銭管理能力": "要支援",
            "金銭管理パターン": "浪費傾向",
            "自立支援サービス": ["金銭管理"],
            "効果的な関わり方": [{"description": "ゆっくり話す", "context": "面談時"}]
        }]

        result = get_visit_briefing("山田太郎")

        assert result["受給者名"] == "山田太郎"
        assert len(result["避けるべき関わり方"]) == 1
        assert result["精神疾患"] == "うつ病"
        assert result["金銭管理能力"] == "要支援"

    @patch('lib.db_queries.run_query')
    def test_get_visit_briefing_not_found(self, mock_run_query):
        """受給者が見つからない場合"""
        from lib.db_queries import get_visit_briefing

        mock_run_query.return_value = []

        result = get_visit_briefing("存在しない受給者")

        assert result == {}


class TestGetCollaborationHistory:
    """連携履歴取得のテスト"""

    @patch('lib.db_queries.run_query')
    def test_get_collaboration_history_success(self, mock_run_query):
        """連携履歴取得成功"""
        from lib.db_queries import get_collaboration_history

        mock_run_query.return_value = [
            {
                "日付": "2024-01-20",
                "種別": "ケース会議",
                "参加者": ["福祉事務所", "社協"],
                "決定事項": ["日自事業利用開始"],
                "次回アクション": ["契約手続き"],
                "関係機関": ["○○市社協"]
            },
            {
                "日付": "2024-01-10",
                "種別": "電話連絡",
                "参加者": ["福祉事務所"],
                "決定事項": [],
                "次回アクション": ["訪問予定"],
                "関係機関": []
            }
        ]

        result = get_collaboration_history("山田太郎", limit=10)

        assert len(result) == 2
        assert result[0]["種別"] == "ケース会議"
        assert result[1]["種別"] == "電話連絡"

    @patch('lib.db_queries.run_query')
    def test_get_collaboration_history_with_limit(self, mock_run_query):
        """制限付きで履歴取得"""
        from lib.db_queries import get_collaboration_history

        mock_run_query.return_value = [
            {"日付": "2024-01-20", "種別": "ケース会議", "参加者": [], "決定事項": [], "次回アクション": [], "関係機関": []}
        ]

        result = get_collaboration_history("山田太郎", limit=5)

        # limitパラメータがクエリに渡されることを確認
        call_args = mock_run_query.call_args
        # run_query(query, params) の params が2番目の位置引数
        params = call_args[0][1]  # 位置引数の2番目
        assert params["limit"] == 5

    @patch('lib.db_queries.run_query')
    def test_get_collaboration_history_empty(self, mock_run_query):
        """連携履歴なし"""
        from lib.db_queries import get_collaboration_history

        mock_run_query.return_value = []

        result = get_collaboration_history("山田太郎")

        assert result == []


class TestProfileDataIntegrity:
    """プロフィールデータ整合性のテスト"""

    @patch('lib.db_queries.run_query')
    def test_mental_health_single_result(self, mock_run_query):
        """精神疾患が複数ある場合最初のみ返す"""
        from lib.db_queries import get_recipient_profile

        # 精神疾患のクエリのみ複数結果を返す
        mock_run_query.side_effect = [
            [],  # ng_approaches
            [],  # economic_risks
            [{"diagnosis": "うつ病"}, {"diagnosis": "不安障害"}],  # mental_health（複数）
            [],  # money_status
            [],  # daily_life_support
            [],  # effective_approaches
            [],  # strengths
            [],  # recent_records
            [],  # support_orgs
        ]

        result = get_recipient_profile("山田太郎")

        # 最初の結果のみ返される
        assert result["mental_health"]["diagnosis"] == "うつ病"

    @patch('lib.db_queries.run_query')
    def test_risk_level_ordering(self, mock_run_query):
        """リスクレベルの順序確認"""
        from lib.db_queries import get_recipient_profile

        mock_run_query.side_effect = [
            # ng_approaches - リスクレベル順で返される想定
            [
                {"description": "高リスク行動", "reason": "", "riskLevel": "High", "consequence": ""},
                {"description": "中リスク行動", "reason": "", "riskLevel": "Medium", "consequence": ""},
            ],
            [],  # economic_risks
            [],  # mental_health
            [],  # money_status
            [],  # daily_life_support
            [],  # effective_approaches
            [],  # strengths
            [],  # recent_records
            [],  # support_orgs
        ]

        result = get_recipient_profile("山田太郎")

        assert result["ng_approaches"][0]["riskLevel"] == "High"
        assert result["ng_approaches"][1]["riskLevel"] == "Medium"
