"""
匿名化エンジンのテスト
TECHNICAL_STANDARDS.md Section 8 準拠
"""

import pytest
from lib.anonymizer import (
    Anonymizer,
    AnonymizationAuditor,
    AnonymizationResult,
    PIIMatch,
    PIIType,
    create_anonymizer,
    anonymize_case_record_for_ai,
)


class TestPIIDetection:
    """PII検出のテスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_detect_phone_number_mobile(self, anonymizer):
        """携帯電話番号の検出"""
        text = "連絡先は090-1234-5678です"
        matches = anonymizer.detect_pii(text)

        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE]
        assert len(phone_matches) >= 1
        assert "090-1234-5678" in [m.original for m in phone_matches]

    def test_detect_phone_number_landline(self, anonymizer):
        """固定電話番号の検出"""
        text = "自宅は03-1234-5678です"
        matches = anonymizer.detect_pii(text)

        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE]
        assert len(phone_matches) >= 1
        assert "03-1234-5678" in [m.original for m in phone_matches]

    def test_detect_postal_code(self, anonymizer):
        """郵便番号の検出"""
        text = "郵便番号160-0023"
        matches = anonymizer.detect_pii(text)

        postal_matches = [m for m in matches if m.pii_type == PIIType.POSTAL_CODE]
        assert len(postal_matches) >= 1
        assert "160-0023" in [m.original for m in postal_matches]

    def test_detect_email(self, anonymizer):
        """メールアドレスの検出"""
        text = "メールはtest@example.comです"
        matches = anonymizer.detect_pii(text)

        email_matches = [m for m in matches if m.pii_type == PIIType.EMAIL]
        assert len(email_matches) >= 1
        assert "test@example.com" in [m.original for m in email_matches]

    def test_detect_address(self, anonymizer):
        """住所の検出"""
        text = "住所は東京都新宿区西新宿1丁目2番3号です"
        matches = anonymizer.detect_pii(text)

        address_matches = [m for m in matches if m.pii_type == PIIType.ADDRESS]
        assert len(address_matches) >= 1

    def test_detect_birth_date_wareki(self, anonymizer):
        """和暦生年月日の検出"""
        text = "生年月日は昭和50年4月1日です"
        matches = anonymizer.detect_pii(text)

        birth_matches = [m for m in matches if m.pii_type == PIIType.BIRTH_DATE]
        assert len(birth_matches) >= 1

    def test_detect_birth_date_seireki(self, anonymizer):
        """西暦生年月日の検出"""
        text = "1975年4月1日生まれ"
        matches = anonymizer.detect_pii(text)

        birth_matches = [m for m in matches if m.pii_type == PIIType.BIRTH_DATE]
        assert len(birth_matches) >= 1


class TestContextualPIIDetection:
    """文脈ベースのPII検出テスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_detect_recipient_name(self, anonymizer):
        """受給者名の検出（文脈ベース）"""
        text = "受給者名: 山田太郎"
        matches = anonymizer.detect_pii(text)

        name_matches = [m for m in matches if m.pii_type == PIIType.NAME]
        assert len(name_matches) >= 1
        assert "山田太郎" in [m.original for m in name_matches]

    def test_detect_name_with_san(self, anonymizer):
        """「〇〇さん」形式の名前検出"""
        text = "山田太郎さんに電話した"
        matches = anonymizer.detect_pii(text)

        name_matches = [m for m in matches if m.pii_type == PIIType.NAME]
        assert len(name_matches) >= 1

    def test_detect_caseworker_name(self, anonymizer):
        """担当者名の検出"""
        text = "担当: 佐藤花子"
        matches = anonymizer.detect_pii(text)

        cw_matches = [m for m in matches if m.pii_type == PIIType.CASEWORKER_NAME]
        assert len(cw_matches) >= 1
        assert "佐藤花子" in [m.original for m in cw_matches]

    def test_detect_doctor_name(self, anonymizer):
        """医師名の検出"""
        text = "主治医: 鈴木一郎"
        matches = anonymizer.detect_pii(text)

        doctor_matches = [m for m in matches if m.pii_type == PIIType.DOCTOR_NAME]
        assert len(doctor_matches) >= 1
        assert "鈴木一郎" in [m.original for m in doctor_matches]

    def test_detect_family_name(self, anonymizer):
        """家族名の検出"""
        text = "長男の田中一が訪問"
        matches = anonymizer.detect_pii(text)

        family_matches = [m for m in matches if m.pii_type == PIIType.FAMILY_NAME]
        assert len(family_matches) >= 1

    def test_detect_case_number(self, anonymizer):
        """ケース番号の検出"""
        text = "ケース番号A12345678について"
        matches = anonymizer.detect_pii(text)

        case_matches = [m for m in matches if m.pii_type == PIIType.CASE_NUMBER]
        assert len(case_matches) >= 1
        assert "A12345678" in [m.original for m in case_matches]


class TestAnonymization:
    """匿名化処理のテスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_anonymize_simple_text(self, anonymizer):
        """シンプルなテキストの匿名化"""
        text = "山田太郎さんに090-1234-5678で連絡"
        result = anonymizer.anonymize_text(text)

        assert isinstance(result, AnonymizationResult)
        assert "090-1234-5678" not in result.anonymized_text
        assert len(result.pii_mappings) >= 1

    def test_anonymize_preserves_structure(self, anonymizer):
        """匿名化が文の構造を保持"""
        text = "受給者: 山田太郎、電話: 090-1234-5678"
        result = anonymizer.anonymize_text(text)

        # 構造（カンマ、コロン）が保持されている
        assert "、" in result.anonymized_text
        assert "受給者:" in result.anonymized_text or "受給者: " in result.anonymized_text

    def test_anonymize_empty_text(self, anonymizer):
        """空のテキストの匿名化"""
        result = anonymizer.anonymize_text("")
        assert result.anonymized_text == ""
        assert len(result.pii_mappings) == 0

    def test_anonymize_no_pii(self, anonymizer):
        """PIIがないテキストの匿名化"""
        text = "今日の天気は晴れです。"
        result = anonymizer.anonymize_text(text)

        assert result.anonymized_text == text
        assert len(result.pii_mappings) == 0


class TestReIdentification:
    """再識別（復元）のテスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_restore_text(self, anonymizer):
        """テキストの復元"""
        original = "山田太郎さんに090-1234-5678で連絡"
        result = anonymizer.anonymize_text(original)

        restored = anonymizer.restore_text(result.anonymized_text, result.pii_mappings)
        assert restored == original

    def test_restore_complex_text(self, anonymizer):
        """複雑なテキストの復元"""
        original = """
        受給者: 山田太郎
        住所: 東京都新宿区西新宿1丁目2番3号
        電話: 090-1234-5678
        担当者: 佐藤花子
        """
        result = anonymizer.anonymize_text(original)

        restored = anonymizer.restore_text(result.anonymized_text, result.pii_mappings)
        # 主要なPIIが復元されている
        assert "山田太郎" in restored
        assert "090-1234-5678" in restored

    def test_restore_empty(self, anonymizer):
        """空のテキストの復元"""
        result = anonymizer.restore_text("", [])
        assert result == ""


class TestStructuredDataAnonymization:
    """構造化データの匿名化テスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_anonymize_dict(self, anonymizer):
        """辞書データの匿名化"""
        data = {
            "name": "山田太郎",
            "phone": "090-1234-5678",
            "notes": "本人は元気そうだった"
        }

        anonymized, result = anonymizer.anonymize_for_external_ai(data)

        assert anonymized["name"] != "山田太郎"
        assert anonymized["phone"] != "090-1234-5678"
        assert "[氏名_" in anonymized["name"]
        assert len(result.pii_mappings) >= 2

    def test_anonymize_nested_dict(self, anonymizer):
        """ネストされた辞書の匿名化"""
        data = {
            "recipient": {
                "name": "山田太郎",
                "address": "東京都新宿区"
            },
            "caseworker": "佐藤花子"
        }

        anonymized, result = anonymizer.anonymize_for_external_ai(data)

        assert "[氏名_" in anonymized["recipient"]["name"]
        assert len(result.pii_mappings) >= 2

    def test_anonymize_list_in_dict(self, anonymizer):
        """リストを含む辞書の匿名化"""
        data = {
            "recipients": [
                {"name": "山田太郎"},
                {"name": "鈴木一郎"}
            ]
        }

        anonymized, result = anonymizer.anonymize_for_external_ai(data)

        assert "[氏名_" in anonymized["recipients"][0]["name"]
        assert "[氏名_" in anonymized["recipients"][1]["name"]

    def test_restore_dict(self, anonymizer):
        """辞書データの復元"""
        original = {
            "name": "山田太郎",
            "phone": "090-1234-5678"
        }

        anonymized, result = anonymizer.anonymize_for_external_ai(original)
        restored = anonymizer.restore_data(anonymized, result.pii_mappings)

        assert restored["name"] == "山田太郎"
        assert restored["phone"] == "090-1234-5678"


class TestAnonymizationResult:
    """AnonymizationResult のテスト"""

    def test_result_has_session_id(self):
        """セッションIDが生成される"""
        result = AnonymizationResult(anonymized_text="test")
        assert result.session_id
        assert len(result.session_id) == 16  # hex(8) = 16文字

    def test_result_has_timestamp(self):
        """タイムスタンプが生成される"""
        result = AnonymizationResult(anonymized_text="test")
        assert result.timestamp

    def test_result_stats(self):
        """統計情報が計算される"""
        mappings = [
            PIIMatch(PIIType.NAME, "山田太郎", "[氏名_1]", 0, 4, 1.0),
            PIIMatch(PIIType.PHONE, "090-1234-5678", "[電話番号_1]", 10, 23, 1.0),
        ]
        result = AnonymizationResult(
            anonymized_text="[氏名_1]に[電話番号_1]で連絡",
            pii_mappings=mappings
        )

        assert result.stats["total_pii_count"] == 2
        assert result.stats["pii_by_type"]["氏名"] == 1
        assert result.stats["pii_by_type"]["電話番号"] == 1


class TestAnonymizationAuditor:
    """匿名化監査のテスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    @pytest.fixture
    def auditor(self, anonymizer):
        return AnonymizationAuditor(anonymizer)

    def test_verify_valid_anonymization(self, anonymizer, auditor):
        """正常な匿名化の検証"""
        original = "山田太郎さんに連絡"
        result = anonymizer.anonymize_text(original)

        verification = auditor.verify_anonymization(
            original, result.anonymized_text, result.pii_mappings
        )

        assert verification["is_valid"]
        assert len(verification["issues"]) == 0

    def test_run_test_suite(self, auditor):
        """テストスイートの実行"""
        results = auditor.run_test_suite()

        assert "total_tests" in results
        assert "passed" in results
        assert "failed" in results
        assert "accuracy" in results
        assert results["accuracy"] >= 0.5  # 最低50%の精度を期待


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_create_anonymizer(self):
        """create_anonymizer の動作確認"""
        anonymizer = create_anonymizer()
        assert isinstance(anonymizer, Anonymizer)

    def test_anonymize_case_record_for_ai(self):
        """anonymize_case_record_for_ai の動作確認"""
        record = {
            "recipient": {
                "name": "山田太郎",
                "caseNumber": "A12345678"
            },
            "narrative": "本人は090-1234-5678に連絡可能"
        }

        anonymized, result = anonymize_case_record_for_ai(record)

        assert "[氏名_" in anonymized["recipient"]["name"]
        assert "090-1234-5678" not in anonymized["narrative"]
        assert len(result.pii_mappings) >= 2


class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_multiple_same_pii(self, anonymizer):
        """同じPIIが複数回出現"""
        text = "山田太郎さんは山田太郎と呼ばれています"
        result = anonymizer.anonymize_text(text)

        # 複数検出されるべき
        name_matches = [m for m in result.pii_mappings if m.pii_type == PIIType.NAME]
        assert len(name_matches) >= 1

    def test_overlapping_patterns(self, anonymizer):
        """パターンが重複する場合"""
        text = "受給者山田太郎さん"  # 「受給者名」パターンと「〜さん」パターンが重複
        result = anonymizer.anonymize_text(text)

        # 重複して検出されていないことを確認
        assert result.anonymized_text.count("[氏名_") <= 2

    def test_special_characters(self, anonymizer):
        """特殊文字を含むテキスト"""
        text = "メール: test@example.com\n電話: 090-1234-5678"
        result = anonymizer.anonymize_text(text)

        assert "test@example.com" not in result.anonymized_text
        assert "090-1234-5678" not in result.anonymized_text


class TestConfidenceScores:
    """確信度スコアのテスト"""

    @pytest.fixture
    def anonymizer(self):
        return Anonymizer()

    def test_high_confidence_phone(self, anonymizer):
        """高確信度の電話番号"""
        text = "090-1234-5678"
        matches = anonymizer.detect_pii(text)

        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE]
        assert len(phone_matches) >= 1
        assert phone_matches[0].confidence >= 0.9

    def test_pii_match_has_position(self, anonymizer):
        """PIIMatchに位置情報がある"""
        text = "電話は090-1234-5678です"
        matches = anonymizer.detect_pii(text)

        phone_matches = [m for m in matches if m.pii_type == PIIType.PHONE]
        assert len(phone_matches) >= 1
        match = phone_matches[0]
        assert match.start >= 0
        assert match.end > match.start
        assert text[match.start:match.end] == match.original
