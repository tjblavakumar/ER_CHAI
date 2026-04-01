"""Unit tests for the Export Service."""

from __future__ import annotations

import ast
import io
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from backend.models.schemas import (
    AnnotationConfig,
    AxesConfig,
    ChartElementState,
    ChartState,
    GridlineConfig,
    LegendConfig,
    LegendEntry,
    Position,
    SeriesConfig,
)
from backend.services.export_service import (
    ExportService,
    _build_pdf,
    _df_to_python_literal,
    _df_to_r_literal,
    _generate_python_script,
    _generate_r_script,
    _render_chart_image,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2020-01-01", "2020-02-01", "2020-03-01"],
        "value": [1.5, 2.3, 3.1],
    })


@pytest.fixture
def sample_csv(sample_df: pd.DataFrame, tmp_path: Path) -> Path:
    p = tmp_path / "data.csv"
    sample_df.to_csv(p, index=False)
    return p


@pytest.fixture
def chart_state(sample_csv: Path) -> ChartState:
    return ChartState(
        chart_type="line",
        title=ChartElementState(
            text="Test Chart",
            font_family="Arial",
            font_size=16,
            font_color="#003A70",
            position=Position(x=100, y=10),
        ),
        axes=AxesConfig(x_label="Date", y_label="Value"),
        series=[
            SeriesConfig(
                name="Series A",
                column="value",
                chart_type="line",
                color="#0072CE",
                line_width=2.0,
                visible=True,
            ),
        ],
        legend=LegendConfig(
            visible=True,
            position=Position(x=300, y=10),
            entries=[
                LegendEntry(label="Series A", color="#0072CE", series_name="Series A"),
            ],
        ),
        gridlines=GridlineConfig(
            horizontal_visible=True,
            vertical_visible=False,
            style="dashed",
            color="#cccccc",
        ),
        annotations=[],
        data_table=None,
        elements_positions={},
        dataset_path=str(sample_csv),
        dataset_columns=["date", "value"],
    )


@pytest.fixture
def bar_chart_state(sample_csv: Path) -> ChartState:
    """Chart state with bar series."""
    return ChartState(
        chart_type="bar",
        title=ChartElementState(
            text="Bar Chart",
            font_family="Helvetica",
            font_size=14,
            font_color="#000000",
            position=Position(x=100, y=10),
        ),
        axes=AxesConfig(x_label="Date", y_label="Count"),
        series=[
            SeriesConfig(
                name="Bars",
                column="value",
                chart_type="bar",
                color="#FF5733",
                line_width=2.0,
                visible=True,
            ),
        ],
        legend=LegendConfig(
            visible=False,
            position=Position(x=0, y=0),
            entries=[],
        ),
        gridlines=GridlineConfig(
            horizontal_visible=False,
            vertical_visible=False,
            style="solid",
            color="#cccccc",
        ),
        annotations=[],
        data_table=None,
        elements_positions={},
        dataset_path=str(sample_csv),
        dataset_columns=["date", "value"],
    )


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestDfToPythonLiteral:
    def test_basic_conversion(self, sample_df: pd.DataFrame) -> None:
        result = _df_to_python_literal(sample_df)
        assert "data = {" in result
        assert "'date'" in result
        assert "'value'" in result
        assert "2020-01-01" in result
        assert "1.5" in result

    def test_produces_valid_python(self, sample_df: pd.DataFrame) -> None:
        result = _df_to_python_literal(sample_df)
        # Should parse as valid Python
        ast.parse(result)

    def test_nan_values(self) -> None:
        df = pd.DataFrame({"a": [1.0, float("nan"), 3.0]})
        result = _df_to_python_literal(df)
        assert "None" in result


class TestDfToRLiteral:
    def test_basic_conversion(self, sample_df: pd.DataFrame) -> None:
        result = _df_to_r_literal(sample_df)
        assert "data <- data.frame(" in result
        assert "date" in result
        assert "value" in result

    def test_nan_values(self) -> None:
        df = pd.DataFrame({"a": [1.0, float("nan"), 3.0]})
        result = _df_to_r_literal(df)
        assert "NA" in result


# ---------------------------------------------------------------------------
# Python export tests
# ---------------------------------------------------------------------------


class TestExportPython:
    @pytest.mark.asyncio
    async def test_produces_valid_zip(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_python(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert "chart.py" in names
            assert "requirements.txt" in names

    @pytest.mark.asyncio
    async def test_requirements_content(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_python(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            req = zf.read("requirements.txt").decode()
            assert "matplotlib" in req
            assert "pandas" in req

    @pytest.mark.asyncio
    async def test_script_contains_data(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_python(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.py").decode()
            assert "data = {" in script
            assert "2020-01-01" in script
            assert "pd.DataFrame" in script

    @pytest.mark.asyncio
    async def test_script_valid_python(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_python(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.py").decode()
            ast.parse(script)  # should not raise

    @pytest.mark.asyncio
    async def test_script_contains_chart_config(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_python(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.py").decode()
            assert "Test Chart" in script
            assert "#0072CE" in script
            assert "Date" in script
            assert "Value" in script

    @pytest.mark.asyncio
    async def test_bar_chart_export(self, bar_chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_python(bar_chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.py").decode()
            assert "ax.bar(" in script


# ---------------------------------------------------------------------------
# R export tests
# ---------------------------------------------------------------------------


class TestExportR:
    @pytest.mark.asyncio
    async def test_produces_valid_zip(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_r(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            names = zf.namelist()
            assert "chart.R" in names
            assert "install_packages.R" in names

    @pytest.mark.asyncio
    async def test_r_script_contains_data(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_r(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.R").decode()
            assert "data <- data.frame(" in script
            assert "2020-01-01" in script

    @pytest.mark.asyncio
    async def test_r_script_uses_ggplot2(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_r(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.R").decode()
            assert "library(ggplot2)" in script
            assert "ggplot(data)" in script

    @pytest.mark.asyncio
    async def test_r_script_contains_chart_config(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_r(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.R").decode()
            assert "Test Chart" in script
            assert "Date" in script
            assert "Value" in script

    @pytest.mark.asyncio
    async def test_install_packages_script(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_r(chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            install = zf.read("install_packages.R").decode()
            assert "ggplot2" in install
            assert "install.packages" in install

    @pytest.mark.asyncio
    async def test_bar_chart_r_export(self, bar_chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_r(bar_chart_state)

        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.R").decode()
            assert "geom_bar(" in script


# ---------------------------------------------------------------------------
# PDF export tests
# ---------------------------------------------------------------------------


class TestExportPdf:
    @pytest.mark.asyncio
    async def test_produces_pdf_bytes(self, chart_state: ChartState) -> None:
        service = ExportService()
        result = await service.export_pdf(chart_state, "This is a test summary.")

        # PDF files start with %PDF
        assert result[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_pdf_contains_summary(self, chart_state: ChartState) -> None:
        service = ExportService()
        summary = "Economic trends show growth in Q1 2020."
        result = await service.export_pdf(chart_state, summary)

        # PDF should be non-trivial in size (has image + text)
        assert len(result) > 1000

    @pytest.mark.asyncio
    async def test_pdf_with_multiline_summary(self, chart_state: ChartState) -> None:
        service = ExportService()
        summary = "Line one of the summary.\nLine two of the summary.\nLine three."
        result = await service.export_pdf(chart_state, summary)
        assert result[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Chart image rendering tests
# ---------------------------------------------------------------------------


class TestRenderChartImage:
    def test_renders_png(self, chart_state: ChartState, sample_df: pd.DataFrame) -> None:
        result = _render_chart_image(chart_state, sample_df)
        # PNG magic bytes
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_renders_bar_chart(self, bar_chart_state: ChartState, sample_df: pd.DataFrame) -> None:
        result = _render_chart_image(bar_chart_state, sample_df)
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_image_size_reasonable(self, chart_state: ChartState, sample_df: pd.DataFrame) -> None:
        result = _render_chart_image(chart_state, sample_df)
        # At 300 DPI, a 10x6 figure should produce a sizable image
        assert len(result) > 5000


# ---------------------------------------------------------------------------
# PDF builder tests
# ---------------------------------------------------------------------------


class TestBuildPdf:
    def test_basic_pdf(self, chart_state: ChartState, sample_df: pd.DataFrame) -> None:
        img = _render_chart_image(chart_state, sample_df)
        result = _build_pdf(img, "Test summary text.")
        assert result[:5] == b"%PDF-"

    def test_empty_summary(self, chart_state: ChartState, sample_df: pd.DataFrame) -> None:
        img = _render_chart_image(chart_state, sample_df)
        result = _build_pdf(img, "")
        assert result[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_single_data_point(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "single.csv"
        pd.DataFrame({"date": ["2020-01-01"], "value": [42.0]}).to_csv(csv_path, index=False)

        state = ChartState(
            chart_type="line",
            title=ChartElementState(
                text="Single Point", font_family="Arial", font_size=14,
                font_color="#000000", position=Position(x=0, y=0),
            ),
            axes=AxesConfig(x_label="X", y_label="Y"),
            series=[SeriesConfig(name="S", column="value", chart_type="line", color="#000000")],
            legend=LegendConfig(visible=False, position=Position(x=0, y=0), entries=[]),
            gridlines=GridlineConfig(),
            annotations=[],
            data_table=None,
            elements_positions={},
            dataset_path=str(csv_path),
            dataset_columns=["date", "value"],
        )

        service = ExportService()
        py_zip = await service.export_python(state)
        r_zip = await service.export_r(state)
        pdf = await service.export_pdf(state, "Single point summary.")

        assert zipfile.is_zipfile(io.BytesIO(py_zip))
        assert zipfile.is_zipfile(io.BytesIO(r_zip))
        assert pdf[:5] == b"%PDF-"

    @pytest.mark.asyncio
    async def test_hidden_series_excluded(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({"date": ["2020-01-01"], "a": [1.0], "b": [2.0]}).to_csv(csv_path, index=False)

        state = ChartState(
            chart_type="line",
            title=ChartElementState(
                text="Hidden", font_family="Arial", font_size=14,
                font_color="#000000", position=Position(x=0, y=0),
            ),
            axes=AxesConfig(x_label="X", y_label="Y"),
            series=[
                SeriesConfig(name="Visible", column="a", chart_type="line", color="#FF0000", visible=True),
                SeriesConfig(name="Hidden", column="b", chart_type="line", color="#00FF00", visible=False),
            ],
            legend=LegendConfig(visible=False, position=Position(x=0, y=0), entries=[]),
            gridlines=GridlineConfig(),
            annotations=[],
            data_table=None,
            elements_positions={},
            dataset_path=str(csv_path),
            dataset_columns=["date", "a", "b"],
        )

        service = ExportService()
        result = await service.export_python(state)
        with zipfile.ZipFile(io.BytesIO(result)) as zf:
            script = zf.read("chart.py").decode()
            assert "#FF0000" in script
            # Hidden series should not appear in plot commands
            assert 'color="#00FF00"' not in script
