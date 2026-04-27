"""API routes for the FRBSF Chart Builder.

All endpoints are mounted under the ``/api`` prefix by the FastAPI application.
"""

from __future__ import annotations

from typing import Any

import math

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


def _sanitize_nan(obj):
    """Recursively replace float NaN/Inf with None for JSON compliance."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nan(v) for v in obj]
    return obj

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
async def ingest_from_url(
    url: str = Form(...),
    reference_image: UploadFile | None = File(None),
):
    """Accept a FRED URL with optional reference image and return chart config.

    Accepts multipart form data with ``url`` (required) and
    ``reference_image`` (optional PNG/JPEG).
    """
    result = await _ingestion_service.ingest_from_url(url, reference_image)
    return _sanitize_nan(result.model_dump())


@router.post("/ingest/upload")
async def ingest_from_upload(
    file: UploadFile = File(...),
    reference_image: UploadFile | None = File(None),
):
    """Accept a multipart file upload with optional reference image."""
    result = await _ingestion_service.ingest_from_file(file, reference_image)
    return _sanitize_nan(result.model_dump())


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
# Direct export endpoints (no saved project required)
# ---------------------------------------------------------------------------


@router.post("/export/python")
async def export_python_direct(payload: dict):
    """Export chart as a Python matplotlib zip archive from chart_state directly."""
    chart_state = ChartState(**payload["chart_state"])
    data = await _export_service.export_python(chart_state)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="chart_python.zip"'},
    )


@router.post("/export/r")
async def export_r_direct(payload: dict):
    """Export chart as an R ggplot2 zip archive from chart_state directly."""
    chart_state = ChartState(**payload["chart_state"])
    data = await _export_service.export_r(chart_state)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="chart_r.zip"'},
    )


@router.post("/export/pdf")
async def export_pdf_direct(
    request: Request,
    canvas_image: UploadFile | None = File(None),
    summary: str | None = Form(None),
):
    """Export chart as a PDF document.

    Accepts either:
    - Multipart form data with ``canvas_image`` (PNG) and ``summary`` text
    - JSON body with ``chart_state`` and ``summary``
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type and canvas_image is not None:
        image_bytes = await canvas_image.read()
        summary_text = summary or "No summary available."
        data = await _export_service.export_pdf_from_image(image_bytes, summary_text)
    else:
        payload = await request.json()
        chart_state = ChartState(**payload["chart_state"])
        summary_text = payload.get("summary", "No summary available.")
        data = await _export_service.export_pdf(chart_state, summary_text)

    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="chart.pdf"'},
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


@router.post("/reanalyze")
async def reanalyze(
    reference_image: UploadFile = File(...),
    dataset_path: str = Form(...),
):
    """Re-analyze reference image and regenerate chart from existing dataset."""
    import os
    from backend.services.ingestion import (
        _detect_and_pivot_long_format,
        _build_chart_state_from_df,
        _apply_image_spec_to_chart_state,
    )

    if not dataset_path or not os.path.exists(dataset_path):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="DATASET_NOT_FOUND",
                message=f"Dataset file not found: {dataset_path}",
            ).model_dump(),
        )

    df = pd.read_csv(dataset_path)
    df = _detect_and_pivot_long_format(df)

    title = os.path.splitext(os.path.basename(dataset_path))[0]
    chart_state = _build_chart_state_from_df(df=df, dataset_path=dataset_path, title=title)

    image_bytes = await reference_image.read()
    spec, vision_result = await _ingestion_service._image_analyzer.analyze(image_bytes)
    chart_state = _apply_image_spec_to_chart_state(chart_state, spec, df, vision_result)

    dataset_rows = df.where(df.notna(), None).to_dict(orient="records")
    return _sanitize_nan({"chart_state": chart_state.model_dump(), "dataset_rows": dataset_rows})


@router.post("/dataset/rows")
async def get_dataset_rows(payload: dict):
    """Load dataset rows from a CSV file path.

    Expects JSON body: ``{"dataset_path": "data/file.csv"}``
    """
    import os
    from backend.services.ingestion import _detect_and_pivot_long_format
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
    df = _detect_and_pivot_long_format(df)
    rows = df.where(df.notna(), None).to_dict(orient="records")
    return {"rows": rows}
