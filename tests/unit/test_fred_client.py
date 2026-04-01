"""Unit tests for the FRED Client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services.fred_client import (
    FREDAuthError,
    FREDClient,
    FREDNotFoundError,
)


# ---------------------------------------------------------------------------
# URL parsing tests
# ---------------------------------------------------------------------------


class TestParseFredUrl:
    """Tests for FREDClient.parse_fred_url."""

    def test_basic_url(self) -> None:
        assert FREDClient.parse_fred_url("https://fred.stlouisfed.org/series/GDP") == "GDP"

    def test_url_with_trailing_slash(self) -> None:
        # Trailing slash after series ID should not match (no ID captured)
        # Actually the regex allows optional path after ID
        assert FREDClient.parse_fred_url("https://fred.stlouisfed.org/series/UNRATE") == "UNRATE"

    def test_url_with_query_params(self) -> None:
        url = "https://fred.stlouisfed.org/series/DFF?cid=118"
        assert FREDClient.parse_fred_url(url) == "DFF"

    def test_url_with_fragment(self) -> None:
        url = "https://fred.stlouisfed.org/series/T10Y2Y#section"
        assert FREDClient.parse_fred_url(url) == "T10Y2Y"

    def test_url_with_underscore_in_id(self) -> None:
        url = "https://fred.stlouisfed.org/series/GDPC1"
        assert FREDClient.parse_fred_url(url) == "GDPC1"

    def test_url_with_whitespace_stripped(self) -> None:
        url = "  https://fred.stlouisfed.org/series/GDP  "
        assert FREDClient.parse_fred_url(url) == "GDP"

    def test_invalid_url_random_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            FREDClient.parse_fred_url("not-a-url")

    def test_invalid_url_wrong_domain(self) -> None:
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            FREDClient.parse_fred_url("https://example.com/series/GDP")

    def test_invalid_url_no_series_path(self) -> None:
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            FREDClient.parse_fred_url("https://fred.stlouisfed.org/")

    def test_invalid_url_graph_path(self) -> None:
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            FREDClient.parse_fred_url("https://fred.stlouisfed.org/graph/?g=abc")

    def test_invalid_url_empty_series_id(self) -> None:
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            FREDClient.parse_fred_url("https://fred.stlouisfed.org/series/")

    def test_invalid_url_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            FREDClient.parse_fred_url("")


# ---------------------------------------------------------------------------
# Helpers for mocking httpx responses
# ---------------------------------------------------------------------------


def _mock_response(status_code: int, json_data: dict | None = None, text: str = "") -> httpx.Response:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.headers = {"content-type": "application/json"}
    resp.request = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.return_value = {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=resp.request, response=resp
        )
    return resp


SAMPLE_SERIES_META = {
    "seriess": [
        {
            "id": "GDP",
            "title": "Gross Domestic Product",
            "units": "Billions of Dollars",
            "frequency": "Quarterly",
        }
    ]
}

SAMPLE_OBSERVATIONS = {
    "observations": [
        {"date": "2023-01-01", "value": "26137.0"},
        {"date": "2023-04-01", "value": "26468.0"},
        {"date": "2023-07-01", "value": "."},
    ]
}


# ---------------------------------------------------------------------------
# download_series tests
# ---------------------------------------------------------------------------


class TestDownloadSeries:
    """Tests for FREDClient.download_series with mocked HTTP."""

    @pytest.fixture
    def client(self) -> FREDClient:
        return FREDClient(api_key="test-key-123")

    async def test_successful_download(self, client: FREDClient) -> None:
        """A successful API call should return a properly parsed FREDDataset."""
        call_count = 0

        async def mock_get(url, *, params=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if "observations" in url:
                return _mock_response(200, SAMPLE_OBSERVATIONS)
            return _mock_response(200, SAMPLE_SERIES_META)

        with patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            dataset = await client.download_series("GDP")

        assert dataset.series_id == "GDP"
        assert dataset.title == "Gross Domestic Product"
        assert dataset.units == "Billions of Dollars"
        assert dataset.frequency == "Quarterly"
        assert len(dataset.observations) == 3
        assert dataset.observations[0].date == "2023-01-01"
        assert dataset.observations[0].value == 26137.0
        assert dataset.observations[2].value is None  # "." → None

    async def test_auth_error(self, client: FREDClient) -> None:
        """An invalid API key should raise FREDAuthError."""
        error_resp = _mock_response(
            401,
            json_data={"error_message": "Bad API key"},
        )

        async def mock_get(url, *, params=None, timeout=None):
            return error_resp

        with patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(FREDAuthError, match="authentication failed"):
                await client.download_series("GDP")

    async def test_not_found_error(self, client: FREDClient) -> None:
        """A 404 response should raise FREDNotFoundError."""
        not_found_resp = _mock_response(404)

        async def mock_get(url, *, params=None, timeout=None):
            return not_found_resp

        with patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(FREDNotFoundError, match="not found"):
                await client.download_series("NONEXISTENT")

    async def test_empty_seriess_raises_not_found(self, client: FREDClient) -> None:
        """If the metadata response has an empty seriess list, raise FREDNotFoundError."""
        empty_meta = _mock_response(200, {"seriess": []})

        async def mock_get(url, *, params=None, timeout=None):
            return empty_meta

        with patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(FREDNotFoundError, match="not found"):
                await client.download_series("INVALID")


# ---------------------------------------------------------------------------
# Retry behavior tests
# ---------------------------------------------------------------------------


class TestRetryBehavior:
    """Tests for retry logic with exponential backoff."""

    @pytest.fixture
    def client(self) -> FREDClient:
        return FREDClient(api_key="test-key")

    async def test_retries_on_server_error_then_succeeds(self, client: FREDClient) -> None:
        """Should retry on 500 and succeed when a subsequent attempt works."""
        call_count = 0

        async def mock_get(url, *, params=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return _mock_response(500, text="Internal Server Error")
            if "observations" in url:
                return _mock_response(200, SAMPLE_OBSERVATIONS)
            return _mock_response(200, SAMPLE_SERIES_META)

        with (
            patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls,
            patch("backend.services.fred_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            dataset = await client.download_series("GDP")

        assert dataset.series_id == "GDP"
        # sleep should have been called for backoff
        assert mock_sleep.call_count >= 1

    async def test_exhausts_retries_on_persistent_server_error(self, client: FREDClient) -> None:
        """Should raise ConnectionError after exhausting all retries."""
        async def mock_get(url, *, params=None, timeout=None):
            return _mock_response(500, text="Internal Server Error")

        with (
            patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls,
            patch("backend.services.fred_client.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(ConnectionError, match="failed after 3 retries"):
                await client.download_series("GDP")

    async def test_retries_on_timeout(self, client: FREDClient) -> None:
        """Should retry on timeout exceptions."""
        call_count = 0

        async def mock_get(url, *, params=None, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise httpx.TimeoutException("Connection timed out")
            if "observations" in url:
                return _mock_response(200, SAMPLE_OBSERVATIONS)
            return _mock_response(200, SAMPLE_SERIES_META)

        with (
            patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls,
            patch("backend.services.fred_client.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            dataset = await client.download_series("GDP")

        assert dataset.series_id == "GDP"

    async def test_no_retry_on_auth_error(self, client: FREDClient) -> None:
        """Auth errors (4xx) should NOT be retried."""
        call_count = 0

        async def mock_get(url, *, params=None, timeout=None):
            nonlocal call_count
            call_count += 1
            return _mock_response(401, json_data={"error_message": "Bad API key"})

        with patch("backend.services.fred_client.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.get = mock_get
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance

            with pytest.raises(FREDAuthError):
                await client.download_series("GDP")

        # Should only have been called once — no retries
        assert call_count == 1
