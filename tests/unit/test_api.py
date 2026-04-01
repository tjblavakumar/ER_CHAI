"""Unit tests for the FRBSF Chart Builder API routes, middleware, and app entry point."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.models.schemas import (
    AIResponse,
    ChartConfigDelta,
    ChartContext,
    ChartState,
    DatasetInfo,
    ErrorResponse,
    IngestionResult,
    Project,
    ProjectCreate,
    ProjectSummary,
    ProjectUpdate,
)


# ---------------------------------------------------------------------------
# Helpers — minimal valid chart state for tests
# ---------------------------------------------------------------------------

def _minimal_chart_state_dict() -> dict:
    return {
        "chart_type": "line",
        "title": {
            "text": "Test",
            "font_family": "Arial",
            "font_size": 14,
            "font_color": "#000000",
            "position": {"x": 0, "y": 0},
        },
        "axes": {"x_label": "X", "y_label": "Y"},
        "series": [
            {
                "name": "s1",
                "column": "value",
                "chart_type": "line",
                "color": "#003B5C",
                "line_width": 2.0,
                "visible": True,
            }
        ],
        "legend": {
            "visible": True,
            "position": {"x": 0, "y": 0},
            "entries": [],
        },
        "gridlines": {
            "horizontal_visible": True,
            "vertical_visible": False,
            "style": "dashed",
            "color": "#cccccc",
        },
        "annotations": [],
        "data_table": None,
        "elements_positions": {},
        "dataset_path": "data/test.csv",
        "dataset_columns": ["date", "value"],
    }


def _chart_state() -> ChartState:
    return ChartState(**_minimal_chart_state_dict())


def _chart_context_dict() -> dict:
    return {
        "chart_state": _minimal_chart_state_dict(),
        "dataset_summary": "2 columns, 10 rows",
        "dataset_sample": [{"date": "2020-01-01", "value": 1.0}],
    }


def _project(pid: str = "test-id") -> Project:
    return Project(
        id=pid,
        name="Test Project",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
        chart_state=_chart_state(),
        dataset_path="data/test.csv",
        summary_text="Test summary",
    )


# ---------------------------------------------------------------------------
# Fixture: test app with mocked services
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_services():
    return {
        "ingestion_service": AsyncMock(),
        "ai_assistant": MagicMock(),
        "summary_generator": AsyncMock(),
        "export_service": AsyncMock(),
        "project_store": AsyncMock(),
    }


@pytest.fixture
def test_app(mock_services):
    """Create a FastAPI test app with mocked services and no lifespan."""
    from fastapi import FastAPI
    from backend.api.middleware import error_handling_middleware
    from backend.api.routes import init_routes, router

    app = FastAPI()

    @app.middleware("http")
    async def _mw(request, call_next):
        return await error_handling_middleware(request, call_next)

    init_routes(**mock_services)
    app.include_router(router)
    return app


@pytest.fixture
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Ingestion endpoints
# ---------------------------------------------------------------------------


async def test_ingest_url(client, mock_services):
    mock_services["ingestion_service"].ingest_from_url.return_value = IngestionResult(
        dataset_path="data/gdp.csv",
        chart_state=_chart_state(),
        dataset_info=DatasetInfo(
            columns=["date", "value"], row_count=10, source="fred"
        ),
    )
    resp = await client.post(
        "/api/ingest/url",
        json={"url": "https://fred.stlouisfed.org/series/GDP"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dataset_path"] == "data/gdp.csv"
    assert data["chart_state"]["chart_type"] == "line"


async def test_ingest_url_invalid_returns_error(client, mock_services):
    mock_services["ingestion_service"].ingest_from_url.side_effect = ValueError(
        "Invalid FRED URL: 'bad'"
    )
    resp = await client.post("/api/ingest/url", json={"url": "bad"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "INVALID_FRED_URL"


async def test_ingest_upload(client, mock_services):
    mock_services["ingestion_service"].ingest_from_file.return_value = IngestionResult(
        dataset_path="data/upload.csv",
        chart_state=_chart_state(),
        dataset_info=DatasetInfo(
            columns=["date", "value"], row_count=5, source="upload"
        ),
    )
    resp = await client.post(
        "/api/ingest/upload",
        files={"file": ("test.csv", b"date,value\n2020-01-01,1.0", "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["dataset_path"] == "data/upload.csv"


async def test_ingest_upload_unsupported_format(client, mock_services):
    mock_services["ingestion_service"].ingest_from_file.side_effect = ValueError(
        "Unsupported file format: '.txt'. Accepted formats: .csv, .xlsx, .xls"
    )
    resp = await client.post(
        "/api/ingest/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "UNSUPPORTED_FILE_FORMAT"


# ---------------------------------------------------------------------------
# AI endpoints
# ---------------------------------------------------------------------------


async def test_ai_chat(client, mock_services):
    mock_services["ai_assistant"].handle_message = AsyncMock(
        return_value=AIResponse(
            type="data_qa", message="The GDP grew by 3%.", chart_delta=None
        )
    )
    resp = await client.post(
        "/api/ai/chat",
        json={
            "session_id": "s1",
            "message": "What is the trend?",
            "chart_context": _chart_context_dict(),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["type"] == "data_qa"
    assert "GDP" in resp.json()["message"]


async def test_ai_reset(client, mock_services):
    mock_services["ai_assistant"].reset_session = MagicMock()
    resp = await client.post("/api/ai/reset", json={"session_id": "s1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "session_reset"
    mock_services["ai_assistant"].reset_session.assert_called_once_with("s1")


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------


async def test_summary_generate(client, mock_services, tmp_path):
    # Write a small CSV for the endpoint to read
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("date,value\n2020-01-01,1.0\n2020-02-01,2.0\n")
    mock_services["summary_generator"].generate.return_value = "Summary text."

    resp = await client.post(
        "/api/summary/generate",
        json={
            "dataset_path": str(csv_path),
            "chart_context": _chart_context_dict(),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["summary"] == "Summary text."


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------


async def test_export_python(client, mock_services):
    mock_services["project_store"].get.return_value = _project("p1")
    mock_services["export_service"].export_python.return_value = b"PK\x03\x04fake"
    resp = await client.get("/api/export/python/p1")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


async def test_export_r(client, mock_services):
    mock_services["project_store"].get.return_value = _project("p1")
    mock_services["export_service"].export_r.return_value = b"PK\x03\x04fake"
    resp = await client.get("/api/export/r/p1")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


async def test_export_pdf(client, mock_services):
    mock_services["project_store"].get.return_value = _project("p1")
    mock_services["export_service"].export_pdf.return_value = b"%PDF-1.4 fake"
    resp = await client.get("/api/export/pdf/p1")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


async def test_export_project_not_found(client, mock_services):
    mock_services["project_store"].get.return_value = None
    resp = await client.get("/api/export/python/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["error"] == "PROJECT_NOT_FOUND"


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------


async def test_list_projects(client, mock_services):
    mock_services["project_store"].list_all.return_value = [
        ProjectSummary(id="p1", name="Proj 1", updated_at="2024-01-01T00:00:00"),
    ]
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["id"] == "p1"


async def test_create_project(client, mock_services):
    mock_services["project_store"].create.return_value = _project("new-id")
    resp = await client.post(
        "/api/projects",
        json={
            "name": "New Project",
            "chart_state": _minimal_chart_state_dict(),
            "dataset_path": "data/test.csv",
            "summary_text": "",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "new-id"


async def test_get_project(client, mock_services):
    mock_services["project_store"].get.return_value = _project("p1")
    resp = await client.get("/api/projects/p1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Project"


async def test_get_project_not_found(client, mock_services):
    mock_services["project_store"].get.return_value = None
    resp = await client.get("/api/projects/missing")
    assert resp.status_code == 404
    assert resp.json()["error"] == "PROJECT_NOT_FOUND"


async def test_update_project(client, mock_services):
    mock_services["project_store"].update.return_value = _project("p1")
    resp = await client.put(
        "/api/projects/p1",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200


async def test_delete_project(client, mock_services):
    mock_services["project_store"].delete.return_value = None
    resp = await client.delete("/api/projects/p1")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


# ---------------------------------------------------------------------------
# Error handling middleware
# ---------------------------------------------------------------------------


async def test_middleware_fred_auth_error(client, mock_services):
    from backend.services.fred_client import FREDAuthError
    mock_services["ingestion_service"].ingest_from_url.side_effect = FREDAuthError(
        "Invalid API key"
    )
    resp = await client.post("/api/ingest/url", json={"url": "https://fred.stlouisfed.org/series/GDP"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "FRED_AUTH_ERROR"


async def test_middleware_fred_not_found(client, mock_services):
    from backend.services.fred_client import FREDNotFoundError
    mock_services["ingestion_service"].ingest_from_url.side_effect = FREDNotFoundError(
        "Series not found"
    )
    resp = await client.post("/api/ingest/url", json={"url": "https://fred.stlouisfed.org/series/FAKE"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "FRED_SERIES_NOT_FOUND"


async def test_middleware_connection_error(client, mock_services):
    mock_services["ingestion_service"].ingest_from_url.side_effect = ConnectionError(
        "FRED API unreachable"
    )
    resp = await client.post("/api/ingest/url", json={"url": "https://fred.stlouisfed.org/series/GDP"})
    assert resp.status_code == 502
    assert resp.json()["error"] == "FRED_API_UNAVAILABLE"


async def test_middleware_bedrock_error(client, mock_services):
    mock_services["ai_assistant"].handle_message = AsyncMock(
        side_effect=RuntimeError("Bedrock API call failed after 3 attempts")
    )
    resp = await client.post(
        "/api/ai/chat",
        json={
            "session_id": "s1",
            "message": "hello",
            "chart_context": _chart_context_dict(),
        },
    )
    assert resp.status_code == 502
    assert resp.json()["error"] == "BEDROCK_API_ERROR"


async def test_middleware_project_update_not_found(client, mock_services):
    mock_services["project_store"].update.side_effect = KeyError("Project not found: missing")
    resp = await client.put("/api/projects/missing", json={"name": "X"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "PROJECT_NOT_FOUND"
