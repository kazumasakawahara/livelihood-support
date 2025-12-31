"""
生活保護受給者尊厳支援データベース - 入力値検証モジュール
Manifesto: Livelihood Protection Support & Dignity Graph 準拠

セキュリティ基準: TECHNICAL_STANDARDS.md 4.3準拠
"""

import re
from datetime import datetime
from typing import Any


class ValidationError(Exception):
    """入力値検証エラー"""
    pass


def validate_string(
    value: Any,
    field_name: str,
    required: bool = False,
    max_length: int = 10000,
    allow_empty: bool = True
) -> str | None:
    """
    文字列の検証

    Args:
        value: 検証対象の値
        field_name: フィールド名（エラーメッセージ用）
        required: 必須フィールドかどうか
        max_length: 最大文字数
        allow_empty: 空文字を許可するか

    Returns:
        検証済み文字列、またはNone

    Raises:
        ValidationError: 検証失敗時
    """
    if value is None:
        if required:
            raise ValidationError(f"{field_name}は必須です")
        return None

    if not isinstance(value, str):
        value = str(value)

    if not allow_empty and value.strip() == "":
        if required:
            raise ValidationError(f"{field_name}は空にできません")
        return None

    if len(value) > max_length:
        raise ValidationError(f"{field_name}は{max_length}文字以内にしてください")

    return value


def validate_date_string(value: Any, field_name: str, required: bool = False) -> str | None:
    """
    日付文字列の検証（YYYY-MM-DD形式）

    Args:
        value: 検証対象の値
        field_name: フィールド名
        required: 必須フィールドかどうか

    Returns:
        検証済み日付文字列、またはNone

    Raises:
        ValidationError: 検証失敗時
    """
    if value is None:
        if required:
            raise ValidationError(f"{field_name}は必須です")
        return None

    if not isinstance(value, str):
        value = str(value)

    # YYYY-MM-DD形式のチェック
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, value):
        raise ValidationError(f"{field_name}はYYYY-MM-DD形式で入力してください")

    # 有効な日付かチェック
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise ValidationError(f"{field_name}は有効な日付ではありません")

    return value


def validate_enum(
    value: Any,
    field_name: str,
    allowed_values: list[str],
    required: bool = False
) -> str | None:
    """
    列挙型の検証

    Args:
        value: 検証対象の値
        field_name: フィールド名
        allowed_values: 許可される値のリスト
        required: 必須フィールドかどうか

    Returns:
        検証済み値、またはNone

    Raises:
        ValidationError: 検証失敗時
    """
    if value is None:
        if required:
            raise ValidationError(f"{field_name}は必須です")
        return None

    if value not in allowed_values:
        raise ValidationError(
            f"{field_name}は次の値のいずれかである必要があります: {', '.join(allowed_values)}"
        )

    return value


def sanitize_for_neo4j(value: str) -> str:
    """
    Neo4j用の入力サニタイズ（インジェクション対策）

    Note: パラメータ化クエリを使用しているため、主に二重チェック目的

    Args:
        value: サニタイズ対象の文字列

    Returns:
        サニタイズ済み文字列

    Raises:
        ValidationError: 危険なパターンを検出した場合
    """
    if not value:
        return value

    # 危険なパターンの検出
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # XSS
        r'on\w+\s*=',  # イベントハンドラ
        r'\x00',  # Null byte
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
            raise ValidationError("不正な文字列パターンが検出されました")

    return value


def validate_recipient_name(name: Any) -> str:
    """
    受給者名の検証（必須フィールド）

    Args:
        name: 受給者名

    Returns:
        検証済み受給者名

    Raises:
        ValidationError: 検証失敗時
    """
    validated = validate_string(name, "受給者名", required=True, max_length=100, allow_empty=False)
    return sanitize_for_neo4j(validated)
