"""
API Routes for the IDP Application
"""

from app.routes.document_data import router as document_data_router
from app.routes.crud_ops import router as crud_ops_router
from app.routes.metrics import router as metrics_router
from app.routes.logs import router as logs_router
from app.routes.benchmark import router as benchmark_router
from app.routes.viewer import router as viewer_router

__all__ = [
    "document_data_router",
    "crud_ops_router",
    "metrics_router",
    "logs_router",
    "benchmark_router",
    "viewer_router",
]
