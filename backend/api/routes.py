"""API routes for the FRBSF Chart Builder.

All endpoints are mounted under the ``/api`` prefix by the FastAPI application.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from backend.models.schemas import (
    ChartContext,
    ChartState,
    ErrorResponse,
    ProjectCreate,
    ProjectUpdate,
)

router = APIRouter(prefix="/api")

# ---------------------------------------------------------------------------
# Service references — populated by ``init_routes`` at startup
# ---------------------------------------------------------------------------

_ingestion_service: Any = None
_ai_assistant: Any = None
_summary_generator: Any = None
_export_service: Any = None
_project_store: Any = None


def init_routes(
    *,
    ingestion_service,
    ai_assistant,
    summary_generator,
    export_service,
    project_store,
) -> None:
    """Inject service instances into the router module.

    Called once during application startup from ``main.py``.
    """
    global _ingestion_service, _ai_assistant, _summary_generator
    global _export_service, _project_store
    _ingestion_service = ingestion_service
    _ai_assistant = ai_assistant
    _summary_generator = summary_generator
    _export_service = export_service
    _project_store = project_store


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@router.get("/health")
async def health_check():
    """Return a simple health status."""
    return {"status": "ok"}


@router.get("/bedrock/status")
async def bedrock_status(request: Request):
    """Check and return Bedrock connection status. Runs the check on first call."""
    import asyncio as _aio
    import json as _json

    status = getattr(request.app.state, "bedrock_status", {})

    # If not checked yet, do it now
    if status.get("error") == "Not checked yet":
        try:
            client = request.app.state.bedrock_client
            model_id = request.app.state.bedrock_model_id
            test_body = _json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "hi"}],
            })
            resp = await _aio.to_thread(
                client.invoke_model,
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=test_body,
            )
            resp["body"].read()
            status["active"] = True
            status["error"] = ""
        except Exception as exc:
            status["active"] = False
            status["error"] = str(exc)
        request.app.state.bedrock_status = status

    return status


# ---------------------------------------------------------------------------
# Ingestion endpoints
# ---------------------------------------------------------------------------


@router.post("/ingest/url")
async def ingest_from_url(payload: dict):
    """Accept a FRED URL and return chart config.

    Expects JSON body: ``{"url": "https://fred.stlouisfed.org/series/GDP"}``
    """
    url = payload.get("url", "")
    result = await _ingestion_service.ingest_from_url(url)
    return result.model_dump()


@router.post("/ingest/upload")
async def ingest_from_upload(
    file: UploadFile = File(...),
    reference_image: UploadFile | None = File(None),
):
    """Accept a multipart file upload with optional reference image."""
    result = await _ingestion_service.ingest_from_file(file, reference_image)
    return result.model_dump()


# ---------------------------------------------------------------------------
# AI Assistant endpoints
# ---------------------------------------------------------------------------


@router.post("/ai/chat")
async def ai_chat(payload: dict):
    """Accept a chat message with chart context and return AI response.

    Expects JSON body::

        {
            "session_id": "...",
            "message": "...",
            "chart_context": { ... }
        }
    """
    session_id = payload.get("session_id", "default")
    message = payload.get("message", "")
    chart_context = ChartContext(**payload["chart_context"])
    response = await _ai_assistant.handle_message(session_id, message, chart_context)
    return response.model_dump()


@router.post("/ai/reset")
async def ai_reset(payload: dict):
    """Reset the AI session.

    Expects JSON body: ``{"session_id": "..."}``
    """
    session_id = payload.get("session_id", "default")
    _ai_assistant.reset_session(session_id)
    return {"status": "session_reset", "session_id": session_id}


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------


@router.post("/summary/generate")
async def generate_summary(payload: dict):
    """Generate an executive summary from dataset and chart context.

    Expects JSON body::

        {
            "dataset_path": "data/gdp.csv",
            "chart_context": { ... }
        }
    """
    dataset_path = payload["dataset_path"]
    chart_context = ChartContext(**payload["chart_context"])
    df = pd.read_csv(dataset_path)
    summary = await _summary_generator.generate(df, chart_context)
    return {"summary": summary}


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------


@router.get("/export/python/{project_id}")
async def export_python(project_id: str):
    """Export chart as a Python matplotlib zip archive."""
    project = await _project_store.get(project_id)
    if project is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="PROJECT_NOT_FOUND",
                message=f"Project not found: {project_id}",
            ).model_dump(),
        )
    data = await _export_service.export_python(project.chart_state)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="chart_python_{project_id}.zip"'},
    )


@router.get("/export/r/{project_id}")
async def export_r(project_id: str):
    """Export chart as an R ggplot2 zip archive."""
    project = await _project_store.get(project_id)
    if project is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="PROJECT_NOT_FOUND",
                message=f"Project not found: {project_id}",
            ).model_dump(),
        )
    data = await _export_service.export_r(project.chart_state)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="chart_r_{project_id}.zip"'},
    )


@router.get("/export/pdf/{project_id}")
async def export_pdf(project_id: str):
    """Export chart as a PDF document with summary."""
    project = await _project_store.get(project_id)
    if project is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="PROJECT_NOT_FOUND",
                message=f"Project not found: {project_id}",
            ).model_dump(),
        )
    summary = project.summary_text or "No summary available."
    data = await _export_service.export_pdf(project.chart_state, summary)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="chart_{project_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


@router.get("/projects")
async def list_projects():
    """List all projects."""
    projects = await _project_store.list_all()
    return [p.model_dump() for p in projects]


@router.post("/projects")
async def create_project(payload: ProjectCreate):
    """Create a new project."""
    project = await _project_store.create(payload)
    return project.model_dump()


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a project by ID."""
    project = await _project_store.get(project_id)
    if project is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="PROJECT_NOT_FOUND",
                message=f"Project not found: {project_id}",
            ).model_dump(),
        )
    return project.model_dump()


@router.put("/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate):
    """Update an existing project."""
    project = await _project_store.update(project_id, payload)
    return project.model_dump()


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    await _project_store.delete(project_id)
    return {"status": "deleted", "id": project_id}


@router.post("/dataset/rows")
async def get_dataset_rows(payload: dict):
    """Load dataset rows from a CSV file path.

    Expects JSON body: ``{"dataset_path": "data/file.csv"}``
    """
    import os
    dataset_path = payload.get("dataset_path", "")
    if not dataset_path or not os.path.exists(dataset_path):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="DATASET_NOT_FOUND",
                message=f"Dataset file not found: {dataset_path}",
            ).model_dump(),
        )
    df = pd.read_csv(dataset_path)
    rows = df.where(df.notna(), None).to_dict(orient="records")
    return {"rows": rows}
