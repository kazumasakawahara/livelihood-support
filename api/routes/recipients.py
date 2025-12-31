"""
受給者APIエンドポイント
/api/v1/recipients

TECHNICAL_STANDARDS.md 6.1 API設計基準準拠
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request

from api.schemas import (
    APIResponse,
    Meta,
    RecipientListResponse,
    RecipientProfile,
    RecipientStats,
    HandoverSummary,
    SimilarCase,
    MatchingPattern,
    VisitBriefing,
)
from api.dependencies import (
    User,
    Permission,
    get_current_user,
    get_current_user_or_mock,
    require_permission,
    require_any_role,
    get_request_id,
)
from lib.db_queries import (
    get_recipients_list,
    get_recipient_stats,
    get_recipient_profile,
    get_handover_summary,
    search_similar_cases,
    find_matching_patterns,
    get_visit_briefing,
)
from lib.audit import create_audit_log


router = APIRouter(prefix="/recipients", tags=["受給者"])


# =============================================================================
# 受給者一覧
# =============================================================================

@router.get(
    "",
    response_model=RecipientListResponse,
    summary="受給者一覧を取得",
    description="登録されている受給者の名前一覧を取得します。",
)
async def list_recipients(
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    受給者一覧を取得

    - caseworker以上のロールが必要
    """
    request_id = get_request_id(request)

    try:
        recipients = get_recipients_list()

        # 監査ログ
        create_audit_log(
            action="LIST",
            user=user.username,
            details={"count": len(recipients)},
        )

        return RecipientListResponse(
            data=recipients,
            meta=Meta(
                request_id=request_id,
                timestamp=datetime.now(),
                total_count=len(recipients),
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"データ取得エラー: {str(e)}",
        )


# =============================================================================
# 統計情報
# =============================================================================

@router.get(
    "/stats",
    response_model=APIResponse,
    summary="受給者統計を取得",
    description="受給者数、精神疾患登録数などの統計情報を取得します。",
)
async def get_stats(
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    受給者統計を取得

    - caseworker以上のロールが必要
    """
    request_id = get_request_id(request)

    try:
        stats = get_recipient_stats()

        return APIResponse(
            data=stats,
            meta=Meta(
                request_id=request_id,
                timestamp=datetime.now(),
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"統計取得エラー: {str(e)}",
        )


# =============================================================================
# 受給者プロフィール
# =============================================================================

@router.get(
    "/{recipient_name}/profile",
    response_model=APIResponse,
    summary="受給者プロフィールを取得",
    description="指定した受給者の詳細プロフィール（NG、効果的関わり方、精神疾患等）を取得します。",
)
async def get_profile(
    recipient_name: str,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    受給者プロフィールを取得

    - 担当ケースまたはsupervisor以上の権限が必要
    """
    request_id = get_request_id(request)

    try:
        profile = get_recipient_profile(recipient_name)

        if not profile or not profile.get("recipient_name"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"受給者が見つかりません: {recipient_name}",
            )

        # 監査ログ
        create_audit_log(
            action="READ",
            user=user.username,
            details={"recipient": recipient_name, "resource": "profile"},
        )

        return APIResponse(
            data=profile,
            meta=Meta(request_id=request_id, timestamp=datetime.now()),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"プロフィール取得エラー: {str(e)}",
        )


# =============================================================================
# 引き継ぎサマリー
# =============================================================================

@router.get(
    "/{recipient_name}/handover",
    response_model=APIResponse,
    summary="引き継ぎサマリーを取得",
    description="担当者交代時の引き継ぎ用サマリーを生成します。",
)
async def get_handover(
    recipient_name: str,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    引き継ぎサマリーを取得

    - 避けるべき関わり方、効果的な関わり方、精神疾患情報を含む
    """
    request_id = get_request_id(request)

    try:
        summary = get_handover_summary(recipient_name)

        # 監査ログ
        create_audit_log(
            action="READ",
            user=user.username,
            details={"recipient": recipient_name, "resource": "handover"},
        )

        return APIResponse(
            data={"recipient_name": recipient_name, "summary": summary},
            meta=Meta(request_id=request_id, timestamp=datetime.now()),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サマリー生成エラー: {str(e)}",
        )


# =============================================================================
# 訪問前ブリーフィング
# =============================================================================

@router.get(
    "/{recipient_name}/briefing",
    response_model=APIResponse,
    summary="訪問前ブリーフィングを取得",
    description="訪問前に確認すべき重要情報（NG、リスク、効果的関わり方）を取得します。",
)
async def get_briefing(
    recipient_name: str,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    訪問前ブリーフィングを取得

    - 訪問前に確認すべき重要情報を取得
    """
    request_id = get_request_id(request)

    try:
        briefing = get_visit_briefing(recipient_name)

        if not briefing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"受給者が見つかりません: {recipient_name}",
            )

        # 監査ログ
        create_audit_log(
            action="READ",
            user=user.username,
            details={"recipient": recipient_name, "resource": "briefing"},
        )

        return APIResponse(
            data=briefing,
            meta=Meta(request_id=request_id, timestamp=datetime.now()),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ブリーフィング取得エラー: {str(e)}",
        )


# =============================================================================
# 類似ケース検索
# =============================================================================

@router.get(
    "/{recipient_name}/similar",
    response_model=APIResponse,
    summary="類似ケースを検索",
    description="同様のリスクパターンを持つケースを検索します。",
)
async def search_similar(
    recipient_name: str,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    類似ケースを検索

    - 同様の経済的リスクを持つケースを検索
    """
    request_id = get_request_id(request)

    try:
        similar_cases = search_similar_cases(recipient_name)

        # 監査ログ
        create_audit_log(
            action="SEARCH",
            user=user.username,
            details={"recipient": recipient_name, "resource": "similar_cases"},
        )

        return APIResponse(
            data=similar_cases,
            meta=Meta(
                request_id=request_id,
                timestamp=datetime.now(),
                total_count=len(similar_cases),
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"類似ケース検索エラー: {str(e)}",
        )


# =============================================================================
# パターンマッチング
# =============================================================================

@router.get(
    "/{recipient_name}/patterns",
    response_model=APIResponse,
    summary="マッチングパターンを検索",
    description="過去の成功パターンとのマッチングを検索します。",
)
async def find_patterns(
    recipient_name: str,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    マッチングパターンを検索

    - 経済的リスクと日常生活自立支援事業のパターンをマッチング
    """
    request_id = get_request_id(request)

    try:
        patterns = find_matching_patterns(recipient_name)

        return APIResponse(
            data=patterns,
            meta=Meta(
                request_id=request_id,
                timestamp=datetime.now(),
                total_count=len(patterns),
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"パターン検索エラー: {str(e)}",
        )
