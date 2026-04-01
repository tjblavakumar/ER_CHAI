"""FRED API client for downloading economic data series."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse

import httpx

from backend.models.schemas import FREDDataset, Observation

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

FRED_URL_PATTERN = re.compile(
    r"^https?://fred\.stlouisfed\.org/series/([A-Za-z0-9_]+)(?:[/?#].*)?$"
)

FRED_API_BASE = "https://api.stlouisfed.org/fred/series"


class FREDAuthError(Exception):
    """Raised when the FRED API key is invalid or missing."""


class FREDNotFoundError(Exception):
    """Raised when the requested FRED series does not exist."""


# ---------------------------------------------------------------------------
# FRED Client
# ---------------------------------------------------------------------------


class FREDClient:
    """Async client for the FRED (Federal Reserve Economic Data) API."""

    MAX_RETRIES = 3
    BACKOFF_DELAYS = [1, 2, 4]  # seconds

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    # -- URL parsing --------------------------------------------------------

    @staticmethod
    def parse_fred_url(url: str) -> str:
        """Extract the series ID from a FRED URL.

        Accepts URLs like:
        - https://fred.stlouisfed.org/series/GDP
        - https://fred.stlouisfed.org/series/UNRATE?foo=bar

        Raises ``ValueError`` when the URL does not match the expected pattern.
        """
        match = FRED_URL_PATTERN.match(url.strip())
        if not match:
            raise ValueError(
                f"Invalid FRED URL: {url!r}. "
                "Expected format: https://fred.stlouisfed.org/series/<SERIES_ID>"
            )
        return match.group(1)

    # -- Series download ----------------------------------------------------

    async def download_series(self, series_id: str) -> FREDDataset:
        """Download a FRED series by ID and return a ``FREDDataset``.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s) on
        transient failures.  Raises:
        - ``FREDAuthError`` on invalid API key (HTTP 400 with bad api_key error).
        - ``FREDNotFoundError`` on non-existent series.
        """
        metadata = await self._request_with_retry(
            f"{FRED_API_BASE}",
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
            },
        )

        seriess = metadata.get("seriess", [])
        if not seriess:
            raise FREDNotFoundError(f"FRED series not found: {series_id}")

        series_meta = seriess[0]

        obs_data = await self._request_with_retry(
            f"{FRED_API_BASE}/observations",
            params={
                "series_id": series_id,
                "api_key": self._api_key,
                "file_type": "json",
            },
        )

        observations: list[Observation] = []
        for obs in obs_data.get("observations", []):
            value: float | None = None
            raw_value = obs.get("value", ".")
            if raw_value != ".":
                try:
                    value = float(raw_value)
                except (ValueError, TypeError):
                    value = None
            observations.append(Observation(date=obs["date"], value=value))

        return FREDDataset(
            series_id=series_meta.get("id", series_id),
            title=series_meta.get("title", ""),
            units=series_meta.get("units", ""),
            frequency=series_meta.get("frequency", ""),
            observations=observations,
        )

    # -- Internal helpers ---------------------------------------------------

    async def _request_with_retry(
        self, url: str, *, params: dict
    ) -> dict:
        """Make a GET request with retry logic.

        Retries up to ``MAX_RETRIES`` times with exponential backoff on
        transient errors (5xx, timeouts, connection errors).  Does NOT retry
        on 4xx client errors.
        """
        last_exc: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=params, timeout=30.0)

                # Auth error
                if resp.status_code in (400, 401, 403):
                    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    error_msg = body.get("error_message", resp.text)
                    if "api_key" in error_msg.lower() or "bad request" in error_msg.lower() or resp.status_code in (401, 403):
                        raise FREDAuthError(
                            f"FRED API authentication failed: {error_msg}"
                        )
                    raise FREDNotFoundError(
                        f"FRED API error ({resp.status_code}): {error_msg}"
                    )

                # Not found
                if resp.status_code == 404:
                    raise FREDNotFoundError(
                        f"FRED series not found (HTTP 404)"
                    )

                # Server error — retry
                if resp.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.BACKOFF_DELAYS[attempt])
                    continue

                resp.raise_for_status()
                return resp.json()

            except (FREDAuthError, FREDNotFoundError):
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.BACKOFF_DELAYS[attempt])

        raise ConnectionError(
            f"FRED API request failed after {self.MAX_RETRIES} retries: {last_exc}"
        )
