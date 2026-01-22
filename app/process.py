"""
FastAPI Application - Main entry point for the IDP system
All endpoints are organized in separate router modules
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.helpers.benchmark import start_benchmarking
from app.helpers.logger import logger

# Import all routers
from app.routes import (
    document_data_router,
    crud_ops_router,
    metrics_router,
    logs_router,
    benchmark_router,
    viewer_router,
)

# Create FastAPI application
app = FastAPI(
    title="Intelligent Document Processing (IDP)",
    description="API for document classification and processing with AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Create required directories
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Register all routers
app.include_router(document_data_router)
app.include_router(crud_ops_router)
app.include_router(metrics_router)
app.include_router(logs_router)
app.include_router(benchmark_router)
app.include_router(viewer_router)

# Start benchmarking system
start_benchmarking()

logger.info("IDP Application initialized successfully")
