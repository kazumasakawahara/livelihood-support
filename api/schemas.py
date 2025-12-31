"""
Pydanticスキーマ定義
TECHNICAL_STANDARDS.md 4.3 入力値検証準拠
"""

from datetime import date as date_type, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


# =============================================================================
# 列挙型
# =============================================================================

class RiskLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ChallengeStatus(str, Enum):
    ACTIVE = "Active"
    IMPROVING = "Improving"
    RESOLVED = "Resolved"


class RecordCategory(str, Enum):
    VISIT = "訪問"
    PHONE = "電話"
    OFFICE = "来所"
    CONSULTATION = "相談"
    ACCOMPANIMENT = "同行"
    MEETING = "会議"
    OTHER = "その他"


# =============================================================================
# 共通レスポンス
# =============================================================================

class Meta(BaseModel):
    """レスポンスメタ情報"""
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    total_count: Optional[int] = None
    page: Optional[int] = None
    per_page: Optional[int] = None


class ErrorDetail(BaseModel):
    """エラー詳細"""
    code: str
    message: str
    field: Optional[str] = None
    detail: Optional[str] = None


class APIResponse(BaseModel):
    """標準APIレスポンス"""
    data: Optional[dict | list] = None
    meta: Meta = Field(default_factory=Meta)
    errors: Optional[list[ErrorDetail]] = None


# =============================================================================
# 受給者関連
# =============================================================================

class RecipientBase(BaseModel):
    """受給者基本情報"""
    name: str = Field(..., min_length=1, max_length=100, description="氏名")
    case_number: Optional[str] = Field(None, max_length=50, description="ケース番号")
    dob: Optional[date_type] = Field(None, description="生年月日")
    gender: Optional[str] = Field(None, max_length=10, description="性別")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """氏名のバリデーション"""
        v = v.strip()
        if not v:
            raise ValueError('氏名は必須です')
        # XSS対策
        dangerous_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('不正な文字列が含まれています')
        return v


class RecipientCreate(RecipientBase):
    """受給者作成リクエスト"""
    pass


class RecipientResponse(RecipientBase):
    """受給者レスポンス"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RecipientListResponse(BaseModel):
    """受給者一覧レスポンス"""
    data: list[str]
    meta: Meta = Field(default_factory=Meta)


# =============================================================================
# 避けるべき関わり方（NgApproach）
# =============================================================================

class NgApproachBase(BaseModel):
    """避けるべき関わり方"""
    description: str = Field(..., min_length=1, max_length=1000, description="内容")
    reason: Optional[str] = Field(None, max_length=1000, description="理由")
    risk_level: RiskLevel = Field(RiskLevel.MEDIUM, description="リスクレベル")
    consequence: Optional[str] = Field(None, max_length=1000, description="結果")


class NgApproachCreate(NgApproachBase):
    """避けるべき関わり方作成"""
    pass


class NgApproachResponse(NgApproachBase):
    """避けるべき関わり方レスポンス"""
    pass


# =============================================================================
# 効果的だった関わり方（EffectiveApproach）
# =============================================================================

class EffectiveApproachBase(BaseModel):
    """効果的だった関わり方"""
    description: str = Field(..., min_length=1, max_length=1000)
    context: Optional[str] = Field(None, max_length=500)


class EffectiveApproachCreate(EffectiveApproachBase):
    """効果的だった関わり方作成"""
    pass


class EffectiveApproachResponse(EffectiveApproachBase):
    """効果的だった関わり方レスポンス"""
    pass


# =============================================================================
# 精神疾患状況
# =============================================================================

class MentalHealthStatus(BaseModel):
    """精神疾患状況"""
    diagnosis: Optional[str] = Field(None, max_length=200, description="診断名")
    current_status: Optional[str] = Field(None, max_length=50, description="現在の状態")
    treatment_status: Optional[str] = Field(None, max_length=50, description="治療状況")
    symptoms: Optional[list[str]] = Field(None, description="症状リスト")


# =============================================================================
# ケース記録
# =============================================================================

class CaseRecordBase(BaseModel):
    """ケース記録基本情報"""
    date: date_type = Field(..., description="記録日")
    category: RecordCategory = Field(RecordCategory.OTHER, description="カテゴリ")
    content: str = Field(..., min_length=1, max_length=50000, description="記録内容")
    recipient_response: Optional[str] = Field(None, max_length=5000, description="本人の反応")
    caseworker: Optional[str] = Field(None, max_length=100, description="記録者")

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """記録内容のバリデーション（XSS対策）"""
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('不正な文字列が含まれています')
        return v


class CaseRecordCreate(CaseRecordBase):
    """ケース記録作成リクエスト"""
    recipient_name: str = Field(..., min_length=1, max_length=100, description="受給者名")


class CaseRecordResponse(CaseRecordBase):
    """ケース記録レスポンス"""
    pass


# =============================================================================
# 受給者プロフィール
# =============================================================================

class RecipientProfile(BaseModel):
    """受給者プロフィール（詳細情報）"""
    recipient_name: str
    ng_approaches: list[NgApproachResponse] = []
    effective_approaches: list[EffectiveApproachResponse] = []
    mental_health: Optional[MentalHealthStatus] = None
    strengths: list[dict] = []
    recent_records: list[CaseRecordResponse] = []
    support_organizations: list[dict] = []
    economic_risks: list[dict] = []
    money_status: Optional[dict] = None
    daily_life_support: Optional[dict] = None


# =============================================================================
# 統計情報
# =============================================================================

class RecipientStats(BaseModel):
    """受給者統計"""
    recipient_count: int = Field(0, description="受給者数")
    mental_health_count: int = Field(0, description="精神疾患登録数")
    economic_risk_count: int = Field(0, description="経済的リスク登録数")
    ng_by_recipient: list[dict] = Field(default_factory=list, description="受給者別NG件数")


# =============================================================================
# 引き継ぎ・検索
# =============================================================================

class HandoverSummary(BaseModel):
    """引き継ぎサマリー"""
    recipient_name: str
    summary: str


class SimilarCase(BaseModel):
    """類似ケース"""
    similar_case: str = Field(..., alias="類似ケース")
    common_risks: list[str] = Field(default_factory=list, alias="共通リスク")
    services: list[str] = Field(default_factory=list, alias="利用サービス")
    risk_status: Optional[str] = Field(None, alias="リスク状態")


class MatchingPattern(BaseModel):
    """マッチングパターン"""
    pattern_name: str = Field(..., alias="パターン名")
    description: str = Field("", alias="説明")
    recommended_interventions: list[str] = Field(default_factory=list, alias="推奨介入")
    related_services: list[str] = Field(default_factory=list, alias="関連サービス")
    success_count: int = Field(0, alias="成功件数")


# =============================================================================
# 訪問ブリーフィング
# =============================================================================

class VisitBriefing(BaseModel):
    """訪問前ブリーフィング"""
    recipient_name: str = Field(..., alias="受給者名")
    ng_approaches: list[dict] = Field(default_factory=list, alias="避けるべき関わり方")
    economic_risks: list[dict] = Field(default_factory=list, alias="経済的リスク")
    mental_health: Optional[str] = Field(None, alias="精神疾患")
    mental_health_status: Optional[str] = Field(None, alias="疾患の状態")
    money_capability: Optional[str] = Field(None, alias="金銭管理能力")
    money_pattern: Optional[str] = Field(None, alias="金銭管理パターン")
    support_services: list[str] = Field(default_factory=list, alias="自立支援サービス")
    effective_approaches: list[dict] = Field(default_factory=list, alias="効果的な関わり方")
