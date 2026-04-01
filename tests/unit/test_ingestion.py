"""Unit tests for the Data Ingestion Service."""

from __future__ import annotations

import io
import os
import tempfile
from unittest.mock import AsyncMock

import pandas as pd
import pytest

from backend.models.schemas import FREDDataset, Observation
from backend.services.fred_client import FREDClient
from backend.services.ingestion import (
    FRBSF_COLORS,
    FRBSF_GRIDLINE_COLOR,
    FRBSF_TITLE_COLOR,
    DataIngestionService,
    _build_default_chart_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_dataset(
    series_id: str = "GDP",
    title: str = "Gross Domestic Product",
    units: str = "Billions of Dollars",
    frequency: str = "Quarterly",
    observations: list[Observation] | None = None,
) -> FREDDataset:
    if observations is None:
        observations = [
            Observation(date="2023-01-01", value=26000.0),
            Observation(date="2023-04-01", value=26500.0),
            Observation(date="2023-07-01", value=27000.0),
        ]
    return FREDDataset(
        series_id=series_id,
        title=title,
        units=units,
        frequency=frequency,
        observations=observations,
    )


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def fred_client_mock():
    client = FREDClient(api_key="test-key")
    client.download_series = AsyncMock(return_value=_make_dataset())
    return client


# ---------------------------------------------------------------------------
# _store_data tests
# ---------------------------------------------------------------------------


class TestStoreData:
    def test_creates_directory_and_file(self, tmp_data_dir):
        data_dir = os.path.join(tmp_data_dir, "data")
        svc = DataIngestionService(
            fred_client=FREDClient(api_key="x"), data_dir=data_dir
        )
        df = pd.DataFrame({"date": ["2023-01-01"], "value": [100.0]})
        path = svc._store_data(df, "test.csv")

        assert os.path.exists(path)
        loaded = pd.read_csv(path)
        assert list(loaded.columns) == ["date", "value"]
        assert len(loaded) == 1

    def test_round_trip_preserves_data(self, tmp_data_dir):
        svc = DataIngestionService(
            fred_client=FREDClient(api_key="x"), data_dir=tmp_data_dir
        )
        df = pd.DataFrame({
            "date": ["2023-01-01", "2023-04-01", "2023-07-01"],
            "value": [1.5, 2.5, 3.5],
        })
        path = svc._store_data(df, "round_trip.csv")
        loaded = pd.read_csv(path)
        pd.testing.assert_frame_equal(df, loaded)

    def test_handles_missing_values(self, tmp_data_dir):
        svc = DataIngestionService(
            fred_client=FREDClient(api_key="x"), data_dir=tmp_data_dir
        )
        df = pd.DataFrame({
            "date": ["2023-01-01", "2023-04-01"],
            "value": [1.0, None],
        })
        path = svc._store_data(df, "missing.csv")
        loaded = pd.read_csv(path)
        assert len(loaded) == 2
        assert pd.isna(loaded["value"].iloc[1])


# ---------------------------------------------------------------------------
# _build_default_chart_state tests
# ---------------------------------------------------------------------------


class TestBuildDefaultChartState:
    def test_chart_type_is_line(self):
        ds = _make_dataset()
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/gdp.csv", columns=["date", "value"]
        )
        assert state.chart_type == "line"

    def test_title_from_dataset(self):
        ds = _make_dataset(title="Unemployment Rate")
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/unrate.csv", columns=["date", "value"]
        )
        assert state.title.text == "Unemployment Rate"
        assert state.title.font_color == FRBSF_TITLE_COLOR

    def test_axes_labels_from_metadata(self):
        ds = _make_dataset(units="Percent")
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/test.csv", columns=["date", "value"]
        )
        assert state.axes.x_label == "Date"
        assert state.axes.y_label == "Percent"

    def test_series_uses_frbsf_primary_color(self):
        ds = _make_dataset()
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/gdp.csv", columns=["date", "value"]
        )
        assert len(state.series) == 1
        assert state.series[0].color == FRBSF_COLORS[0]
        assert state.series[0].chart_type == "line"

    def test_legend_visible_with_entry(self):
        ds = _make_dataset()
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/gdp.csv", columns=["date", "value"]
        )
        assert state.legend.visible is True
        assert len(state.legend.entries) == 1
        assert state.legend.entries[0].color == FRBSF_COLORS[0]

    def test_gridlines_defaults(self):
        ds = _make_dataset()
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/gdp.csv", columns=["date", "value"]
        )
        assert state.gridlines.horizontal_visible is True
        assert state.gridlines.vertical_visible is False
        assert state.gridlines.style == "dashed"
        assert state.gridlines.color == FRBSF_GRIDLINE_COLOR

    def test_dataset_path_and_columns(self):
        ds = _make_dataset()
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/gdp.csv", columns=["date", "value"]
        )
        assert state.dataset_path == "data/gdp.csv"
        assert state.dataset_columns == ["date", "value"]

    def test_elements_positions_populated(self):
        ds = _make_dataset()
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/gdp.csv", columns=["date", "value"]
        )
        assert "title" in state.elements_positions
        assert "legend" in state.elements_positions

    def test_empty_units_falls_back_to_value(self):
        ds = _make_dataset(units="")
        state = _build_default_chart_state(
            dataset=ds, dataset_path="data/test.csv", columns=["date", "value"]
        )
        assert state.axes.y_label == "Value"


# ---------------------------------------------------------------------------
# ingest_from_url tests
# ---------------------------------------------------------------------------


class TestIngestFromUrl:
    @pytest.mark.asyncio
    async def test_returns_ingestion_result(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(
            fred_client=fred_client_mock, data_dir=tmp_data_dir
        )
        result = await svc.ingest_from_url(
            "https://fred.stlouisfed.org/series/GDP"
        )

        assert result.dataset_path.endswith("gdp.csv")
        assert os.path.exists(result.dataset_path)
        assert result.dataset_info.source == "fred"
        assert result.dataset_info.row_count == 3
        assert result.dataset_info.columns == ["date", "value"]
        assert result.chart_state.chart_type == "line"
        assert result.chart_state.title.text == "Gross Domestic Product"

    @pytest.mark.asyncio
    async def test_stores_csv_file(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(
            fred_client=fred_client_mock, data_dir=tmp_data_dir
        )
        result = await svc.ingest_from_url(
            "https://fred.stlouisfed.org/series/GDP"
        )
        df = pd.read_csv(result.dataset_path)
        assert len(df) == 3
        assert list(df.columns) == ["date", "value"]

    @pytest.mark.asyncio
    async def test_date_range_in_dataset_info(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(
            fred_client=fred_client_mock, data_dir=tmp_data_dir
        )
        result = await svc.ingest_from_url(
            "https://fred.stlouisfed.org/series/GDP"
        )
        assert result.dataset_info.date_range == "2023-01-01 to 2023-07-01"

    @pytest.mark.asyncio
    async def test_invalid_url_raises(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(
            fred_client=fred_client_mock, data_dir=tmp_data_dir
        )
        with pytest.raises(ValueError, match="Invalid FRED URL"):
            await svc.ingest_from_url("https://example.com/not-fred")

    @pytest.mark.asyncio
    async def test_handles_missing_observation_values(self, tmp_data_dir):
        ds = _make_dataset(
            observations=[
                Observation(date="2023-01-01", value=100.0),
                Observation(date="2023-04-01", value=None),
            ]
        )
        client = FREDClient(api_key="test-key")
        client.download_series = AsyncMock(return_value=ds)
        svc = DataIngestionService(fred_client=client, data_dir=tmp_data_dir)
        result = await svc.ingest_from_url(
            "https://fred.stlouisfed.org/series/GDP"
        )
        assert result.dataset_info.row_count == 2


# ---------------------------------------------------------------------------
# Fake UploadFile helper
# ---------------------------------------------------------------------------


class FakeUploadFile:
    """Mimics FastAPI's UploadFile for testing."""

    def __init__(self, filename: str, content: bytes) -> None:
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


# ---------------------------------------------------------------------------
# _parse_csv / _parse_excel tests
# ---------------------------------------------------------------------------


class TestParseCsv:
    def test_parses_valid_csv(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        csv_bytes = b"date,value\n2023-01-01,100\n2023-04-01,200\n"
        df = svc._parse_csv(csv_bytes)
        assert list(df.columns) == ["date", "value"]
        assert len(df) == 2

    def test_raises_on_malformed_csv(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        # Completely invalid binary content
        with pytest.raises(ValueError, match="Failed to parse CSV"):
            svc._parse_csv(b"\x00\x01\x02\x03\x80\x81")


class TestParseExcel:
    def test_parses_valid_excel(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        df_orig = pd.DataFrame({"date": ["2023-01-01"], "value": [42.0]})
        buf = io.BytesIO()
        df_orig.to_excel(buf, index=False)
        buf.seek(0)
        df = svc._parse_excel(buf.read())
        assert list(df.columns) == ["date", "value"]
        assert len(df) == 1

    def test_raises_on_malformed_excel(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        with pytest.raises(ValueError, match="Failed to parse Excel"):
            svc._parse_excel(b"this is not an excel file")


# ---------------------------------------------------------------------------
# ingest_from_file tests
# ---------------------------------------------------------------------------


class TestIngestFromFile:
    @pytest.mark.asyncio
    async def test_csv_ingestion(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        csv_bytes = b"date,value\n2023-01-01,100\n2023-04-01,200\n"
        fake = FakeUploadFile("my_data.csv", csv_bytes)
        result = await svc.ingest_from_file(fake)

        assert result.dataset_info.source == "upload"
        assert result.dataset_info.row_count == 2
        assert result.dataset_info.columns == ["date", "value"]
        assert os.path.exists(result.dataset_path)
        assert result.chart_state.chart_type == "line"
        assert result.chart_state.title.text == "my_data"

    @pytest.mark.asyncio
    async def test_excel_ingestion(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        df_orig = pd.DataFrame({"month": ["Jan", "Feb"], "sales": [10, 20]})
        buf = io.BytesIO()
        df_orig.to_excel(buf, index=False)
        buf.seek(0)
        fake = FakeUploadFile("sales.xlsx", buf.read())
        result = await svc.ingest_from_file(fake)

        assert result.dataset_info.source == "upload"
        assert result.dataset_info.row_count == 2
        assert "sales" in result.dataset_info.columns
        assert result.chart_state.chart_type == "line"

    @pytest.mark.asyncio
    async def test_unsupported_format_raises(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        fake = FakeUploadFile("data.json", b'{"key": "value"}')
        with pytest.raises(ValueError, match="Unsupported file format"):
            await svc.ingest_from_file(fake)

    @pytest.mark.asyncio
    async def test_unsupported_format_mentions_accepted(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        fake = FakeUploadFile("data.txt", b"hello")
        with pytest.raises(ValueError, match=r"\.csv.*\.xlsx.*\.xls"):
            await svc.ingest_from_file(fake)

    @pytest.mark.asyncio
    async def test_malformed_csv_raises(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        fake = FakeUploadFile("bad.csv", b"\x00\x01\x02\x03\x80\x81")
        with pytest.raises(ValueError, match="Failed to parse"):
            await svc.ingest_from_file(fake)

    @pytest.mark.asyncio
    async def test_empty_csv_raises(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        fake = FakeUploadFile("empty.csv", b"")
        with pytest.raises(ValueError):
            await svc.ingest_from_file(fake)

    @pytest.mark.asyncio
    async def test_date_range_detected(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        csv_bytes = b"date,value\n2020-01-01,10\n2024-06-01,20\n"
        fake = FakeUploadFile("dates.csv", csv_bytes)
        result = await svc.ingest_from_file(fake)
        assert result.dataset_info.date_range is not None
        assert "2020" in result.dataset_info.date_range
        assert "2024" in result.dataset_info.date_range

    @pytest.mark.asyncio
    async def test_multiple_numeric_columns_create_series(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        csv_bytes = b"date,gdp,unemployment\n2023-01-01,100,5.0\n2023-04-01,200,4.5\n"
        fake = FakeUploadFile("multi.csv", csv_bytes)
        result = await svc.ingest_from_file(fake)
        assert len(result.chart_state.series) == 2
        assert result.chart_state.series[0].color == FRBSF_COLORS[0]
        assert result.chart_state.series[1].color == FRBSF_COLORS[1]

    @pytest.mark.asyncio
    async def test_stored_file_is_readable(self, fred_client_mock, tmp_data_dir):
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        csv_bytes = b"x,y\n1,2\n3,4\n"
        fake = FakeUploadFile("simple.csv", csv_bytes)
        result = await svc.ingest_from_file(fake)
        loaded = pd.read_csv(result.dataset_path)
        assert len(loaded) == 2
        assert list(loaded.columns) == ["x", "y"]

    @pytest.mark.asyncio
    async def test_xls_extension_accepted(self, fred_client_mock, tmp_data_dir):
        """Ensure .xls extension is recognized (even though openpyxl writes .xlsx)."""
        svc = DataIngestionService(fred_client=fred_client_mock, data_dir=tmp_data_dir)
        df_orig = pd.DataFrame({"a": [1], "b": [2]})
        buf = io.BytesIO()
        df_orig.to_excel(buf, index=False, engine="openpyxl")
        buf.seek(0)
        # We label it .xls but the content is actually xlsx — the parser
        # should still handle it via openpyxl fallback.
        fake = FakeUploadFile("legacy.xls", buf.read())
        result = await svc.ingest_from_file(fake)
        assert result.dataset_info.row_count == 1
