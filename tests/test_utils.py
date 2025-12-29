"""
lib/utils.py のユニットテスト
ユーティリティ関数のテスト（和暦変換、日付処理）
"""

import pytest
from datetime import date
from lib.utils import (
    convert_wareki_to_seireki,
    safe_date_parse,
    calculate_age,
    format_date_with_age,
    get_risk_emoji,
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
