"""
lib/utils.py のユニットテスト
ユーティリティ関数のテスト（和暦変換、日付処理）
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from lib.utils import (
    convert_wareki_to_seireki,
    safe_date_parse,
    calculate_age,
    format_date_with_age,
    get_risk_emoji,
    get_status_badge,
    format_mental_health_warning,
    get_input_example,
    _convert_gengo_to_date,
)


class TestConvertWarekiToSeireki:
    """和暦→西暦変換のテスト"""

    def test_showa_kanji(self):
        """昭和（漢字形式）"""
        result = convert_wareki_to_seireki("昭和50年3月15日")
        assert result == "1975-03-15"

    def test_heisei_kanji(self):
        """平成（漢字形式）"""
        # 注: 「元年」は数字でないためサポートされていない。「1年」を使用。
        result = convert_wareki_to_seireki("平成1年1月8日")
        assert result == "1989-01-08"

    def test_reiwa_kanji(self):
        """令和（漢字形式）"""
        result = convert_wareki_to_seireki("令和5年10月1日")
        assert result == "2023-10-01"

    def test_showa_alphabet(self):
        """昭和（アルファベット形式）"""
        result = convert_wareki_to_seireki("S50.3.15")
        assert result == "1975-03-15"

    def test_heisei_alphabet(self):
        """平成（アルファベット形式）"""
        result = convert_wareki_to_seireki("H1.1.8")
        assert result == "1989-01-08"

    def test_reiwa_alphabet(self):
        """令和（アルファベット形式）"""
        result = convert_wareki_to_seireki("R5.10.1")
        assert result == "2023-10-01"

    def test_meiji(self):
        """明治"""
        result = convert_wareki_to_seireki("明治45年7月30日")
        assert result == "1912-07-30"

    def test_taisho(self):
        """大正"""
        result = convert_wareki_to_seireki("大正15年12月25日")
        assert result == "1926-12-25"

    def test_slash_separator(self):
        """スラッシュ区切り"""
        result = convert_wareki_to_seireki("昭和50/3/15")
        assert result == "1975-03-15"

    def test_invalid_format(self):
        """不正な形式"""
        result = convert_wareki_to_seireki("無効な日付")
        assert result is None

    def test_empty_string(self):
        """空文字列"""
        result = convert_wareki_to_seireki("")
        assert result is None

    def test_none_value(self):
        """None"""
        result = convert_wareki_to_seireki(None)
        assert result is None

    def test_invalid_date(self):
        """存在しない日付"""
        result = convert_wareki_to_seireki("昭和50年2月30日")
        assert result is None


class TestSafeDateParse:
    """safe_date_parse関数のテスト"""

    def test_iso_format(self):
        """ISO形式（YYYY-MM-DD）"""
        result = safe_date_parse("2024-12-28")
        assert result == date(2024, 12, 28)

    def test_slash_format(self):
        """スラッシュ形式（YYYY/MM/DD）"""
        result = safe_date_parse("2024/12/28")
        assert result == date(2024, 12, 28)

    def test_wareki_format(self):
        """和暦形式"""
        result = safe_date_parse("昭和50年3月15日")
        assert result == date(1975, 3, 15)

    def test_empty_string(self):
        """空文字列"""
        result = safe_date_parse("")
        assert result is None

    def test_none_value(self):
        """None"""
        result = safe_date_parse(None)
        assert result is None

    def test_invalid_date(self):
        """不正な日付"""
        result = safe_date_parse("無効な日付")
        assert result is None

    def test_whitespace(self):
        """前後の空白は無視"""
        result = safe_date_parse("  2024-12-28  ")
        assert result == date(2024, 12, 28)


class TestCalculateAge:
    """calculate_age関数のテスト"""

    def test_age_from_date(self):
        """日付オブジェクトから年齢計算"""
        birth = date(1980, 5, 15)
        ref = date(2024, 12, 28)
        result = calculate_age(birth, ref)
        assert result == 44

    def test_age_before_birthday(self):
        """誕生日前は年齢-1"""
        birth = date(1980, 12, 31)
        ref = date(2024, 12, 28)
        result = calculate_age(birth, ref)
        assert result == 43

    def test_age_on_birthday(self):
        """誕生日当日"""
        birth = date(1980, 12, 28)
        ref = date(2024, 12, 28)
        result = calculate_age(birth, ref)
        assert result == 44

    def test_age_from_string(self):
        """文字列から年齢計算"""
        result = calculate_age("1980-05-15", date(2024, 12, 28))
        assert result == 44

    def test_age_from_wareki(self):
        """和暦から年齢計算"""
        result = calculate_age("昭和55年5月15日", date(2024, 12, 28))
        assert result == 44

    def test_none_birth_date(self):
        """生年月日がNone"""
        result = calculate_age(None)
        assert result is None

    def test_invalid_string(self):
        """不正な日付文字列"""
        result = calculate_age("無効な日付")
        assert result is None


class TestFormatDateWithAge:
    """format_date_with_age関数のテスト"""

    def test_date_with_age(self):
        """日付と年齢を整形"""
        # 動的に今日の日付を使うため、固定値でのテストが難しい
        # 代わりに形式が正しいかをテスト
        result = format_date_with_age(date(1980, 5, 15))
        assert result.startswith("1980-05-15")
        assert "歳" in result

    def test_none_value(self):
        """Noneの場合"""
        result = format_date_with_age(None)
        assert result == "不明"

    def test_string_date(self):
        """文字列日付"""
        result = format_date_with_age("1980-05-15")
        assert result.startswith("1980-05-15")
        assert "歳" in result

    def test_invalid_string(self):
        """不正な文字列はそのまま返す"""
        result = format_date_with_age("無効な日付")
        assert result == "無効な日付"


class TestGetRiskEmoji:
    """get_risk_emoji関数のテスト"""

    def test_high_risk(self):
        """Highリスク"""
        assert get_risk_emoji("High") == "🔴"

    def test_medium_risk(self):
        """Mediumリスク"""
        assert get_risk_emoji("Medium") == "🟠"

    def test_low_risk(self):
        """Lowリスク"""
        assert get_risk_emoji("Low") == "🟡"

    def test_unknown_risk(self):
        """不明なリスクレベル"""
        assert get_risk_emoji("Unknown") == "⚪"

    def test_empty_risk(self):
        """空文字列"""
        assert get_risk_emoji("") == "⚪"


class TestGetStatusBadge:
    """get_status_badge関数のテスト"""

    def test_active_status(self):
        """Activeステータス"""
        result = get_status_badge("Active")
        assert "Active" in result
        assert "#28a745" in result  # 緑色
        assert "background-color" in result

    def test_improving_status(self):
        """Improvingステータス"""
        result = get_status_badge("Improving")
        assert "Improving" in result
        assert "#17a2b8" in result  # 青色

    def test_resolved_status(self):
        """Resolvedステータス"""
        result = get_status_badge("Resolved")
        assert "Resolved" in result
        assert "#6c757d" in result  # グレー

    def test_high_risk_status(self):
        """Highステータス（リスク）"""
        result = get_status_badge("High")
        assert "High" in result
        assert "#dc3545" in result  # 赤色

    def test_medium_risk_status(self):
        """Mediumステータス（リスク）"""
        result = get_status_badge("Medium")
        assert "Medium" in result
        assert "#fd7e14" in result  # オレンジ

    def test_low_risk_status(self):
        """Lowステータス（リスク）"""
        result = get_status_badge("Low")
        assert "Low" in result
        assert "#ffc107" in result  # 黄色

    def test_unknown_status(self):
        """不明なステータス"""
        result = get_status_badge("Unknown")
        assert "Unknown" in result
        assert "#6c757d" in result  # デフォルトはグレー


class TestFormatMentalHealthWarning:
    """format_mental_health_warning関数のテスト"""

    def test_warning_contains_diagnosis(self):
        """警告メッセージに診断名が含まれる"""
        result = format_mental_health_warning("うつ病")
        assert "うつ病" in result
        assert "精神疾患" in result

    def test_warning_contains_guidance(self):
        """警告メッセージに対応ガイダンスが含まれる"""
        result = format_mental_health_warning("統合失調症")
        assert "批判的な言葉かけ" in result
        assert "就労への性急な圧力" in result
        assert "約束や期限の強要" in result
        assert "長時間の面談" in result

    def test_warning_contains_support_message(self):
        """支援メッセージが含まれる"""
        result = format_mental_health_warning("不安障害")
        assert "本人のペースを尊重" in result
        assert "伴走する姿勢" in result


class TestGetInputExample:
    """get_input_example関数のテスト"""

    def test_returns_example_text(self):
        """入力例テキストを返す"""
        result = get_input_example()
        assert isinstance(result, str)
        assert len(result) > 100  # 十分な長さがある

    def test_contains_visit_record(self):
        """訪問記録の要素が含まれる"""
        result = get_input_example()
        assert "訪問" in result
        assert "山田太郎" in result

    def test_contains_health_info(self):
        """健康情報が含まれる"""
        result = get_input_example()
        assert "うつ病" in result
        assert "通院" in result

    def test_contains_family_info(self):
        """家族情報が含まれる"""
        result = get_input_example()
        assert "元妻" in result
        assert "実母" in result


class TestConvertGengoToDate:
    """_convert_gengo_to_date関数のテスト"""

    def test_valid_gengo(self):
        """有効な元号"""
        result = _convert_gengo_to_date("昭和", 50, 3, 15)
        assert result == "1975-03-15"

    def test_invalid_gengo(self):
        """無効な元号"""
        result = _convert_gengo_to_date("無効", 50, 3, 15)
        assert result is None

    def test_alphabet_gengo(self):
        """アルファベット元号"""
        result = _convert_gengo_to_date("S", 50, 3, 15)
        assert result == "1975-03-15"

    def test_invalid_date_values(self):
        """無効な日付値"""
        result = _convert_gengo_to_date("昭和", 50, 2, 30)  # 2月30日は存在しない
        assert result is None


class TestSessionState:
    """セッション状態管理のテスト"""

    def test_init_session_state(self):
        """init_session_state関数のテスト"""
        mock_session_state = MagicMock()
        mock_session_state.__contains__ = lambda self, key: False

        with patch('lib.utils.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.utils import init_session_state
            init_session_state()

            # 各属性が設定されたことを確認
            assert mock_session_state.step == 'input'

    def test_reset_session_state(self):
        """reset_session_state関数のテスト"""
        mock_session_state = MagicMock()

        with patch('lib.utils.st') as mock_st:
            mock_st.session_state = mock_session_state

            from lib.utils import reset_session_state
            reset_session_state()

            # リセットされたことを確認
            assert mock_session_state.step == 'input'
            assert mock_session_state.extracted_data is None
            assert mock_session_state.edited_data is None
