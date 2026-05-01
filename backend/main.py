"""FastAPI application entry point for the FRBSF Chart Builder.

Loads configuration on startup, initializes all services, mounts the API
router, and serves static frontend files.
"""

from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
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
from backend.services.llm_client import create_llm_client
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

    # Create LLM clients for AI functionality
    llm_client = create_llm_client(config, use_vision=False)
    vision_llm_client = create_llm_client(config, use_vision=True)

    # Build Bedrock client only if needed (for ImageAnalyzer which still uses Bedrock)
    bedrock_client = None
    if config.llm_provider == "bedrock" or config.aws_region:
        bedrock_kwargs: dict = {"region_name": config.aws_region or "us-east-1"}
        if config.aws_access_key_id and config.aws_secret_access_key:
            bedrock_kwargs["aws_access_key_id"] = config.aws_access_key_id
            bedrock_kwargs["aws_secret_access_key"] = config.aws_secret_access_key
            if config.aws_session_token:
                bedrock_kwargs["aws_session_token"] = config.aws_session_token
        try:
            bedrock_client = boto3.client("bedrock-runtime", **bedrock_kwargs)
        except Exception as exc:
            logger.warning("Failed to create Bedrock client (not required for LiteLLM): %s", exc)
            bedrock_client = None

    # Initialize services
    fred_client = FREDClient(api_key=config.fred_api_key)
    
    # ImageAnalyzer - create only if Bedrock client is available
    # (ImageAnalyzer still requires Bedrock for vision analysis)
    if bedrock_client:
        image_analyzer = ImageAnalyzer(
            bedrock_client=bedrock_client,
            vision_model_id=config.bedrock_vision_model_id or "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        )
    else:
        logger.warning("ImageAnalyzer disabled - Bedrock client not available")
        image_analyzer = None
    ingestion_service = DataIngestionService(fred_client=fred_client, image_analyzer=image_analyzer)
    ai_assistant = AIAssistantHandler(llm_client=llm_client)
    summary_generator = SummaryGenerator(llm_client=llm_client)
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

    # LLM status — checked lazily via /api/bedrock/status endpoint
    app.state.bedrock_status = {"active": False, "model": config.bedrock_model_id or config.litellm_model_id, "error": "Not checked yet"}
    app.state.bedrock_client = bedrock_client
    app.state.bedrock_model_id = config.bedrock_model_id or config.litellm_model_id
    app.state.llm_provider = config.llm_provider

    logger.info("FRBSF Chart Builder started successfully.")
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="FRBSF Chart Builder",
        version="4.0.0",
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
