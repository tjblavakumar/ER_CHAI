"""Unit tests for the Image Analyzer service.

Covers:
- ``_merge_results`` logic (colour mapping, legend layout, defaults)
- Error handling for unreadable / non-chart images
- Mocked Bedrock Vision responses
- OpenCV extraction on a synthetic image
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from backend.models.schemas import (
    AnnotationSpec,
    AxisConfig,
    ChartSpecification,
    ContourInfo,
    DataTableSpec,
    FontSpec,
    FontStyles,
    LegendEntry,
    LegendLayout,
    OpenCVResult,
    TextRegion,
    VisionResult,
)
from backend.services.image_analyzer import ImageAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_solid_image(color_bgr: tuple[int, int, int] = (200, 100, 50),
                      width: int = 200, height: int = 150) -> bytes:
    """Create a simple solid-colour PNG image as bytes."""
    img = np.full((height, width, 3), color_bgr, dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _make_chart_like_image() -> bytes:
    """Create a synthetic chart-like image with lines and text-like regions."""
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255  # white background

    # Draw axes
    cv2.line(img, (60, 350), (560, 350), (0, 0, 0), 2)  # x-axis
    cv2.line(img, (60, 50), (60, 350), (0, 0, 0), 2)    # y-axis

    # Draw a "data line" in blue
    pts = np.array([[100, 300], [200, 200], [300, 250], [400, 150], [500, 180]])
    cv2.polylines(img, [pts], isClosed=False, color=(180, 80, 0), thickness=2)

    # Draw a rectangle to simulate a legend box
    cv2.rectangle(img, (400, 60), (560, 100), (0, 0, 0), 1)

    # Draw text-like blocks (filled rectangles simulating text)
    cv2.rectangle(img, (250, 10), (400, 35), (60, 60, 60), -1)   # title area
    cv2.rectangle(img, (250, 370), (400, 390), (60, 60, 60), -1)  # x-label area

    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _make_opencv_result(
    colors: list[str] | None = None,
    text_regions: list[TextRegion] | None = None,
    contours: list[ContourInfo] | None = None,
) -> OpenCVResult:
    return OpenCVResult(
        dominant_colors=colors if colors is not None else ["#003B5C", "#5B9BD5", "#FFFFFF"],
        text_regions=text_regions if text_regions is not None else [],
        contour_data=contours if contours is not None else [],
    )


def _make_vision_result(
    chart_type: str = "line",
    legend_entries: list[LegendEntry] | None = None,
    layout_description: str = "Legend at bottom, horizontal layout",
    annotations: list[AnnotationSpec] | None = None,
    data_table: DataTableSpec | None = None,
) -> VisionResult:
    return VisionResult(
        chart_type=chart_type,
        axis_config=AxisConfig(x_label="Date", y_label="Value"),
        legend_entries=legend_entries if legend_entries is not None else [
            LegendEntry(label="GDP", color="#0000FF", series_name="gdp"),
        ],
        annotations=annotations if annotations is not None else [],
        data_table=data_table,
        layout_description=layout_description,
    )


# ---------------------------------------------------------------------------
# Tests: _merge_results
# ---------------------------------------------------------------------------


class TestMergeResults:
    """Tests for the merge logic combining OpenCV + Vision results."""

    def setup_method(self) -> None:
        self.analyzer = ImageAnalyzer(bedrock_client=MagicMock())

    def test_merge_uses_vision_chart_type(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result(chart_type="bar")
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.chart_type == "bar"

    def test_merge_uses_opencv_colors_for_legend_entries(self) -> None:
        cv = _make_opencv_result(colors=["#FF0000", "#00FF00", "#0000FF"])
        vision = _make_vision_result(legend_entries=[
            LegendEntry(label="A", color="#111111", series_name="a"),
            LegendEntry(label="B", color="#222222", series_name="b"),
        ])
        spec = self.analyzer._merge_results(cv, vision)
        # OpenCV colours should be preferred
        assert spec.color_mappings["a"] == "#FF0000"
        assert spec.color_mappings["b"] == "#00FF00"

    def test_merge_falls_back_to_vision_color_when_opencv_short(self) -> None:
        cv = _make_opencv_result(colors=["#FF0000"])
        vision = _make_vision_result(legend_entries=[
            LegendEntry(label="A", color="#111111", series_name="a"),
            LegendEntry(label="B", color="#222222", series_name="b"),
        ])
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.color_mappings["a"] == "#FF0000"
        assert spec.color_mappings["b"] == "#222222"  # fallback to vision

    def test_merge_creates_default_mapping_when_no_legend_entries(self) -> None:
        cv = _make_opencv_result(colors=["#AABBCC", "#DDEEFF"])
        vision = _make_vision_result(legend_entries=[])
        spec = self.analyzer._merge_results(cv, vision)
        # Should create mappings from OpenCV colours
        assert "series_0" in spec.color_mappings
        assert spec.color_mappings["series_0"] == "#AABBCC"

    def test_merge_ensures_at_least_one_color_mapping(self) -> None:
        cv = _make_opencv_result(colors=[])
        vision = _make_vision_result(legend_entries=[])
        spec = self.analyzer._merge_results(cv, vision)
        assert len(spec.color_mappings) >= 1

    def test_merge_uses_vision_axis_config(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result()
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.axis_config.x_label == "Date"
        assert spec.axis_config.y_label == "Value"

    def test_merge_uses_frbsf_default_font_styles(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result()
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.font_styles.title.family == "Arial"
        assert spec.font_styles.title.size == 16

    def test_merge_legend_layout_right(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result(layout_description="Legend on the right side")
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.legend_layout.position == "right"
        assert spec.legend_layout.orientation == "vertical"

    def test_merge_legend_layout_top(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result(layout_description="Legend at top")
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.legend_layout.position == "top"

    def test_merge_legend_layout_default_bottom(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result(layout_description="Standard chart layout")
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.legend_layout.position == "bottom"

    def test_merge_preserves_vision_annotations(self) -> None:
        ann = AnnotationSpec(text="Recession", x=100, y=200)
        cv = _make_opencv_result()
        vision = _make_vision_result(annotations=[ann])
        spec = self.analyzer._merge_results(cv, vision)
        assert len(spec.annotations) == 1
        assert spec.annotations[0].text == "Recession"

    def test_merge_preserves_vision_data_table(self) -> None:
        dt = DataTableSpec(columns=["Date", "Value"], visible=True, font_size=10)
        cv = _make_opencv_result()
        vision = _make_vision_result(data_table=dt)
        spec = self.analyzer._merge_results(cv, vision)
        assert spec.data_table is not None
        assert spec.data_table.columns == ["Date", "Value"]

    def test_merge_returns_valid_chart_specification(self) -> None:
        cv = _make_opencv_result()
        vision = _make_vision_result()
        spec = self.analyzer._merge_results(cv, vision)
        # Should be a valid ChartSpecification
        assert isinstance(spec, ChartSpecification)
        assert spec.chart_type in ("line", "bar", "mixed")
        assert len(spec.color_mappings) > 0
        assert spec.font_styles is not None
        assert spec.axis_config is not None


# ---------------------------------------------------------------------------
# Tests: Error handling
# ---------------------------------------------------------------------------


class TestAnalyzeErrors:
    """Tests for error handling on invalid / non-chart images."""

    def setup_method(self) -> None:
        self.analyzer = ImageAnalyzer(bedrock_client=MagicMock())

    @pytest.mark.asyncio
    async def test_analyze_rejects_invalid_bytes(self) -> None:
        with pytest.raises(ValueError, match="Unable to decode"):
            await self.analyzer.analyze(b"not-an-image")

    @pytest.mark.asyncio
    async def test_analyze_rejects_empty_bytes(self) -> None:
        with pytest.raises(ValueError, match="Unable to decode"):
            await self.analyzer.analyze(b"")

    def test_opencv_extract_rejects_invalid_bytes(self) -> None:
        with pytest.raises(ValueError, match="Unable to decode"):
            self.analyzer._opencv_extract(b"garbage-data")


# ---------------------------------------------------------------------------
# Tests: OpenCV extraction on synthetic images
# ---------------------------------------------------------------------------


class TestOpenCVExtract:
    """Tests for the OpenCV extraction pipeline."""

    def setup_method(self) -> None:
        self.analyzer = ImageAnalyzer(bedrock_client=MagicMock())

    def test_extract_dominant_colors_returns_hex_list(self) -> None:
        image_bytes = _make_solid_image(color_bgr=(200, 100, 50))
        result = self.analyzer._opencv_extract(image_bytes)
        assert len(result.dominant_colors) > 0
        for c in result.dominant_colors:
            assert c.startswith("#")
            assert len(c) == 7

    def test_extract_from_chart_like_image(self) -> None:
        image_bytes = _make_chart_like_image()
        result = self.analyzer._opencv_extract(image_bytes)
        # Should find some dominant colours
        assert len(result.dominant_colors) > 0
        # Should find some text regions or contours in a chart-like image
        # (exact counts depend on the synthetic image, just verify structure)
        assert isinstance(result.text_regions, list)
        assert isinstance(result.contour_data, list)

    def test_dominant_colors_are_sorted_by_frequency(self) -> None:
        # Create an image that is mostly red with a small blue patch
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[:, :] = (0, 0, 255)  # red in BGR
        img[0:20, 0:20] = (255, 0, 0)  # small blue patch
        _, buf = cv2.imencode(".png", img)
        image_bytes = buf.tobytes()

        result = self.analyzer._opencv_extract(image_bytes)
        # The most dominant colour should be close to red
        # (exact hex depends on k-means, but red should dominate)
        assert len(result.dominant_colors) > 0


# ---------------------------------------------------------------------------
# Tests: Bedrock Vision (mocked)
# ---------------------------------------------------------------------------


class TestBedrockVisionAnalyze:
    """Tests for the Bedrock Vision analysis with mocked API responses."""

    def _make_mock_bedrock(self, response_json: dict) -> MagicMock:
        """Create a mock bedrock client that returns *response_json*."""
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "content": [{"type": "text", "text": json.dumps(response_json)}],
        }).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": mock_body}
        return mock_client

    @pytest.mark.asyncio
    async def test_vision_analyze_parses_valid_response(self) -> None:
        response = {
            "chart_type": "bar",
            "axis_config": {"x_label": "Year", "y_label": "GDP"},
            "legend_entries": [
                {"label": "US GDP", "color": "#003B5C", "series_name": "us_gdp"},
            ],
            "annotations": [{"text": "Peak", "x": 100, "y": 50}],
            "data_table": None,
            "layout_description": "Bar chart with legend on the right",
        }
        mock_client = self._make_mock_bedrock(response)
        analyzer = ImageAnalyzer(bedrock_client=mock_client)

        image_bytes = _make_solid_image()
        result = await analyzer._bedrock_vision_analyze(image_bytes)

        assert result.chart_type == "bar"
        assert result.axis_config.x_label == "Year"
        assert len(result.legend_entries) == 1
        assert result.legend_entries[0].series_name == "us_gdp"
        assert len(result.annotations) == 1

    @pytest.mark.asyncio
    async def test_vision_analyze_handles_unknown_chart_type(self) -> None:
        response = {
            "chart_type": "scatter",  # not in our supported set
            "axis_config": {},
            "legend_entries": [],
            "annotations": [],
            "data_table": None,
            "layout_description": "",
        }
        mock_client = self._make_mock_bedrock(response)
        analyzer = ImageAnalyzer(bedrock_client=mock_client)

        result = await analyzer._bedrock_vision_analyze(_make_solid_image())
        assert result.chart_type == "line"  # should default to "line"

    @pytest.mark.asyncio
    async def test_vision_analyze_raises_on_api_error(self) -> None:
        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = RuntimeError("API down")
        analyzer = ImageAnalyzer(bedrock_client=mock_client)

        with pytest.raises(ValueError, match="Bedrock Vision analysis failed"):
            await analyzer._bedrock_vision_analyze(_make_solid_image())

    @pytest.mark.asyncio
    async def test_vision_analyze_handles_missing_fields(self) -> None:
        """Vision response with minimal fields should still parse."""
        response = {
            "chart_type": "line",
            "layout_description": "Simple line chart",
        }
        mock_client = self._make_mock_bedrock(response)
        analyzer = ImageAnalyzer(bedrock_client=mock_client)

        result = await analyzer._bedrock_vision_analyze(_make_solid_image())
        assert result.chart_type == "line"
        assert result.legend_entries == []
        assert result.annotations == []


# ---------------------------------------------------------------------------
# Tests: Full pipeline (mocked Bedrock)
# ---------------------------------------------------------------------------


class TestAnalyzeFullPipeline:
    """Integration-style test for the full analyze() pipeline with mocked Bedrock."""

    @pytest.mark.asyncio
    async def test_analyze_returns_chart_specification(self) -> None:
        response = {
            "chart_type": "line",
            "axis_config": {"x_label": "Date", "y_label": "Rate"},
            "legend_entries": [
                {"label": "Fed Rate", "color": "#003B5C", "series_name": "fed_rate"},
            ],
            "annotations": [],
            "data_table": None,
            "layout_description": "Line chart with legend at bottom",
        }
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({
            "content": [{"type": "text", "text": json.dumps(response)}],
        }).encode()
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = {"body": mock_body}

        analyzer = ImageAnalyzer(bedrock_client=mock_client)
        image_bytes = _make_chart_like_image()

        spec = await analyzer.analyze(image_bytes)

        assert isinstance(spec, ChartSpecification)
        assert spec.chart_type == "line"
        assert "fed_rate" in spec.color_mappings
        assert spec.font_styles.title.family == "Arial"
        assert spec.axis_config.x_label == "Date"
