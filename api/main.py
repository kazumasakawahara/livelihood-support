"""
生活保護受給者尊厳支援システム - REST API
TECHNICAL_STANDARDS.md 6.1 API設計基準準拠

FastAPIアプリケーションのエントリーポイント
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import recipients_router, records_router
from api.schemas import APIResponse, Meta, ErrorDetail
from lib.db_connection import get_driver


# =============================================================================
# アプリケーション設定
# =============================================================================

DEBUG = os.getenv("DEBUG", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル管理"""
    # 起動時処理
    print("🚀 API Server starting...")
    yield
    # 終了時処理
    print("🛑 API Server shutting down...")


# =============================================================================
# FastAPIアプリケーション
# =============================================================================

app = FastAPI(
    title="生活保護受給者尊厳支援API",
    description="""
## 概要

生活保護受給者の尊厳を守るための支援情報管理API。

### 主な機能

- **受給者管理**: 受給者一覧、プロフィール、統計情報
- **ケース記録**: 記録の作成、連携履歴の取得
- **引き継ぎ支援**: 担当者交代時のサマリー生成
- **パターンマッチング**: 類似ケース検索、成功パターン提案

### 認証

Keycloak OIDC認証を使用。Authorizationヘッダーに Bearer トークンを設定してください。

### ロール

- `caseworker`: 担当ケースの読み書き
- `supervisor`: チーム全体の閲覧、監査ログ
- `admin`: 全権限
- `auditor`: 監査ログ閲覧のみ
    """,
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    lifespan=lifespan,
)


# =============================================================================
# ミドルウェア
# =============================================================================

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8501").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


# =============================================================================
# エラーハンドリング
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """バリデーションエラーのハンドリング"""
    errors = []
    for error in exc.errors():
        errors.append(
            ErrorDetail(
                code="VALIDATION_ERROR",
                message=error.get("msg", "入力値が不正です"),
                field=".".join(str(loc) for loc in error.get("loc", [])),
                detail=str(error.get("ctx", "")),
            )
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(
            errors=errors,
            meta=Meta(timestamp=datetime.now()),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般エラーのハンドリング"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse(
            errors=[
                ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="サーバーエラーが発生しました",
                    detail=str(exc) if DEBUG else None,
                )
            ],
            meta=Meta(timestamp=datetime.now()),
        ).model_dump(mode="json"),
    )


# =============================================================================
# ルーター登録
# =============================================================================

API_PREFIX = "/api/v1"

app.include_router(recipients_router, prefix=API_PREFIX)
app.include_router(records_router, prefix=API_PREFIX)


# =============================================================================
# Prometheusメトリクス
# =============================================================================

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/health/ready", "/health/live", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

instrumentator.instrument(app).expose(app, include_in_schema=False)


# =============================================================================
# ヘルスチェック
# =============================================================================

def check_neo4j_connection() -> dict[str, Any]:
    """Neo4jデータベース接続確認"""
    try:
        driver = get_driver()
        if driver is None:
            return {"status": "unhealthy", "error": "Driver not initialized"}

        start_time = time.time()
        with driver.session() as session:
            result = session.run("RETURN 1 AS ping")
            result.single()
        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get(
    "/health",
    tags=["システム"],
    summary="ヘルスチェック（簡易版）",
    response_model=dict,
)
async def health_check():
    """
    APIサーバーのヘルスチェック（簡易版）

    - サーバー稼働確認用
    - データベース接続は確認しない
    - Kubernetes liveness probeに使用
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }


@app.get(
    "/health/ready",
    tags=["システム"],
    summary="レディネスチェック",
    response_model=dict,
)
async def readiness_check(response: Response):
    """
    APIサーバーのレディネスチェック

    - 全依存サービスの接続確認
    - Kubernetes readiness probeに使用
    - Neo4j接続確認を含む
    """
    neo4j_status = check_neo4j_connection()

    is_ready = neo4j_status["status"] == "healthy"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "checks": {
            "neo4j": neo4j_status,
        },
    }


@app.get(
    "/health/live",
    tags=["システム"],
    summary="ライブネスチェック",
    response_model=dict,
)
async def liveness_check():
    """
    APIサーバーのライブネスチェック

    - プロセス生存確認用
    - Kubernetes liveness probeに使用
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
    }


@app.get(
    "/",
    tags=["システム"],
    summary="APIルート",
    include_in_schema=False,
)
async def root():
    """APIルート"""
    return {
        "message": "生活保護受給者尊厳支援API",
        "version": "1.0.0",
        "docs": "/docs" if DEBUG else "本番環境では無効",
    }


# =============================================================================
# 開発用エントリーポイント
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
    )
