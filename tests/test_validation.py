"""
lib/validation.py のユニットテスト
入力値検証機能のテスト
"""

import pytest
from lib.validation import (
    ValidationError,
    validate_string,
    validate_date_string,
    validate_enum,
    sanitize_for_neo4j,
    validate_recipient_name,
)


class TestValidateString:
    """validate_string関数のテスト"""

    def test_valid_string(self):
        """正常な文字列の検証"""
        result = validate_string("テスト文字列", "フィールド名")
        assert result == "テスト文字列"

    def test_none_not_required(self):
        """Noneで必須でない場合"""
        result = validate_string(None, "フィールド名", required=False)
        assert result is None

    def test_none_required(self):
        """Noneで必須の場合はエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_string(None, "フィールド名", required=True)
        assert "フィールド名は必須です" in str(exc_info.value)

    def test_empty_string_not_allowed(self):
        """空文字列が許可されない場合"""
        result = validate_string("", "フィールド名", required=False, allow_empty=False)
        assert result is None

    def test_empty_string_required_not_allowed(self):
        """空文字列が必須で許可されない場合はエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_string("   ", "フィールド名", required=True, allow_empty=False)
        assert "空にできません" in str(exc_info.value)

    def test_max_length_exceeded(self):
        """最大文字数超過"""
        long_string = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            validate_string(long_string, "フィールド名", max_length=100)
        assert "100文字以内" in str(exc_info.value)

    def test_max_length_ok(self):
        """最大文字数以内"""
        string = "a" * 100
        result = validate_string(string, "フィールド名", max_length=100)
        assert len(result) == 100

    def test_non_string_converted(self):
        """非文字列は文字列に変換される"""
        result = validate_string(123, "フィールド名")
        assert result == "123"


class TestValidateDateString:
    """validate_date_string関数のテスト"""

    def test_valid_date(self):
        """正常な日付形式"""
        result = validate_date_string("2024-12-28", "日付")
        assert result == "2024-12-28"

    def test_none_not_required(self):
        """Noneで必須でない場合"""
        result = validate_date_string(None, "日付", required=False)
        assert result is None

    def test_none_required(self):
        """Noneで必須の場合はエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_string(None, "日付", required=True)
        assert "日付は必須です" in str(exc_info.value)

    def test_invalid_format(self):
        """不正な日付形式"""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_string("2024/12/28", "日付")
        assert "YYYY-MM-DD形式" in str(exc_info.value)

    def test_invalid_date(self):
        """存在しない日付"""
        with pytest.raises(ValidationError) as exc_info:
            validate_date_string("2024-02-30", "日付")
        assert "有効な日付ではありません" in str(exc_info.value)

    def test_leap_year(self):
        """うるう年の2月29日"""
        result = validate_date_string("2024-02-29", "日付")
        assert result == "2024-02-29"

    def test_non_leap_year(self):
        """非うるう年の2月29日はエラー"""
        with pytest.raises(ValidationError):
            validate_date_string("2023-02-29", "日付")


class TestValidateEnum:
    """validate_enum関数のテスト"""

    def test_valid_enum(self):
        """正常な列挙値"""
        result = validate_enum("High", "リスク", ["High", "Medium", "Low"])
        assert result == "High"

    def test_none_not_required(self):
        """Noneで必須でない場合"""
        result = validate_enum(None, "リスク", ["High", "Medium", "Low"])
        assert result is None

    def test_none_required(self):
        """Noneで必須の場合はエラー"""
        with pytest.raises(ValidationError) as exc_info:
            validate_enum(None, "リスク", ["High", "Medium", "Low"], required=True)
        assert "リスクは必須です" in str(exc_info.value)

    def test_invalid_enum(self):
        """許可されていない値"""
        with pytest.raises(ValidationError) as exc_info:
            validate_enum("Critical", "リスク", ["High", "Medium", "Low"])
        assert "High, Medium, Low" in str(exc_info.value)


class TestSanitizeForNeo4j:
    """sanitize_for_neo4j関数のテスト"""

    def test_normal_string(self):
        """通常の文字列はそのまま"""
        result = sanitize_for_neo4j("山田太郎さん")
        assert result == "山田太郎さん"

    def test_empty_string(self):
        """空文字列はそのまま"""
        result = sanitize_for_neo4j("")
        assert result == ""

    def test_none_value(self):
        """Noneはそのまま"""
        result = sanitize_for_neo4j(None)
        assert result is None

    def test_script_tag(self):
        """scriptタグは拒否"""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_for_neo4j("<script>alert('xss')</script>")
        assert "不正な文字列パターン" in str(exc_info.value)

    def test_javascript_protocol(self):
        """javascriptプロトコルは拒否"""
        with pytest.raises(ValidationError):
            sanitize_for_neo4j("javascript:alert(1)")

    def test_event_handler(self):
        """イベントハンドラは拒否"""
        with pytest.raises(ValidationError):
            sanitize_for_neo4j("onclick=alert(1)")

    def test_null_byte(self):
        """Nullバイトは拒否"""
        with pytest.raises(ValidationError):
            sanitize_for_neo4j("test\x00injection")


class TestValidateRecipientName:
    """validate_recipient_name関数のテスト"""

    def test_valid_name(self):
        """正常な受給者名"""
        result = validate_recipient_name("山田太郎")
        assert result == "山田太郎"

    def test_none_name(self):
        """Noneはエラー（必須フィールド）"""
        with pytest.raises(ValidationError):
            validate_recipient_name(None)

    def test_empty_name(self):
        """空文字列はエラー"""
        with pytest.raises(ValidationError):
            validate_recipient_name("")

    def test_whitespace_name(self):
        """空白のみはエラー"""
        with pytest.raises(ValidationError):
            validate_recipient_name("   ")

    def test_long_name(self):
        """長すぎる名前はエラー"""
        long_name = "あ" * 101
        with pytest.raises(ValidationError):
            validate_recipient_name(long_name)

    def test_xss_in_name(self):
        """XSS攻撃を含む名前は拒否"""
        with pytest.raises(ValidationError):
            validate_recipient_name("<script>alert('xss')</script>")
