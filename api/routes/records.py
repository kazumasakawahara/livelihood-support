"""
ケース記録APIエンドポイント
/api/v1/records

TECHNICAL_STANDARDS.md 6.1 API設計基準準拠
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request

from api.schemas import (
    APIResponse,
    Meta,
    CaseRecordCreate,
    CaseRecordResponse,
)
from api.dependencies import (
    User,
    Permission,
    get_current_user,
    get_current_user_or_mock,
    require_permission,
    get_request_id,
)
from lib.db_queries import get_collaboration_history
from lib.db_operations import register_to_database
from lib.audit import create_audit_log


router = APIRouter(prefix="/records", tags=["ケース記録"])


# =============================================================================
# ケース記録作成
# =============================================================================

@router.post(
    "",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="ケース記録を作成",
    description="新しいケース記録を登録します。",
)
async def create_record(
    record: CaseRecordCreate,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    ケース記録を作成

    - caseworker以上のロールが必要
    - 受給者名は必須
    """
    request_id = get_request_id(request)

    try:
        # 登録用データを構築
        data = {
            "recipient": {"name": record.recipient_name},
            "caseRecords": [
                {
                    "date": record.date.isoformat(),
                    "category": record.category.value,
                    "content": record.content,
                    "recipientResponse": record.recipient_response or "",
                    "caseworker": record.caseworker or user.name,
                }
            ],
        }

        # データベースに登録
        result = register_to_database(data, user.username)

        # 監査ログ
        create_audit_log(
            action="CREATE",
            user=user.username,
            details={
                "recipient": record.recipient_name,
                "resource": "case_record",
                "date": record.date.isoformat(),
            },
        )

        return APIResponse(
            data={
                "message": "ケース記録を登録しました",
                "recipient_name": record.recipient_name,
                "warnings": result.get("warnings", []),
            },
            meta=Meta(request_id=request_id, timestamp=datetime.now()),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登録エラー: {str(e)}",
        )


# =============================================================================
# 連携履歴
# =============================================================================

@router.get(
    "/collaboration/{recipient_name}",
    response_model=APIResponse,
    summary="連携履歴を取得",
    description="指定した受給者の多機関連携履歴を取得します。",
)
async def get_collaboration(
    recipient_name: str,
    request: Request,
    limit: int = Query(10, ge=1, le=100, description="取得件数"),
    user: User = Depends(get_current_user_or_mock),
):
    """
    連携履歴を取得

    - ケース会議、電話連絡などの連携記録を取得
    """
    request_id = get_request_id(request)

    try:
        history = get_collaboration_history(recipient_name, limit=limit)

        # 監査ログ
        create_audit_log(
            action="READ",
            user=user.username,
            details={"recipient": recipient_name, "resource": "collaboration_history"},
        )

        return APIResponse(
            data=history,
            meta=Meta(
                request_id=request_id,
                timestamp=datetime.now(),
                total_count=len(history),
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"連携履歴取得エラー: {str(e)}",
        )


# =============================================================================
# 一括登録
# =============================================================================

@router.post(
    "/bulk",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
    summary="一括登録",
    description="受給者情報と関連データを一括で登録します。",
)
async def bulk_register(
    data: dict,
    request: Request,
    user: User = Depends(get_current_user_or_mock),
):
    """
    一括登録

    - 受給者情報、NG、効果的関わり方、精神疾患などを一括登録
    - Streamlitアプリと同等のフルデータ登録
    """
    request_id = get_request_id(request)

    # 受給者名の確認
    recipient_name = data.get("recipient", {}).get("name")
    if not recipient_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="受給者名は必須です",
        )

    try:
        result = register_to_database(data, user.username)

        # 監査ログ
        create_audit_log(
            action="CREATE",
            user=user.username,
            details={
                "recipient": recipient_name,
                "resource": "bulk_data",
                "ng_count": len(data.get("ngApproaches", [])),
                "record_count": len(data.get("caseRecords", [])),
            },
        )

        return APIResponse(
            data={
                "message": "データを登録しました",
                "recipient_name": recipient_name,
                "warnings": result.get("warnings", []),
            },
            meta=Meta(request_id=request_id, timestamp=datetime.now()),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登録エラー: {str(e)}",
        )
