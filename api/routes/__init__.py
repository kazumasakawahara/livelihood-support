"""
APIルート定義
"""

from .recipients import router as recipients_router
from .records import router as records_router

__all__ = ["recipients_router", "records_router"]
