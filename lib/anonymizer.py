"""
生活保護受給者尊厳支援データベース - 匿名化エンジン
TECHNICAL_STANDARDS.md Section 8 準拠

外部AIサービス利用時のPII（個人識別情報）保護機能を提供
- 直接識別子の検出・置換
- テキスト内PII検出
- 再識別（復元）機能
- 匿名化精度検証

セキュリティレベル: 要配慮個人情報対応
"""

import re
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class PIIType(Enum):
    """PII（個人識別情報）の種別"""
    NAME = "氏名"
    ADDRESS = "住所"
    PHONE = "電話番号"
    BIRTH_DATE = "生年月日"
    CASE_NUMBER = "ケース番号"
    BANK_ACCOUNT = "口座番号"
    MY_NUMBER = "マイナンバー"
    EMAIL = "メールアドレス"
    POSTAL_CODE = "郵便番号"
    FAMILY_NAME = "家族名"
    KEY_PERSON_NAME = "キーパーソン名"
    ORGANIZATION_CONTACT = "機関連絡先"
    DOCTOR_NAME = "医師名"
    CASEWORKER_NAME = "担当者名"


@dataclass
class PIIMatch:
    """検出されたPIIの情報"""
    pii_type: PIIType
    original: str
    placeholder: str
    start: int
    end: int
    confidence: float = 1.0  # 検出の確信度 (0.0-1.0)


@dataclass
class AnonymizationResult:
    """匿名化処理の結果"""
    anonymized_text: str
    pii_mappings: list[PIIMatch] = field(default_factory=list)
    session_id: str = ""
    timestamp: str = ""
    stats: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.session_id:
            self.session_id = secrets.token_hex(8)
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.stats:
            self.stats = self._compute_stats()

    def _compute_stats(self) -> dict:
        """統計情報を計算"""
        type_counts = {}
        for mapping in self.pii_mappings:
            type_name = mapping.pii_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        return {
            "total_pii_count": len(self.pii_mappings),
            "pii_by_type": type_counts
        }


class Anonymizer:
    """
    データ匿名化サービス

    TECHNICAL_STANDARDS.md Section 8.1, 8.2 準拠

    Usage:
        anonymizer = Anonymizer()
        result = anonymizer.anonymize_text(text)
        # ... send result.anonymized_text to external AI ...
        restored = anonymizer.restore_text(ai_response, result.pii_mappings)
    """

    # PII検出用正規表現パターン
    # 注意: 日本語テキストでは\bが正しく動作しないため、代わりに(?<!\d)と(?!\d)を使用
    PII_PATTERNS = {
        PIIType.MY_NUMBER: [
            (r'(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)', 0.95),  # マイナンバー形式
        ],
        PIIType.PHONE: [
            # 携帯電話（優先度高）
            (r'(?<!\d)0[789]0[-\s]?\d{4}[-\s]?\d{4}(?!\d)', 0.95),
            # 固定電話（市外局番-市内局番-加入者番号）
            (r'(?<!\d)0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4}(?!\d)', 0.9),
        ],
        PIIType.POSTAL_CODE: [
            (r'(?<!\d)\d{3}[-ー]\d{4}(?!\d)', 0.95),  # 郵便番号
        ],
        PIIType.BANK_ACCOUNT: [
            (r'(?:普通|当座|貯蓄)?\s*口座[番号:：]?\s*\d{5,8}', 0.85),
            (r'(?<!\d)\d{7}(?!\d)(?=\s*[（(]?口座)', 0.7),  # 口座番号らしき7桁
        ],
        PIIType.EMAIL: [
            (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', 0.95),
        ],
        PIIType.BIRTH_DATE: [
            # 和暦生年月日
            (r'(?:昭和|平成|令和)[元\d]{1,2}年\d{1,2}月\d{1,2}日生?', 0.9),
            # 西暦生年月日
            (r'(?:19|20)\d{2}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2}日?生?', 0.85),
        ],
        PIIType.ADDRESS: [
            # 都道府県から始まる住所
            (r'(?:東京都|北海道|(?:京都|大阪)府|[^\s]{2,3}県)[^\s、。]{5,}', 0.8),
            # 〜丁目〜番〜号
            (r'[^\s]{2,}[0-9０-９一二三四五六七八九十]+丁目[0-9０-９一二三四五六七八九十\-ー]+番[0-9０-９一二三四五六七八九十\-ー]*号?', 0.85),
        ],
    }

    # 日本人名パターン（姓名の間にスペースあり/なし両対応）
    NAME_PATTERNS = [
        # カタカナ名（フルネーム）
        (r'[ァ-ヶー]{2,}[\s　]+[ァ-ヶー]{2,}', PIIType.NAME, 0.8),
        # 漢字名（2-4文字の姓 + 1-4文字の名）
        (r'(?<![ァ-ヶー\w])[一-龥々]{2,4}[\s　]+[一-龥々]{1,4}(?![ァ-ヶー\w])', PIIType.NAME, 0.75),
        # 「〇〇さん」「〇〇様」形式
        (r'[一-龥々ァ-ヶー]{2,6}(?:さん|様|氏|先生)', PIIType.NAME, 0.7),
    ]

    # 文脈ベースのPII検出パターン
    CONTEXTUAL_PATTERNS = [
        # 受給者名（「受給者名: 山田太郎」または「受給者: 山田太郎」形式）
        (r'(?:受給者|本人|対象者)(?:名)?\s*[:：]\s*[「『]?([一-龥々ァ-ヶー]{2,8})[」』]?', PIIType.NAME, 0.9),
        # 担当者・ケースワーカー（「担当CWの田中」形式も対応）
        (r'(?:担当者?|CW|ケースワーカー)(?:名)?\s*[:：の]\s*[「『]?([一-龥々ァ-ヶー]{2,6})[」』]?', PIIType.CASEWORKER_NAME, 0.85),
        # 主治医・医師（「佐藤医師」形式も対応）
        (r'(?:主治医|担当医|医師)(?:名)?\s*[:：の]\s*[「『]?([一-龥々ァ-ヶー]{2,6})[」』]?(?:先生|医師)?', PIIType.DOCTOR_NAME, 0.85),
        # 「〇〇医師」形式（姓+医師）
        (r'([一-龥々]{1,4})(?:医師|先生)(?:に|へ|から|が|は|を)', PIIType.DOCTOR_NAME, 0.8),
        # 家族名（「長男の田中一」形式）
        (r'(?:長男|長女|次男|次女|息子|娘|母|父|兄|弟|姉|妹|配偶者|夫|妻|祖父|祖母)[のは]\s*[「『]?([一-龥々ァ-ヶー]{2,6})[」』]?', PIIType.FAMILY_NAME, 0.8),
        # キーパーソン
        (r'(?:キーパーソン|緊急連絡先)\s*[名:：]\s*[「『]?([一-龥々ァ-ヶー]{2,8})[」』]?', PIIType.KEY_PERSON_NAME, 0.85),
        # ケース番号（「ケース番号A12345678」「R05-12345」「H30-98765」形式）
        (r'(?:ケース|世帯|受給者)\s*(?:番号)?\s*[番号:：]?\s*([A-Za-zRrHh]?\d{1,2}[-ー]?\d{4,10})', PIIType.CASE_NUMBER, 0.9),
    ]

    def __init__(self, placeholder_format: str = "[{type}_{id}]"):
        """
        匿名化エンジンの初期化

        Args:
            placeholder_format: プレースホルダーの形式
                {type}: PII種別
                {id}: 一意識別子
        """
        self.placeholder_format = placeholder_format
        self._placeholder_counter = {}

    def _generate_placeholder(self, pii_type: PIIType) -> str:
        """プレースホルダーを生成"""
        type_name = pii_type.name
        count = self._placeholder_counter.get(type_name, 0) + 1
        self._placeholder_counter[type_name] = count
        return self.placeholder_format.format(type=pii_type.value, id=count)

    def _reset_counter(self):
        """プレースホルダーカウンターをリセット"""
        self._placeholder_counter = {}

    def detect_pii(self, text: str) -> list[PIIMatch]:
        """
        テキスト内のPIIを検出

        Args:
            text: 検査対象のテキスト

        Returns:
            検出されたPIIのリスト（位置情報付き）
        """
        if not text:
            return []

        matches: list[PIIMatch] = []
        matched_ranges: set[tuple[int, int]] = set()

        def add_match(pii_type: PIIType, original: str, start: int, end: int, confidence: float):
            """重複を避けて一致を追加"""
            # 既存の範囲と重複チェック
            for existing_start, existing_end in matched_ranges:
                if start < existing_end and end > existing_start:
                    return  # 重複している場合はスキップ

            placeholder = self._generate_placeholder(pii_type)
            matches.append(PIIMatch(
                pii_type=pii_type,
                original=original,
                placeholder=placeholder,
                start=start,
                end=end,
                confidence=confidence
            ))
            matched_ranges.add((start, end))

        # 正規表現パターンでPII検出
        for pii_type, patterns in self.PII_PATTERNS.items():
            for pattern, confidence in patterns:
                for match in re.finditer(pattern, text):
                    add_match(pii_type, match.group(), match.start(), match.end(), confidence)

        # 名前パターンで検出
        for pattern, pii_type, confidence in self.NAME_PATTERNS:
            for match in re.finditer(pattern, text):
                add_match(pii_type, match.group(), match.start(), match.end(), confidence)

        # 文脈ベースのパターンで検出
        for pattern, pii_type, confidence in self.CONTEXTUAL_PATTERNS:
            for match in re.finditer(pattern, text):
                # グループ1がある場合はそれを使用（キャプチャされた部分）
                if match.lastindex and match.lastindex >= 1:
                    original = match.group(1)
                    # グループ1の位置を計算
                    group_start = match.start(1)
                    group_end = match.end(1)
                    add_match(pii_type, original, group_start, group_end, confidence)
                else:
                    add_match(pii_type, match.group(), match.start(), match.end(), confidence)

        # 位置でソート（逆順：後ろから置換するため）
        matches.sort(key=lambda m: m.start, reverse=True)

        return matches

    def anonymize_text(self, text: str) -> AnonymizationResult:
        """
        テキストを匿名化

        Args:
            text: 匿名化対象のテキスト

        Returns:
            匿名化結果（匿名化テキスト、マッピング情報含む）
        """
        if not text:
            return AnonymizationResult(anonymized_text="", pii_mappings=[])

        self._reset_counter()

        # PII検出
        matches = self.detect_pii(text)

        # 後ろから置換（位置ずれを防ぐ）
        anonymized = text
        for match in matches:
            anonymized = (
                anonymized[:match.start] +
                match.placeholder +
                anonymized[match.end:]
            )

        # 位置を正順に戻す
        matches.reverse()

        return AnonymizationResult(
            anonymized_text=anonymized,
            pii_mappings=matches
        )

    def anonymize_for_external_ai(self, data: dict) -> tuple[dict, AnonymizationResult]:
        """
        外部AI送信用にデータを匿名化（TECH-8.2準拠）

        Args:
            data: 匿名化対象のデータ（ケース記録など）

        Returns:
            (匿名化されたデータ, 匿名化結果)
        """
        anonymized_data = {}
        all_mappings: list[PIIMatch] = []

        # 直接識別子フィールドの除去/置換
        direct_identifier_fields = {
            "name": PIIType.NAME,
            "recipient_name": PIIType.NAME,
            "address": PIIType.ADDRESS,
            "phone": PIIType.PHONE,
            "birth_date": PIIType.BIRTH_DATE,
            "dob": PIIType.BIRTH_DATE,
            "case_number": PIIType.CASE_NUMBER,
            "caseNumber": PIIType.CASE_NUMBER,
            "my_number": PIIType.MY_NUMBER,
            "bank_account": PIIType.BANK_ACCOUNT,
            "email": PIIType.EMAIL,
            "caseworker": PIIType.CASEWORKER_NAME,
            "recorded_by": PIIType.CASEWORKER_NAME,
        }

        self._reset_counter()

        for key, value in data.items():
            if key in direct_identifier_fields:
                if value:
                    pii_type = direct_identifier_fields[key]
                    placeholder = self._generate_placeholder(pii_type)
                    all_mappings.append(PIIMatch(
                        pii_type=pii_type,
                        original=str(value),
                        placeholder=placeholder,
                        start=0,
                        end=len(str(value)),
                        confidence=1.0
                    ))
                    anonymized_data[key] = placeholder
                else:
                    anonymized_data[key] = value
            elif isinstance(value, str):
                # テキストフィールドはテキスト内PII検出
                result = self.anonymize_text(value)
                anonymized_data[key] = result.anonymized_text
                all_mappings.extend(result.pii_mappings)
            elif isinstance(value, dict):
                # ネストされた辞書は再帰処理
                nested_data, nested_result = self.anonymize_for_external_ai(value)
                anonymized_data[key] = nested_data
                all_mappings.extend(nested_result.pii_mappings)
            elif isinstance(value, list):
                # リストの各要素を処理
                anonymized_list = []
                for item in value:
                    if isinstance(item, dict):
                        nested_data, nested_result = self.anonymize_for_external_ai(item)
                        anonymized_list.append(nested_data)
                        all_mappings.extend(nested_result.pii_mappings)
                    elif isinstance(item, str):
                        result = self.anonymize_text(item)
                        anonymized_list.append(result.anonymized_text)
                        all_mappings.extend(result.pii_mappings)
                    else:
                        anonymized_list.append(item)
                anonymized_data[key] = anonymized_list
            else:
                anonymized_data[key] = value

        return anonymized_data, AnonymizationResult(
            anonymized_text="",  # 構造化データの場合は空
            pii_mappings=all_mappings
        )

    def restore_text(self, text: str, mappings: list[PIIMatch]) -> str:
        """
        匿名化テキストを復元（再識別）

        Args:
            text: 匿名化されたテキスト
            mappings: 匿名化時のマッピング情報

        Returns:
            復元されたテキスト
        """
        if not text or not mappings:
            return text

        restored = text
        for mapping in mappings:
            restored = restored.replace(mapping.placeholder, mapping.original)

        return restored

    def restore_data(self, data: dict, mappings: list[PIIMatch]) -> dict:
        """
        匿名化データを復元

        Args:
            data: 匿名化されたデータ
            mappings: 匿名化時のマッピング情報

        Returns:
            復元されたデータ
        """
        # マッピングを辞書に変換
        mapping_dict = {m.placeholder: m.original for m in mappings}

        def restore_value(value: Any) -> Any:
            if isinstance(value, str):
                result = value
                for placeholder, original in mapping_dict.items():
                    result = result.replace(placeholder, original)
                return result
            elif isinstance(value, dict):
                return {k: restore_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [restore_value(item) for item in value]
            else:
                return value

        return restore_value(data)


class AnonymizationAuditor:
    """
    匿名化精度の検証クラス

    TECHNICAL_STANDARDS.md Section 8 に基づく品質保証
    """

    # 検証用のテストパターン
    TEST_PATTERNS = [
        # 必ず検出すべきパターン
        ("山田太郎さんに電話した", [PIIType.NAME]),
        ("090-1234-5678に連絡", [PIIType.PHONE]),
        ("東京都新宿区西新宿1-2-3", [PIIType.ADDRESS]),
        ("ケース番号A12345678", [PIIType.CASE_NUMBER]),
    ]

    def __init__(self, anonymizer: Anonymizer):
        self.anonymizer = anonymizer

    def verify_anonymization(self, original: str, anonymized: str, mappings: list[PIIMatch]) -> dict:
        """
        匿名化結果を検証

        Args:
            original: 元のテキスト
            anonymized: 匿名化されたテキスト
            mappings: マッピング情報

        Returns:
            検証結果
        """
        issues = []

        # 1. 元のPIIが残っていないか確認
        for mapping in mappings:
            if mapping.original in anonymized:
                issues.append({
                    "type": "pii_leakage",
                    "pii_type": mapping.pii_type.value,
                    "description": f"PIIが匿名化されていません: {mapping.original[:10]}..."
                })

        # 2. 復元可能性の確認
        restored = self.anonymizer.restore_text(anonymized, mappings)
        if restored != original:
            issues.append({
                "type": "restoration_failure",
                "description": "復元結果が元のテキストと一致しません"
            })

        # 3. プレースホルダーが正しく挿入されているか
        for mapping in mappings:
            if mapping.placeholder not in anonymized:
                issues.append({
                    "type": "placeholder_missing",
                    "pii_type": mapping.pii_type.value,
                    "description": f"プレースホルダーが見つかりません: {mapping.placeholder}"
                })

        return {
            "is_valid": len(issues) == 0,
            "original_length": len(original),
            "anonymized_length": len(anonymized),
            "pii_count": len(mappings),
            "issues": issues
        }

    def run_test_suite(self) -> dict:
        """
        テストスイートを実行

        Returns:
            テスト結果サマリー
        """
        results = {
            "total_tests": len(self.TEST_PATTERNS),
            "passed": 0,
            "failed": 0,
            "failures": []
        }

        for text, expected_types in self.TEST_PATTERNS:
            result = self.anonymizer.anonymize_text(text)
            detected_types = {m.pii_type for m in result.pii_mappings}

            for expected_type in expected_types:
                if expected_type in detected_types:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["failures"].append({
                        "text": text,
                        "expected": expected_type.value,
                        "detected": [t.value for t in detected_types]
                    })

        results["accuracy"] = results["passed"] / results["total_tests"] if results["total_tests"] > 0 else 0
        return results


def create_anonymizer() -> Anonymizer:
    """
    デフォルト設定の匿名化エンジンを作成

    Returns:
        Anonymizer インスタンス
    """
    return Anonymizer()


def anonymize_case_record_for_ai(record: dict) -> tuple[dict, AnonymizationResult]:
    """
    ケース記録をAI処理用に匿名化

    Args:
        record: ケース記録データ

    Returns:
        (匿名化されたレコード, 匿名化結果)

    Usage:
        anonymized, result = anonymize_case_record_for_ai(record)
        ai_response = external_ai.process(anonymized)
        restored_response = anonymizer.restore_data(ai_response, result.pii_mappings)
    """
    anonymizer = create_anonymizer()
    return anonymizer.anonymize_for_external_ai(record)
