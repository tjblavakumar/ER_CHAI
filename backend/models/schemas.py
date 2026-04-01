"""Pydantic data models for the FRBSF Chart Builder application."""

from __future__ import annotations

from pydantic import BaseModel


# --- Config ---


class AppConfig(BaseModel):
    fred_api_key: str
    aws_region: str
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_vision_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"


# --- Data ---


class Observation(BaseModel):
    date: str  # ISO date
    value: float | None = None  # None for missing data points


class FREDDataset(BaseModel):
    series_id: str
    title: str
    units: str
    frequency: str
    observations: list[Observation]


# --- Image Analysis (supporting models) ---


class TextRegion(BaseModel):
    text: str
    x: float
    y: float
    width: float
    height: float


class ContourInfo(BaseModel):
    points: list[list[float]]  # list of [x, y] coordinate pairs
    area: float
    color: str  # hex color


class FontSpec(BaseModel):
    family: str
    size: int
    color: str
    weight: str = "normal"


class FontStyles(BaseModel):
    title: FontSpec
    axis_label: FontSpec
    tick_label: FontSpec
    legend: FontSpec
    annotation: FontSpec


class LegendEntry(BaseModel):
    label: str
    color: str
    series_name: str


class AnnotationSpec(BaseModel):
    text: str
    x: float
    y: float
    font_size: int = 10
    font_color: str = "#333333"


class DataTableSpec(BaseModel):
    columns: list[str]
    visible: bool = False
    font_size: int = 10


class AxisConfig(BaseModel):
    x_label: str = ""
    y_label: str = ""
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None


class LegendLayout(BaseModel):
    position: str  # "top", "bottom", "left", "right"
    orientation: str  # "horizontal", "vertical"


class VerticalBand(BaseModel):
    start_date: str
    end_date: str
    color: str
    opacity: float = 0.3


# --- Image Analysis ---


class OpenCVResult(BaseModel):
    dominant_colors: list[str]  # hex colors
    text_regions: list[TextRegion]
    contour_data: list[ContourInfo]


class VisionResult(BaseModel):
    chart_type: str  # "line", "bar", "mixed"
    axis_config: AxisConfig
    legend_entries: list[LegendEntry]
    annotations: list[AnnotationSpec]
    data_table: DataTableSpec | None = None
    layout_description: str


class ChartSpecification(BaseModel):
    chart_type: str
    color_mappings: dict[str, str]  # series_name -> hex color
    font_styles: FontStyles
    axis_config: AxisConfig
    legend_layout: LegendLayout
    annotations: list[AnnotationSpec]
    data_table: DataTableSpec | None = None
    vertical_bands: list[VerticalBand]


# --- Chart Configuration ---


class Position(BaseModel):
    x: float
    y: float


class ChartElementState(BaseModel):
    text: str
    font_family: str = "Arial"
    font_size: int = 14
    font_color: str = "#000000"
    position: Position


class AxesConfig(BaseModel):
    x_label: str
    y_label: str
    x_min: float | None = None
    x_max: float | None = None
    y_min: float | None = None
    y_max: float | None = None
    x_scale: str = "linear"  # "linear" | "logarithmic"
    y_scale: str = "linear"


class SeriesConfig(BaseModel):
    name: str
    column: str
    chart_type: str  # "line" | "bar"
    color: str  # hex
    line_width: float = 2.0
    visible: bool = True


class LegendConfig(BaseModel):
    visible: bool = True
    position: Position
    entries: list[LegendEntry]


class GridlineConfig(BaseModel):
    horizontal_visible: bool = True
    vertical_visible: bool = False
    style: str = "dashed"  # "solid" | "dashed" | "dotted"
    color: str = "#cccccc"


class AnnotationConfig(BaseModel):
    id: str
    type: str  # "text" | "vertical_band"
    text: str | None = None
    position: Position
    font_size: int = 10
    font_color: str = "#333333"
    band_start: str | None = None  # date for vertical bands
    band_end: str | None = None
    band_color: str | None = None


class DataTableConfig(BaseModel):
    visible: bool = False
    position: Position
    columns: list[str]
    font_size: int = 10


class ChartState(BaseModel):
    chart_type: str  # "line", "bar", "mixed"
    title: ChartElementState
    axes: AxesConfig
    series: list[SeriesConfig]
    legend: LegendConfig
    gridlines: GridlineConfig
    annotations: list[AnnotationConfig]
    data_table: DataTableConfig | None = None
    elements_positions: dict[str, Position]  # element_id -> {x, y}
    dataset_path: str
    dataset_columns: list[str]


# --- AI ---


class ChartContext(BaseModel):
    chart_state: ChartState
    dataset_summary: str  # column names, row count, date range, basic stats
    dataset_sample: list[dict]  # first N rows as dicts


class ChartConfigDelta(BaseModel):
    """Partial chart state update. Only non-None fields are applied."""

    chart_type: str | None = None
    title: ChartElementState | None = None
    axes: AxesConfig | None = None
    series: list[SeriesConfig] | None = None
    legend: LegendConfig | None = None
    gridlines: GridlineConfig | None = None
    annotations: list[AnnotationConfig] | None = None
    data_table: DataTableConfig | None = None


class AIResponse(BaseModel):
    type: str  # "chart_modify" | "data_qa"
    message: str  # text response to user
    chart_delta: ChartConfigDelta | None = None  # only for chart_modify


# --- Project ---


class Project(BaseModel):
    id: str  # UUID
    name: str
    created_at: str  # ISO datetime
    updated_at: str  # ISO datetime
    chart_state: ChartState
    dataset_path: str
    summary_text: str = ""


class ProjectCreate(BaseModel):
    name: str
    chart_state: ChartState
    dataset_path: str
    summary_text: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    chart_state: ChartState | None = None
    summary_text: str | None = None


class ProjectSummary(BaseModel):
    id: str
    name: str
    updated_at: str


# --- Ingestion ---


class DatasetInfo(BaseModel):
    columns: list[str]
    row_count: int
    date_range: str | None = None  # "2020-01-01 to 2024-01-01"
    source: str  # "fred" | "upload"


class IngestionResult(BaseModel):
    dataset_path: str
    chart_state: ChartState
    dataset_info: DatasetInfo


# --- Error ---


class ErrorResponse(BaseModel):
    error: str  # error code (e.g., "CONFIG_MISSING_KEY", "FRED_AUTH_ERROR")
    message: str  # human-readable description
    details: dict | None = None  # optional additional context
