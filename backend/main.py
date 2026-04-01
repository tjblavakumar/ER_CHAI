"""FastAPI application entry point for the FRBSF Chart Builder.

Loads configuration on startup, initializes all services, mounts the API
router, and serves static frontend files.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.middleware import error_handling_middleware
from backend.api.routes import init_routes, router
from backend.services.ai_assistant import AIAssistantHandler
from backend.services.config import ConfigError, load_config
from backend.services.export_service import ExportService
from backend.services.fred_client import FREDClient
from backend.services.image_analyzer import ImageAnalyzer
from backend.services.ingestion import DataIngestionService
from backend.services.project_store import ProjectStore
from backend.services.summary_generator import SummaryGenerator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load config and initialize services on startup."""
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        print(f"\n*** Configuration Error ***\n{exc}\n", file=sys.stderr)
        sys.exit(1)

    # Build shared Bedrock client
    bedrock_kwargs: dict = {"region_name": config.aws_region}
    if config.aws_access_key_id and config.aws_secret_access_key:
        bedrock_kwargs["aws_access_key_id"] = config.aws_access_key_id
        bedrock_kwargs["aws_secret_access_key"] = config.aws_secret_access_key
    bedrock_client = boto3.client("bedrock-runtime", **bedrock_kwargs)

    # Initialize services
    fred_client = FREDClient(api_key=config.fred_api_key)
    image_analyzer = ImageAnalyzer(
        bedrock_client=bedrock_client,
        vision_model_id=config.bedrock_vision_model_id,
    )
    ingestion_service = DataIngestionService(fred_client=fred_client)
    ai_assistant = AIAssistantHandler(
        bedrock_client=bedrock_client,
        model_id=config.bedrock_model_id,
    )
    summary_generator = SummaryGenerator(
        bedrock_client=bedrock_client,
        model_id=config.bedrock_model_id,
    )
    export_service = ExportService()
    project_store = ProjectStore()

    # Inject services into the router
    init_routes(
        ingestion_service=ingestion_service,
        ai_assistant=ai_assistant,
        summary_generator=summary_generator,
        export_service=export_service,
        project_store=project_store,
    )

    logger.info("FRBSF Chart Builder started successfully.")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="FRBSF Chart Builder",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handling middleware
    @app.middleware("http")
    async def _error_middleware(request, call_next):
        return await error_handling_middleware(request, call_next)

    # Mount API router
    app.include_router(router)

    # Serve static frontend files if the directory exists
    static_dir = Path("frontend/dist")
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
