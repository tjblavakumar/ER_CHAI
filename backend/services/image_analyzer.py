"""Image Analyzer service for the FRBSF Chart Builder.

Uses a dual pipeline — OpenCV for deterministic extraction (colors, contours,
text regions) and AWS Bedrock Vision for semantic chart understanding — then
merges both results into a unified ``ChartSpecification``.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

import boto3
import cv2
import numpy as np

from backend.models.schemas import (
    AnnotationSpec,
    AxisConfig,
    ChartSpecification,
    ComputedColumnDefinition,
    ContourInfo,
    DataTableSpec,
    FontSpec,
    FontStyles,
    LegendEntry,
    LegendLayout,
    OpenCVResult,
    TextRegion,
    VerticalBand,
    VisionResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FRBSF defaults (fallbacks when extraction is incomplete)
# ---------------------------------------------------------------------------

_DEFAULT_FONT_STYLES = FontStyles(
    title=FontSpec(family="Arial", size=16, color="#003B5C", weight="bold"),
    axis_label=FontSpec(family="Arial", size=12, color="#333333"),
    tick_label=FontSpec(family="Arial", size=10, color="#333333"),
    legend=FontSpec(family="Arial", size=11, color="#333333"),
    annotation=FontSpec(family="Arial", size=10, color="#333333"),
)

_DEFAULT_LEGEND_LAYOUT = LegendLayout(position="bottom", orientation="horizontal")


# ---------------------------------------------------------------------------
# Image Analyzer
# ---------------------------------------------------------------------------


class ImageAnalyzer:
    """Orchestrates OpenCV + Bedrock Vision analysis of reference chart images."""

    def __init__(self, bedrock_client: Any | None = None, *, region: str = "us-east-1",
                 vision_model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0") -> None:
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime", region_name=region,
        )
        self._vision_model_id = vision_model_id

    # -- Public API ---------------------------------------------------------

    async def analyze(self, image_bytes: bytes) -> tuple[ChartSpecification, VisionResult]:
        """Run the full analysis pipeline on *image_bytes*.

        Returns a tuple of (ChartSpecification, VisionResult) so callers
        can access both the merged spec and the raw Vision details.
        """
        if not image_bytes:
            raise ValueError(
                "Unable to decode the provided image. "
                "Please supply a valid PNG, JPEG, or BMP file."
            )
        img_array = np.frombuffer(image_bytes, dtype=np.uint8)
        try:
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except cv2.error:
            img = None
        if img is None:
            raise ValueError(
                "Unable to decode the provided image. "
                "Please supply a valid PNG, JPEG, or BMP file."
            )

        cv_result = self._opencv_extract(image_bytes)
        vision_result = await self._bedrock_vision_analyze(image_bytes)

        return self._merge_results(cv_result, vision_result), vision_result

    # -- OpenCV extraction --------------------------------------------------

    def _opencv_extract(self, image_bytes: bytes) -> OpenCVResult:
        """Extract dominant colors, text regions, and contour data using OpenCV.

        Returns an ``OpenCVResult`` with:
        - ``dominant_colors``: up to 5 hex colours via k-means clustering.
        - ``text_regions``: bounding-box regions likely containing text.
        - ``contour_data``: significant contours (chart elements).
        """
        img_array = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Unable to decode image for OpenCV extraction.")

        dominant_colors = self._extract_dominant_colors(img, k=5)
        text_regions = self._extract_text_regions(img)
        contour_data = self._extract_contours(img)

        return OpenCVResult(
            dominant_colors=dominant_colors,
            text_regions=text_regions,
            contour_data=contour_data,
        )

    # -- Bedrock Vision analysis --------------------------------------------

    async def _bedrock_vision_analyze(self, image_bytes: bytes) -> VisionResult:
        """Send the image to Bedrock Vision API for comprehensive chart analysis."""
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "You are an expert chart analyst. Analyze this chart image THOROUGHLY and "
            "extract EVERY visual element. Return a JSON object with ALL of the following fields.\n\n"
            "REQUIRED FIELDS:\n"
            '1. "chart_type": one of "line", "bar", "area", or "mixed"\n'
            '2. "title": the chart title text (exact text as shown)\n'
            '3. "title_font_size": estimated font size of the title (integer)\n'
            '4. "title_color": hex color of the title text\n\n'
            "AXIS CONFIGURATION:\n"
            '5. "axis_config": {\n'
            '     "x_label": x-axis label text,\n'
            '     "y_label": y-axis label text,\n'
            '     "x_min": minimum x value or null,\n'
            '     "x_max": maximum x value or null,\n'
            '     "y_min": minimum y value shown on axis,\n'
            '     "y_max": maximum y value shown on axis\n'
            "   }\n"
            '6. "y_format": how y-axis values are formatted. Values:\n'
            '   - "percent" if values have % symbol\n'
            '   - "integer" if values are whole numbers\n'
            '   - "decimal1" if values have 1 decimal place\n'
            '   - "auto" otherwise\n'
            '7. "axis_line_width": thickness of axis lines (1-5)\n'
            '8. "tick_font_size": font size of tick labels\n\n'
            "DATA SERIES (CRITICAL - be very precise with colors):\n"
            '9. "legend_entries": array of objects for EACH data series:\n'
            "   [{\n"
            '     "label": display name of the series,\n'
            '     "color": EXACT hex color of the line/bar (e.g., "#003B5C"),\n'
            '     "series_name": identifier for the series\n'
            "   }]\n"
            '10. "series_line_widths": array of line widths for each series (e.g., [2.0, 1.5])\n'
            '11. "series_line_styles": array of line styles for each series '
            '("solid", "dashed", "dotted")\n'
            '12. "legend_position": where legends appear - "inline" (next to lines), '
            '"top", "bottom", "right"\n\n'
            "GRIDLINES:\n"
            '13. "gridline_style": "solid", "dashed", "dotted", or "none"\n'
            '14. "gridline_color": hex color of gridlines\n\n'
            "ANNOTATIONS (extract ALL text annotations, lines, and bands):\n"
            '15. "annotations": array of text annotations visible on the chart:\n'
            '   [{"text": "annotation text", "x": pixel_x, "y": pixel_y}]\n'
            '16. "horizontal_lines": array of horizontal reference lines:\n'
            '   [{"value": y_axis_value, "label": "text label if any", '
            '"color": hex_color, "style": "dotted/dashed/solid"}]\n'
            '   Look for dotted/dashed lines that span the full chart width at a specific Y value.\n'
            '17. "vertical_bands": array of shaded vertical regions:\n'
            '   [{"start": "start_date", "end": "end_date", "color": hex_color}]\n'
            '   Look for shaded/highlighted rectangular regions spanning the chart height.\n\n'
            "DATA TABLE:\n"
            '18. "data_table": if a data table is visible below/beside the chart:\n'
            '   {"columns": [column_names], "visible": true, "font_size": 10,\n'
            '    "layout": "transposed" or "standard" (transposed = dates as columns and series as rows),\n'
            '    "num_sampled_dates": number of date columns shown (integer),\n'
            '    "series_shown": [list of series names in the table],\n'
            '    "computed_columns": array of any computed/derived columns detected in the table.\n'
            "     Look for columns whose values are derived from other columns (e.g., a column showing\n"
            "     the change or difference between two date columns, or a percentage change column).\n"
            "     For each computed column found, provide:\n"
            '     [{"label": "column header text as shown (e.g. chg)",\n'
            '       "formula": "difference" if it shows value_a - value_b, or '
            '"percent_change" if it shows (value_a - value_b) / value_b * 100,\n'
            '       "operands": [index_a, index_b] where indices reference sampled date columns '
            "using negative indexing (-1 = last date column, -2 = second-to-last, etc.)}]\n"
            "     Set to [] if no computed/derived columns are detected.\n"
            "   }\n"
            "   Set to null if no data table is visible.\n\n"
            "LAYOUT:\n"
            '19. "layout_description": detailed description of the overall layout, '
            "including where legends are placed, any special formatting, footnotes, "
            "source citations, or other visual elements.\n"
            '20. "background_color": hex color of the chart background\n\n'
            "IMPORTANT INSTRUCTIONS:\n"
            "- Be EXTREMELY precise with colors. Use exact hex codes.\n"
            "- Identify EVERY data series and its exact color.\n"
            "- Capture ALL horizontal reference lines (target lines, threshold lines).\n"
            "- Capture ALL vertical shaded bands (recession bands, highlight periods).\n"
            "- Capture ALL text annotations visible on the chart.\n"
            "- Note the exact y-axis range and formatting (%, whole numbers, decimals).\n"
            "- If legend text appears inline next to the data lines (not in a box), "
            'set legend_position to "inline".\n\n'
            "Return ONLY valid JSON, no markdown fences or explanation."
        )

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 16384,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": b64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        })

        try:
            response = await asyncio.to_thread(
                self._bedrock.invoke_model,
                modelId=self._vision_model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            raw_body = response["body"].read()
            if not raw_body:
                raise ValueError("Empty response from Bedrock Vision API")
            response_body = json.loads(raw_body)
            text_content = response_body["content"][0]["text"]
            logger.info("Vision API raw response (first 500 chars): %s", text_content[:500])

            # Strip markdown fences if present
            cleaned = text_content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines).strip()

            parsed = json.loads(cleaned)
        except json.JSONDecodeError as jexc:
            logger.error("Vision API returned non-JSON: %s", text_content[:500] if 'text_content' in dir() else "no content")
            raise ValueError(
                f"Bedrock Vision analysis failed — could not parse response as JSON: {jexc}"
            ) from jexc
        except Exception as exc:
            raise ValueError(
                f"Bedrock Vision analysis failed: {exc}"
            ) from exc

        return self._parse_vision_response(parsed)

    # -- Merge results ------------------------------------------------------

    def _merge_results(self, cv: OpenCVResult, vision: VisionResult) -> ChartSpecification:
        """Combine OpenCV and Vision results into a unified ``ChartSpecification``.

        Strategy:
        - Prefer Vision API colors (semantic understanding is more reliable for chart lines)
        - Use OpenCV colors only as fallback when Vision doesn't identify series
        - Pass through all Vision-extracted metadata (title, formatting, annotations, etc.)
        """
        # Build colour mappings: prefer Vision colors, fallback to OpenCV
        color_mappings: dict[str, str] = {}
        for entry in vision.legend_entries:
            color_mappings[entry.series_name] = entry.color

        # If no legend entries from Vision, use OpenCV colours
        if not color_mappings and cv.dominant_colors:
            for i, color in enumerate(cv.dominant_colors):
                color_mappings[f"series_{i}"] = color

        if not color_mappings:
            color_mappings["series_0"] = "#003B5C"

        # Derive legend layout
        layout_desc = vision.layout_description.lower()
        if "right" in layout_desc:
            legend_layout = LegendLayout(position="right", orientation="vertical")
        elif "left" in layout_desc:
            legend_layout = LegendLayout(position="left", orientation="vertical")
        elif "top" in layout_desc:
            legend_layout = LegendLayout(position="top", orientation="horizontal")
        elif "inline" in layout_desc or vision.legend_position == "inline":
            legend_layout = LegendLayout(position="bottom", orientation="horizontal")
        else:
            legend_layout = _DEFAULT_LEGEND_LAYOUT

        return ChartSpecification(
            chart_type=vision.chart_type,
            color_mappings=color_mappings,
            font_styles=FontStyles(
                title=FontSpec(family="Arial", size=vision.title_font_size, color=vision.title_color, weight="bold"),
                axis_label=FontSpec(family="Arial", size=12, color="#333333"),
                tick_label=FontSpec(family="Arial", size=vision.tick_font_size, color="#333333"),
                legend=FontSpec(family="Arial", size=11, color="#333333"),
                annotation=FontSpec(family="Arial", size=10, color="#333333"),
            ),
            axis_config=vision.axis_config,
            legend_layout=legend_layout,
            annotations=vision.annotations,
            data_table=vision.data_table,
            vertical_bands=[],
        )

    # -- Internal helpers ---------------------------------------------------

    @staticmethod
    def _extract_dominant_colors(img: np.ndarray, k: int = 5) -> list[str]:
        """Extract *k* dominant colours from *img* using k-means clustering.

        Returns a list of hex colour strings sorted by cluster frequency
        (most dominant first).
        """
        # Reshape to a flat list of pixels
        pixels = img.reshape(-1, 3).astype(np.float32)

        # Subsample for performance (max 10 000 pixels)
        if len(pixels) > 10_000:
            indices = np.random.default_rng(42).choice(len(pixels), 10_000, replace=False)
            pixels = pixels[indices]

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(
            pixels, k, None, criteria, 3, cv2.KMEANS_PP_CENTERS,
        )

        # Sort by frequency (most common first)
        _, counts = np.unique(labels, return_counts=True)
        order = np.argsort(-counts)
        sorted_centers = centers[order]

        hex_colors: list[str] = []
        for bgr in sorted_centers:
            b, g, r = int(bgr[0]), int(bgr[1]), int(bgr[2])
            # Filter out near-white (background) and near-black (text) colors
            if r > 230 and g > 230 and b > 230:
                continue
            if r < 30 and g < 30 and b < 30:
                continue
            hex_colors.append(f"#{r:02X}{g:02X}{b:02X}")

        return hex_colors

    @staticmethod
    def _extract_text_regions(img: np.ndarray) -> list[TextRegion]:
        """Detect text-like regions using morphological operations.

        Uses edge detection + dilation to find rectangular regions that
        likely contain text.  Returns bounding-box ``TextRegion`` objects
        (the ``text`` field is left as a placeholder since we don't run
        full OCR here).
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply adaptive threshold to highlight text
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2,
        )

        # Dilate to merge nearby text characters into blocks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[TextRegion] = []
        h_img, w_img = img.shape[:2]
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter: text regions are typically wider than tall and not too large
            aspect = w / max(h, 1)
            area_ratio = (w * h) / (w_img * h_img)
            if 1.5 < aspect < 30 and 0.0005 < area_ratio < 0.15:
                regions.append(TextRegion(
                    text="",  # placeholder — no OCR
                    x=float(x),
                    y=float(y),
                    width=float(w),
                    height=float(h),
                ))

        return regions

    @staticmethod
    def _extract_contours(img: np.ndarray) -> list[ContourInfo]:
        """Extract significant contours from the image.

        Filters out very small contours (noise) and very large ones
        (image border).  Returns ``ContourInfo`` objects with points,
        area, and average colour.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h_img, w_img = img.shape[:2]
        total_area = h_img * w_img
        min_area = total_area * 0.001
        max_area = total_area * 0.8

        results: list[ContourInfo] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            # Approximate contour to reduce point count
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            points = [[float(p[0][0]), float(p[0][1])] for p in approx]

            # Sample average colour inside the contour
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.drawContours(mask, [cnt], -1, 255, -1)
            mean_color = cv2.mean(img, mask=mask)[:3]  # BGR
            b, g, r = int(mean_color[0]), int(mean_color[1]), int(mean_color[2])
            hex_color = f"#{r:02X}{g:02X}{b:02X}"

            results.append(ContourInfo(
                points=points,
                area=float(area),
                color=hex_color,
            ))

        return results

    @staticmethod
    def _parse_vision_response(data: dict) -> VisionResult:
        """Parse the raw JSON dict from Bedrock Vision into a ``VisionResult``."""
        chart_type = data.get("chart_type", "line")
        if chart_type not in ("line", "bar", "mixed", "area"):
            chart_type = "line"

        raw_axis = data.get("axis_config", {})
        axis_config = AxisConfig(
            x_label=raw_axis.get("x_label") or "",
            y_label=raw_axis.get("y_label") or "",
            x_min=raw_axis.get("x_min"),
            x_max=raw_axis.get("x_max"),
            y_min=raw_axis.get("y_min"),
            y_max=raw_axis.get("y_max"),
        )

        legend_entries: list[LegendEntry] = []
        for entry in data.get("legend_entries", []):
            try:
                legend_entries.append(LegendEntry(
                    label=entry.get("label", ""),
                    color=entry.get("color", "#000000"),
                    series_name=entry.get("series_name", entry.get("label", "")),
                ))
            except Exception:
                continue

        annotations: list[AnnotationSpec] = []
        for ann in data.get("annotations", []):
            try:
                annotations.append(AnnotationSpec(
                    text=ann.get("text", ""),
                    x=float(ann.get("x", 0)),
                    y=float(ann.get("y", 0)),
                ))
            except Exception:
                continue

        data_table: DataTableSpec | None = None
        raw_dt = data.get("data_table")
        if raw_dt and isinstance(raw_dt, dict):
            computed_columns: list[ComputedColumnDefinition] = []
            for cc in raw_dt.get("computed_columns") or []:
                if not isinstance(cc, dict):
                    logger.warning("Skipping malformed computed_column entry (not a dict): %s", cc)
                    continue
                label = cc.get("label")
                formula = cc.get("formula")
                operands = cc.get("operands")
                if not label or not formula or operands is None:
                    logger.warning(
                        "Skipping malformed computed_column entry (missing fields): %s", cc,
                    )
                    continue
                try:
                    computed_columns.append(ComputedColumnDefinition(
                        label=label,
                        formula=formula,
                        operands=operands,
                    ))
                except Exception:
                    logger.warning("Skipping invalid computed_column entry: %s", cc)
                    continue

            data_table = DataTableSpec(
                columns=raw_dt.get("columns", []),
                visible=raw_dt.get("visible", False),
                font_size=raw_dt.get("font_size", 10),
                layout=raw_dt.get("layout", "transposed"),
                num_sampled_dates=raw_dt.get("num_sampled_dates"),
                series_shown=raw_dt.get("series_shown"),
                computed_columns=computed_columns,
            )

        return VisionResult(
            chart_type=chart_type,
            title=data.get("title") or "",
            title_font_size=data.get("title_font_size", 16),
            title_color=data.get("title_color") or "#003B5C",
            axis_config=axis_config,
            y_format=data.get("y_format") or "auto",
            axis_line_width=data.get("axis_line_width", 1.0),
            tick_font_size=data.get("tick_font_size", 10),
            legend_entries=legend_entries,
            legend_position=data.get("legend_position") or "inline",
            gridline_style=data.get("gridline_style") or "dashed",
            gridline_color=data.get("gridline_color") or "#D1D3D4",
            annotations=annotations,
            horizontal_lines=data.get("horizontal_lines", []),
            vertical_bands=data.get("vertical_bands", []),
            data_table=data_table,
            layout_description=data.get("layout_description") or "",
            background_color=data.get("background_color") or "#ffffff",
            series_line_widths=data.get("series_line_widths", []),
            series_line_styles=data.get("series_line_styles", []),
        )
