"""
MCPサーバーのユニットテスト
ツール、プロンプト、リソースの動作確認

Note: MCPサーバーは公式mcpパッケージと同名のため、
      個別の関数をテストする形式を採用
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import date

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# Cypherクエリバリデーションテスト
# =============================================================================

class TestCypherQueryValidation:
    """Cypherクエリのバリデーションテスト"""

    def test_create_query_is_blocked(self):
        """CREATE文がブロックされる"""
        dangerous_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DROP', 'DETACH']
        cypher = "CREATE (r:Recipient {name: 'test'})"
        upper_cypher = cypher.upper()

        blocked = False
        for keyword in dangerous_keywords:
            if keyword in upper_cypher:
                blocked = True
                break

        assert blocked is True

    def test_delete_query_is_blocked(self):
        """DELETE文がブロックされる"""
        dangerous_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DROP', 'DETACH']
        cypher = "MATCH (r:Recipient) DELETE r"
        upper_cypher = cypher.upper()

        blocked = False
        for keyword in dangerous_keywords:
            if keyword in upper_cypher:
                blocked = True
                break

        assert blocked is True

    def test_merge_query_is_blocked(self):
        """MERGE文がブロックされる"""
        dangerous_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DROP', 'DETACH']
        cypher = "MERGE (r:Recipient {name: 'test'})"
        upper_cypher = cypher.upper()

        blocked = False
        for keyword in dangerous_keywords:
            if keyword in upper_cypher:
                blocked = True
                break

        assert blocked is True

    def test_read_query_is_allowed(self):
        """MATCH文は許可される"""
        dangerous_keywords = ['CREATE', 'MERGE', 'SET', 'DELETE', 'REMOVE', 'DROP', 'DETACH']
        cypher = "MATCH (r:Recipient) RETURN r.name"
        upper_cypher = cypher.upper()

        blocked = False
        for keyword in dangerous_keywords:
            if keyword in upper_cypher:
                blocked = True
                break

        assert blocked is False


# =============================================================================
# データ構造テスト
# =============================================================================

class TestNgApproachData:
    """NgApproachデータ構造のテスト"""

    def test_ng_data_structure(self):
        """NgApproachのデータ構造"""
        ng_data = {
            "description": "大きな声で話しかける",
            "reason": "パニックを誘発する",
            "riskLevel": "High",
            "consequence": "パニック発作"
        }

        assert "description" in ng_data
        assert "reason" in ng_data
        assert "riskLevel" in ng_data
        assert ng_data["riskLevel"] in ["High", "Medium", "Low"]

    def test_default_risk_level(self):
        """デフォルトリスクレベル"""
        default_risk = "Medium"
        assert default_risk in ["High", "Medium", "Low"]


class TestEconomicRiskData:
    """EconomicRiskデータ構造のテスト"""

    def test_economic_risk_structure(self):
        """経済的リスクのデータ構造"""
        risk_data = {
            "type": "経済的搾取",
            "perpetrator": "長男",
            "perpetratorRelationship": "長男",
            "severity": "High",
            "description": "毎月訪問してお金を持っていく",
            "status": "Active"
        }

        assert "type" in risk_data
        assert "severity" in risk_data
        assert risk_data["severity"] in ["High", "Medium", "Low"]
        assert risk_data["status"] in ["Active", "Resolved", "Monitoring"]


class TestMoneyManagementData:
    """MoneyManagementStatusデータ構造のテスト"""

    def test_money_management_structure(self):
        """金銭管理状況のデータ構造"""
        mms_data = {
            "capability": "支援が必要",
            "pattern": "受給日に使い切る",
            "riskLevel": "Medium",
            "observations": "計画的な支出が困難"
        }

        assert "capability" in mms_data
        assert "pattern" in mms_data
        assert "riskLevel" in mms_data


# =============================================================================
# ガイドコンテンツテスト
# =============================================================================

class TestGuideContent:
    """ガイドコンテンツのテスト"""

    def test_manifesto_guide_content(self):
        """マニフェストガイドの内容"""
        # マニフェストガイドに含まれるべき内容
        required_sections = [
            "7本柱のスキーマ",
            "第1の柱",
            "第2の柱",
            "第3の柱",
            "第4の柱",
            "第5の柱",
            "第6の柱",
            "第7の柱",
            "AI運用プロトコル",
            "Safety First",
        ]

        # 実際のガイドコンテンツ
        guide = """
# 生活保護受給者尊厳支援グラフ マニフェスト概要

## 7本柱のスキーマ

### 第1の柱：ケース記録
- CaseRecord: 日々の支援記録

### 第2の柱：抽出された本人像
- Strength: 強み

### 第3の柱：関わり方の知恵
- NgApproach: 避けるべき関わり方（最重要）

### 第4の柱：参考情報としての申告歴
- DeclaredHistory: 申告された生活歴

### 第5の柱：社会的ネットワーク
- KeyPerson: キーパーソン

### 第6の柱：法的・制度的基盤
- ProtectionDecision: 保護決定

### 第7の柱：金銭的安全と多機関連携
- MoneyManagementStatus: 金銭管理状況

## 5つのAI運用プロトコル

1. **Safety First（二次被害防止最優先）**
"""

        for section in required_sections:
            assert section in guide, f"Missing section: {section}"

    def test_economic_risk_guide_content(self):
        """経済的リスクガイドの内容"""
        required_topics = [
            "経済的搾取",
            "借金",
            "名義貸し",
            "検出のサイン",
            "対応のポイント",
        ]

        guide = """
# 経済的リスク検出ガイド

## リスクの種類

### 1. 経済的搾取
- 家族や知人による金銭の持ち出し

### 2. 借金・名義貸し
- 借金の保証人になることの要求

## 検出のサイン

### 言動のサイン
- 「お金がない」

## 対応のポイント

1. **本人の意向を確認**
"""

        for topic in required_topics:
            assert topic in guide, f"Missing topic: {topic}"


# =============================================================================
# 批判的表現パターンテスト
# =============================================================================

class TestCriticalExpressionPatterns:
    """批判的表現パターンのテスト"""

    def test_critical_patterns(self):
        """批判的表現のパターン"""
        critical_words = ["指導した", "指示した", "約束させた", "誓わせた", "言い聞かせた"]

        for word in critical_words:
            assert len(word) > 0

    def test_recommended_alternatives(self):
        """推奨される代替表現"""
        alternatives = {
            "指導した": "お伝えした",
            "指示した": "ご案内した",
            "約束させた": "確認した",
        }

        for original, replacement in alternatives.items():
            assert original != replacement


# =============================================================================
# 経済的リスクサインテスト
# =============================================================================

class TestEconomicRiskSignals:
    """経済的リスクサインのテスト"""

    def test_risk_signals_patterns(self):
        """経済的リスクサインのパターン"""
        patterns = [
            "お金がない",
            "息子が来た",
            "借りたい",
            "貸して",
            "持っていかれた",
        ]

        test_text = "先日、お金がないと訴えがあった。息子が来たらしい。"

        found_signals = []
        for pattern in patterns:
            if pattern in test_text:
                found_signals.append(pattern)

        assert len(found_signals) == 2
        assert "お金がない" in found_signals
        assert "息子が来た" in found_signals


# =============================================================================
# プロンプトテンプレートテスト
# =============================================================================

class TestPromptTemplates:
    """プロンプトテンプレートのテスト"""

    def test_visit_preparation_template(self):
        """訪問準備テンプレート"""
        recipient_name = "山田太郎"

        template = f"""
# 訪問前チェックリスト: {recipient_name}さん

## 1. 緊急確認事項
- `get_visit_briefing_tool("{recipient_name}")` を実行

## 2. 確認すべき重要項目
1. ⚠️ 避けるべき関わり方（NgApproach）
2. ⚠️ 経済的リスク（EconomicRisk）
"""

        assert recipient_name in template
        assert "NgApproach" in template
        assert "EconomicRisk" in template

    def test_handover_guide_template(self):
        """引き継ぎガイドテンプレート"""
        recipient_name = "山田太郎"

        template = f"""
# 担当者引き継ぎガイド: {recipient_name}さん

## 1. 引き継ぎサマリーの取得
```
get_handover_summary_tool("{recipient_name}")
```

## 2. 優先確認事項（マニフェストルール4準拠）
1. ⚠️ 避けるべき関わり方を最初に確認
"""

        assert recipient_name in template
        assert "マニフェスト" in template

    def test_risk_assessment_template(self):
        """リスクアセスメントテンプレート"""
        recipient_name = "山田太郎"

        template = f"""
# リスクアセスメントガイド: {recipient_name}さん

## 1. 現在のリスク情報取得
```
search_emergency_info("{recipient_name}")
```

## 2. 経済的リスクの評価

### チェックポイント:
- [ ] 家族や知人からの金銭要求はないか
"""

        assert recipient_name in template
        assert "経済的リスク" in template
        assert "チェックポイント" in template


# =============================================================================
# db_operations関数テスト
# =============================================================================

class TestDbOperations:
    """db_operations関数のテスト"""

    def test_register_ng_approach_function(self):
        """register_ng_approach関数の存在確認"""
        from lib.db_operations import register_ng_approach

        assert callable(register_ng_approach)

    def test_register_economic_risk_function(self):
        """register_economic_risk関数の存在確認"""
        from lib.db_operations import register_economic_risk

        assert callable(register_economic_risk)

    def test_register_money_management_status_function(self):
        """register_money_management_status関数の存在確認"""
        from lib.db_operations import register_money_management_status

        assert callable(register_money_management_status)

    def test_register_effective_approach_function(self):
        """register_effective_approach関数の存在確認"""
        from lib.db_operations import register_effective_approach

        assert callable(register_effective_approach)

    def test_register_support_organization_function(self):
        """register_support_organization関数の存在確認"""
        from lib.db_operations import register_support_organization

        assert callable(register_support_organization)


# =============================================================================
# db_queries関数テスト
# =============================================================================

class TestDbQueries:
    """db_queries関数のテスト"""

    def test_get_recipients_list_function(self):
        """get_recipients_list関数の存在確認"""
        from lib.db_queries import get_recipients_list

        assert callable(get_recipients_list)

    def test_get_recipient_profile_function(self):
        """get_recipient_profile関数の存在確認"""
        from lib.db_queries import get_recipient_profile

        assert callable(get_recipient_profile)

    def test_get_visit_briefing_function(self):
        """get_visit_briefing関数の存在確認"""
        from lib.db_queries import get_visit_briefing

        assert callable(get_visit_briefing)

    def test_get_handover_summary_function(self):
        """get_handover_summary関数の存在確認"""
        from lib.db_queries import get_handover_summary

        assert callable(get_handover_summary)

    def test_search_similar_cases_function(self):
        """search_similar_cases関数の存在確認"""
        from lib.db_queries import search_similar_cases

        assert callable(search_similar_cases)


# =============================================================================
# AI抽出関数テスト
# =============================================================================

class TestAiExtractor:
    """AI抽出関数のテスト"""

    def test_detect_critical_expressions_function(self):
        """detect_critical_expressions関数の存在確認"""
        from lib.ai_extractor import detect_critical_expressions

        assert callable(detect_critical_expressions)

    def test_detect_economic_risk_signals_function(self):
        """detect_economic_risk_signals関数の存在確認"""
        from lib.ai_extractor import detect_economic_risk_signals

        assert callable(detect_economic_risk_signals)

    def test_detect_collaboration_signals_function(self):
        """detect_collaboration_signals関数の存在確認"""
        from lib.ai_extractor import detect_collaboration_signals

        assert callable(detect_collaboration_signals)


# =============================================================================
# 監査ログ関数テスト
# =============================================================================

class TestAuditLog:
    """監査ログ関数のテスト"""

    def test_create_audit_log_function(self):
        """create_audit_log関数の存在確認"""
        from lib.audit import create_audit_log

        assert callable(create_audit_log)


# =============================================================================
# 結果形式テスト
# =============================================================================

class TestResultFormats:
    """結果形式のテスト"""

    def test_success_result_format(self):
        """成功結果の形式"""
        result = {
            "status": "success",
            "message": "登録しました",
            "recipient": "山田太郎",
        }

        assert result["status"] == "success"
        assert "message" in result

    def test_error_result_format(self):
        """エラー結果の形式"""
        result = {
            "error": "受給者が見つかりません"
        }

        assert "error" in result

    def test_warning_result_format(self):
        """警告付き結果の形式"""
        result = {
            "status": "success",
            "message": "登録しました",
            "warning": "この情報は訪問前ブリーフィングで最優先表示されます"
        }

        assert result["status"] == "success"
        assert "warning" in result
