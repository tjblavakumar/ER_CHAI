"""Structured error handling middleware for the FRBSF Chart Builder API.

Maps backend exceptions to ErrorResponse JSON with appropriate HTTP status codes
per the design error handling table.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.models.schemas import ErrorResponse
from backend.services.config import ConfigError
from backend.services.fred_client import FREDAuthError, FREDNotFoundError

logger = logging.getLogger(__name__)


async def error_handling_middleware(request: Request, call_next):
    """Catch exceptions and return structured ErrorResponse JSON."""
    try:
        return await call_next(request)
    except Exception as exc:
        return _exception_to_response(exc)


def _exception_to_response(exc: Exception) -> JSONResponse:
    """Map a backend exception to an appropriate HTTP error response."""
    if isinstance(exc, ConfigError):
        msg = str(exc)
        if "not found" in msg.lower():
            body = ErrorResponse(
                error="CONFIG_FILE_NOT_FOUND",
                message=msg,
                details=None,
            )
            return JSONResponse(status_code=500, content=body.model_dump())
        body = ErrorResponse(
            error="CONFIG_INVALID",
            message=msg,
            details=None,
        )
        return JSONResponse(status_code=500, content=body.model_dump())

    if isinstance(exc, FREDAuthError):
        body = ErrorResponse(error="FRED_AUTH_ERROR", message=str(exc))
        return JSONResponse(status_code=401, content=body.model_dump())

    if isinstance(exc, FREDNotFoundError):
        body = ErrorResponse(
            error="FRED_SERIES_NOT_FOUND",
            message=str(exc),
        )
        return JSONResponse(status_code=404, content=body.model_dump())

    if isinstance(exc, ConnectionError):
        body = ErrorResponse(
            error="FRED_API_UNAVAILABLE",
            message=str(exc),
        )
        return JSONResponse(status_code=502, content=body.model_dump())

    if isinstance(exc, ValueError):
        msg = str(exc)
        msg_lower = msg.lower()
        if "unsupported file format" in msg_lower:
            body = ErrorResponse(
                error="UNSUPPORTED_FILE_FORMAT",
                message=msg,
                details={"accepted_formats": [".csv", ".xlsx", ".xls"]},
            )
            return JSONResponse(status_code=400, content=body.model_dump())
        if "invalid fred url" in msg_lower:
            body = ErrorResponse(
                error="INVALID_FRED_URL",
                message=msg,
            )
            return JSONResponse(status_code=400, content=body.model_dump())
        if "parse" in msg_lower or "malformed" in msg_lower:
            body = ErrorResponse(
                error="FILE_PARSE_ERROR",
                message=msg,
            )
            return JSONResponse(status_code=400, content=body.model_dump())
        if "unable to decode" in msg_lower or "image" in msg_lower:
            body = ErrorResponse(
                error="IMAGE_ANALYSIS_FAILED",
                message=msg,
            )
            return JSONResponse(status_code=422, content=body.model_dump())
        # Generic validation error
        body = ErrorResponse(
            error="INVALID_CHART_STATE",
            message=msg,
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    if isinstance(exc, ValidationError):
        body = ErrorResponse(
            error="INVALID_CHART_STATE",
            message="Validation error",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    if isinstance(exc, KeyError):
        body = ErrorResponse(
            error="PROJECT_NOT_FOUND",
            message=str(exc),
        )
        return JSONResponse(status_code=404, content=body.model_dump())

    if isinstance(exc, RuntimeError) and "bedrock" in str(exc).lower():
        body = ErrorResponse(
            error="BEDROCK_API_ERROR",
            message=str(exc),
        )
        return JSONResponse(status_code=502, content=body.model_dump())

    # Fallback
    logger.exception("Unhandled exception: %s", exc)
    body = ErrorResponse(
        error="INTERNAL_ERROR",
        message="An unexpected error occurred.",
    )
    return JSONResponse(status_code=500, content=body.model_dump())
