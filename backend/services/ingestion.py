"""Data Ingestion Service for the FRBSF Chart Builder.

Handles downloading FRED data from URLs, parsing uploaded CSV/Excel files,
storing datasets locally, and generating default FRBSF-branded chart
specifications.
"""

from __future__ import annotations

import io
import logging
import os
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

from backend.models.schemas import (
    AnnotationConfig,
    AxesConfig,
    ChartElementState,
    ChartSpecification,
    ChartState,
    ComputedColumnDefinition,
    DatasetInfo,
    DataTableConfig,
    GridlineConfig,
    IngestionResult,
    LegendConfig,
    LegendEntry,
    Position,
    SeriesConfig,
)
from backend.services.fred_client import FREDClient
from backend.services.image_analyzer import ImageAnalyzer

# ---------------------------------------------------------------------------
# Constants – FRBSF default branding
# ---------------------------------------------------------------------------

DATA_DIR = "data"

# FRBSF brand palette
FRBSF_COLORS = [
    "#003B5C",  # FRBSF dark blue (primary)
    "#5B9BD5",  # FRBSF medium blue
    "#A5C8E1",  # FRBSF light blue
    "#6D6E71",  # FRBSF dark gray
    "#A7A9AC",  # FRBSF medium gray
    "#D1D3D4",  # FRBSF light gray
]

FRBSF_FONT_FAMILY = "Arial"
FRBSF_TITLE_FONT_SIZE = 16
FRBSF_AXIS_FONT_SIZE = 12
FRBSF_LEGEND_FONT_SIZE = 11
FRBSF_TITLE_COLOR = "#003B5C"
FRBSF_TEXT_COLOR = "#333333"
FRBSF_GRIDLINE_COLOR = "#D1D3D4"


# ---------------------------------------------------------------------------
# Data Ingestion Service
# ---------------------------------------------------------------------------


class DataIngestionService:
    """Orchestrates data ingestion from FRED URLs (and later file uploads)."""

    def __init__(
        self,
        fred_client: FREDClient,
        data_dir: str = DATA_DIR,
        image_analyzer: ImageAnalyzer | None = None,
    ) -> None:
        self._fred = fred_client
        self._data_dir = data_dir
        self._image_analyzer = image_analyzer

    # -- Public API ---------------------------------------------------------

    async def ingest_from_url(self, url: str, reference_image: object | None = None) -> IngestionResult:
        """Download FRED data from *url*, store locally, and generate a
        default FRBSF-branded chart specification.

        If *reference_image* is provided (a FastAPI ``UploadFile``), the
        image is analyzed with Vision AI and the detected styling is
        applied to the chart.

        Returns an ``IngestionResult`` containing the dataset path, a
        ready-to-render ``ChartState``, and dataset metadata.
        """
        series_id = FREDClient.parse_fred_url(url)
        dataset = await self._fred.download_series(series_id)

        # Build a DataFrame from the observations
        rows = [
            {"date": obs.date, "value": obs.value}
            for obs in dataset.observations
        ]
        df = pd.DataFrame(rows)

        # Persist to local file
        filename = f"{dataset.series_id.lower()}.csv"
        dataset_path = self._store_data(df, filename)

        # Compute date range
        dates = df["date"].dropna()
        date_range = (
            f"{dates.min()} to {dates.max()}" if len(dates) > 0 else None
        )

        dataset_info = DatasetInfo(
            columns=list(df.columns),
            row_count=len(df),
            date_range=date_range,
            source="fred",
        )

        chart_state = _build_default_chart_state(
            dataset=dataset,
            dataset_path=dataset_path,
            columns=list(df.columns),
            df=df,
        )

        # Apply reference image analysis if provided and analyzer is available
        if reference_image is not None and self._image_analyzer is not None:
            image_bytes: bytes = await reference_image.read()
            spec, vision_result = await self._image_analyzer.analyze(image_bytes)
            chart_state = _apply_image_spec_to_chart_state(chart_state, spec, df, vision_result)

        # Include actual data rows for frontend rendering
        dataset_rows = df.where(df.notna(), None).to_dict(orient="records")

        return IngestionResult(
            dataset_path=dataset_path,
            chart_state=chart_state,
            dataset_info=dataset_info,
            dataset_rows=dataset_rows,
        )

    async def ingest_from_file(
        self,
        file: object,
        reference_image: object | None = None,
    ) -> IngestionResult:
        """Parse an uploaded CSV/Excel file and generate a chart spec.

        *file* should be a FastAPI ``UploadFile`` (or any object with
        ``.filename`` and an async ``.read()`` method).

        Raises ``ValueError`` for unsupported formats or malformed data.
        """
        filename: str = getattr(file, "filename", "") or ""
        ext = os.path.splitext(filename)[1].lower()

        if ext not in (".csv", ".xlsx", ".xls"):
            raise ValueError(
                f"Unsupported file format: '{ext}'. "
                "Accepted formats: .csv, .xlsx, .xls"
            )

        content: bytes = await file.read()

        try:
            if ext == ".csv":
                df = self._parse_csv(content)
            else:
                df = self._parse_excel(content)
        except ValueError:
            raise  # re-raise our own descriptive errors
        except Exception as exc:
            raise ValueError(
                f"Failed to parse file '{filename}': {exc}"
            ) from exc

        if df.empty:
            raise ValueError(
                f"The uploaded file '{filename}' contains no data."
            )

        # Check for categorical grouped data first (before pivoting)
        categorical_info = _detect_categorical_data(df)

        if categorical_info is None:
            # Not categorical — try long-format pivot as before
            df = _detect_and_pivot_long_format(df)

        # Persist to local file (always store as CSV)
        safe_name = re.sub(r"[^\w\-.]", "_", os.path.splitext(filename)[0])
        stored_filename = f"{safe_name}.csv"
        dataset_path = self._store_data(df, stored_filename)

        # Detect date range if a date-like column exists
        date_range = _detect_date_range(df)

        dataset_info = DatasetInfo(
            columns=list(df.columns),
            row_count=len(df),
            date_range=date_range,
            source="upload",
        )

        if categorical_info is not None:
            chart_state = _build_categorical_chart_state(
                df=df,
                dataset_path=dataset_path,
                title=os.path.splitext(filename)[0],
                category_column=categorical_info["category_column"],
                group_column=categorical_info["group_column"],
                value_column=categorical_info["value_column"],
            )
        else:
            chart_state = _build_chart_state_from_df(
                df=df,
                dataset_path=dataset_path,
                title=os.path.splitext(filename)[0],
            )

        # Apply reference image analysis if provided and analyzer is available
        if reference_image is not None and self._image_analyzer is not None:
            image_bytes: bytes = await reference_image.read()
            spec, vision_result = await self._image_analyzer.analyze(image_bytes)
            chart_state = _apply_image_spec_to_chart_state(chart_state, spec, df, vision_result)

        # Include actual data rows for frontend rendering
        dataset_rows = df.where(df.notna(), None).to_dict(orient="records")

        return IngestionResult(
            dataset_path=dataset_path,
            chart_state=chart_state,
            dataset_info=dataset_info,
            dataset_rows=dataset_rows,
        )

    # -- File parsers -------------------------------------------------------

    def _parse_csv(self, content: bytes) -> pd.DataFrame:
        """Parse CSV bytes into a DataFrame.

        Raises ``ValueError`` on malformed / unparseable content.
        """
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise ValueError(f"Failed to parse CSV: {exc}") from exc
        return df

    def _parse_excel(self, content: bytes) -> pd.DataFrame:
        """Parse Excel (.xlsx / .xls) bytes into a DataFrame.

        Reads the first sheet.  Raises ``ValueError`` on malformed content.
        """
        try:
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)
        except Exception as exc:
            raise ValueError(f"Failed to parse Excel file: {exc}") from exc
        return df

    # -- Internal helpers ---------------------------------------------------

    def _store_data(self, df: pd.DataFrame, filename: str) -> str:
        """Persist *df* as a CSV file in the data directory.

        Creates the data directory if it does not exist.  Returns the
        relative file path (e.g. ``data/gdp.csv``).
        """
        os.makedirs(self._data_dir, exist_ok=True)
        path = os.path.join(self._data_dir, filename)
        df.to_csv(path, index=False)
        return path


# ---------------------------------------------------------------------------
# Default FRBSF-branded chart state builder
# ---------------------------------------------------------------------------


def _build_default_chart_state(
    *,
    dataset: object,
    dataset_path: str,
    columns: list[str],
    df: pd.DataFrame | None = None,
) -> ChartState:
    """Create a default FRBSF-branded ``ChartState`` from a FRED dataset."""
    from backend.models.schemas import FREDDataset

    assert isinstance(dataset, FREDDataset)

    primary_color = FRBSF_COLORS[0]

    # Compute y-axis range from actual data
    y_min_val: float | None = None
    y_max_val: float | None = None
    if df is not None and "value" in df.columns:
        numeric_vals = pd.to_numeric(df["value"], errors="coerce").dropna()
        if len(numeric_vals) > 0:
            y_min_val = float(numeric_vals.min())
            y_max_val = float(numeric_vals.max())
            # Add 5% padding
            y_range = y_max_val - y_min_val
            if y_range > 0:
                y_min_val -= y_range * 0.05
                y_max_val += y_range * 0.05

    title = ChartElementState(
        text=dataset.title,
        font_family=FRBSF_FONT_FAMILY,
        font_size=FRBSF_TITLE_FONT_SIZE,
        font_color=FRBSF_TITLE_COLOR,
        position=Position(x=50, y=10),
    )

    axes = AxesConfig(
        x_label="Date",
        y_label=dataset.units or "Value",
        x_scale="linear",
        y_scale="linear",
        y_min=y_min_val,
        y_max=y_max_val,
    )

    series = [
        SeriesConfig(
            name=dataset.series_id,
            column="value",
            chart_type="line",
            color=primary_color,
            line_width=2.0,
            visible=True,
        )
    ]

    legend_entries = [
        LegendEntry(
            label=dataset.title,
            color=primary_color,
            series_name=dataset.series_id,
        )
    ]

    legend = LegendConfig(
        visible=True,
        position=Position(x=50, y=40),
        entries=legend_entries,
    )

    gridlines = GridlineConfig(
        horizontal_visible=True,
        vertical_visible=False,
        style="dashed",
        color=FRBSF_GRIDLINE_COLOR,
    )

    elements_positions: dict[str, Position] = {
        "title": Position(x=50, y=10),
        "legend": Position(x=50, y=40),
        "x_axis_label": Position(x=300, y=450),
        "y_axis_label": Position(x=10, y=250),
    }

    return ChartState(
        chart_type="line",
        title=title,
        axes=axes,
        series=series,
        legend=legend,
        gridlines=gridlines,
        annotations=[],
        data_table=None,
        elements_positions=elements_positions,
        dataset_path=dataset_path,
        dataset_columns=columns,
    )


# ---------------------------------------------------------------------------
# Helpers for file-based ingestion
# ---------------------------------------------------------------------------


def _detect_date_range(df: pd.DataFrame) -> str | None:
    """Try to detect a date range from the first column that looks date-like."""
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors="coerce", format="mixed").dropna()
            if len(dates) > 0:
                return f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
        except Exception:
            continue
    return None


def _detect_and_pivot_long_format(df: pd.DataFrame) -> pd.DataFrame:
    """Detect if a DataFrame is in long format (date, key, value) and pivot to wide.

    Long format indicators:
    - Has a date-like column
    - Has a string/category column with repeated values (the key/series identifier)
    - Has a numeric value column

    If detected, pivots to wide format with date as index and each unique key as a column.
    Otherwise returns the DataFrame unchanged.
    """
    cols = list(df.columns)
    if len(cols) < 3:
        return df

    # Find ALL date columns, key column candidates, and value column candidates
    date_cols = []
    key_candidates = []
    value_candidates = []

    for col in cols:
        # Check if it's a date column (only string columns can be dates)
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
                if parsed.notna().sum() > len(df) * 0.5:
                    date_cols.append(col)
                    continue
            except Exception:
                pass
            # Not a date — check if it's a key candidate
            nunique = df[col].nunique()
            if 1 < nunique <= len(df) * 0.5:
                key_candidates.append((col, nunique))
        elif pd.api.types.is_numeric_dtype(df[col]):
            value_candidates.append(col)

    if not date_cols or not key_candidates or not value_candidates:
        return df

    # Prefer the actual date column: columns named "date" over others
    date_col = date_cols[0]
    for dc in date_cols:
        if dc.lower() in ("date", "dates", "observation_date"):
            date_col = dc
            break

    # Prefer value columns named "value", "values", "amount", "count"
    _PREFERRED_VALUE_NAMES = {"value", "values", "amount", "count", "rate", "pct"}
    value_col = value_candidates[0]
    for vc in value_candidates:
        if vc.lower() in _PREFERRED_VALUE_NAMES:
            value_col = vc
            break

    # Prefer key columns named "variable", "key", "series", etc.
    _PREFERRED_KEY_NAMES = {"variable", "key", "series", "category", "name", "type", "group", "indicator"}
    key_col = key_candidates[0][0]
    for kc, _ in key_candidates:
        if kc.lower() in _PREFERRED_KEY_NAMES:
            key_col = kc
            break
    if key_col == key_candidates[0][0] and len(key_candidates) > 1:
        key_candidates.sort(key=lambda x: x[1])
        key_col = key_candidates[0][0]

    # Pivot: date as index, key values become columns, values fill the cells
    try:
        pivoted = df.pivot_table(
            index=date_col, columns=key_col, values=value_col, aggfunc="first"
        ).reset_index()
        pivoted.columns.name = None
        pivoted = pivoted.sort_values(date_col).reset_index(drop=True)
        return pivoted
    except Exception:
        return df


def _detect_categorical_data(df: pd.DataFrame) -> dict | None:
    """Detect if a DataFrame represents categorical grouped data.

    Categorical data indicators:
    - Has a category column (string, few unique values, e.g., "Energy", "Food")
    - Has a group/period column (string, few unique values, e.g., "12-month", "6-month")
    - Has a numeric value column
    - Does NOT have a date column (or the "period" column is not parseable as dates)
    - The category × group combination should cover most rows (they form a grid)

    Returns a dict with {category_column, group_column, value_column} if detected,
    or None if the data is not categorical.
    """
    cols = list(df.columns)
    if len(cols) < 3:
        return None

    # Find all string columns and numeric columns
    string_cols = []
    numeric_cols = []
    date_col_found = False

    for col in cols:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
            continue
        if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            # Check if it's a date column
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
                if parsed.notna().sum() > len(df) * 0.5:
                    date_col_found = True
                    continue
            except Exception:
                pass
            string_cols.append(col)

    # Need at least 2 string columns and 1 numeric column, and no date column
    if date_col_found or len(string_cols) < 2 or len(numeric_cols) < 1:
        return None

    value_col = numeric_cols[0]

    # Find the best (category, group) pair: the combination that best covers
    # the rows (category × group ≈ total rows) and forms a grid structure.
    best_pair = None
    best_score = -1

    for i, col_a in enumerate(string_cols):
        n_a = df[col_a].nunique()
        if n_a < 2 or n_a > len(df) * 0.6:
            continue
        for col_b in string_cols[i + 1:]:
            n_b = df[col_b].nunique()
            if n_b < 2 or n_b > len(df) * 0.6:
                continue
            # Check if the combination covers most rows
            combo_count = df.groupby([col_a, col_b]).size().shape[0]
            expected = n_a * n_b
            coverage = combo_count / max(len(df), 1)
            grid_fit = combo_count / max(expected, 1)
            # Score: high coverage + good grid fit + prefer more groups (richer chart)
            score = coverage * grid_fit * (n_a + n_b)
            if score > best_score:
                best_score = score
                # Category = fewer unique values, group = more unique values
                if n_a <= n_b:
                    best_pair = (col_a, col_b)
                else:
                    best_pair = (col_b, col_a)

    if best_pair is None or best_score < 0.5:
        return None

    return {
        "category_column": best_pair[0],
        "group_column": best_pair[1],
        "value_column": value_col,
    }


def _compute_derived_value(
    formula: str,
    operand_values: list[float | None],
) -> float | None:
    """Compute a derived value from operand values using the given formula.

    Supports "difference" (a - b) and "percent_change" ((a - b) / b * 100).
    Returns None for division by zero, missing operands, or unrecognized formulas.
    """
    if formula == "difference":
        if len(operand_values) < 2:
            return None
        a, b = operand_values[0], operand_values[1]
        if a is None or b is None:
            return None
        return a - b
    elif formula == "percent_change":
        if len(operand_values) < 2:
            return None
        a, b = operand_values[0], operand_values[1]
        if a is None or b is None:
            return None
        if b == 0:
            return None
        return (a - b) / b * 100
    else:
        return None


def _build_chart_state_from_df(
    *,
    df: pd.DataFrame,
    dataset_path: str,
    title: str,
) -> ChartState:
    """Create a default FRBSF-branded ``ChartState`` from an uploaded DataFrame.

    Picks the first numeric column as the data series and uses the first
    column as the x-axis label (assumed to be a date or category).
    """
    columns = list(df.columns)
    numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]

    # Determine x-axis label from the first non-numeric column, or fallback
    non_numeric_cols = [c for c in columns if c not in numeric_cols]
    x_label = non_numeric_cols[0] if non_numeric_cols else (columns[0] if columns else "Index")

    # Build series configs for each numeric column (up to palette size)
    series: list[SeriesConfig] = []
    legend_entries: list[LegendEntry] = []
    for i, col in enumerate(numeric_cols[: len(FRBSF_COLORS)]):
        color = FRBSF_COLORS[i]
        series.append(
            SeriesConfig(
                name=col,
                column=col,
                chart_type="line",
                color=color,
                line_width=2.0,
                visible=True,
            )
        )
        legend_entries.append(
            LegendEntry(label=col, color=color, series_name=col)
        )

    # If no numeric columns, create a placeholder series from the first column
    if not series and columns:
        series.append(
            SeriesConfig(
                name=columns[0],
                column=columns[0],
                chart_type="line",
                color=FRBSF_COLORS[0],
                line_width=2.0,
                visible=True,
            )
        )
        legend_entries.append(
            LegendEntry(label=columns[0], color=FRBSF_COLORS[0], series_name=columns[0])
        )

    title_element = ChartElementState(
        text=title,
        font_family=FRBSF_FONT_FAMILY,
        font_size=FRBSF_TITLE_FONT_SIZE,
        font_color=FRBSF_TITLE_COLOR,
        position=Position(x=50, y=10),
    )

    axes = AxesConfig(
        x_label=x_label,
        y_label=numeric_cols[0] if len(numeric_cols) == 1 else "Value",
        x_scale="linear",
        y_scale="linear",
        y_min=float(df[numeric_cols].min(skipna=True).min()) if numeric_cols and not pd.isna(df[numeric_cols].min().min()) else None,
        y_max=float(df[numeric_cols].max(skipna=True).max()) if numeric_cols and not pd.isna(df[numeric_cols].max().max()) else None,
    )

    legend = LegendConfig(
        visible=True,
        position=Position(x=50, y=40),
        entries=legend_entries,
    )

    gridlines = GridlineConfig(
        horizontal_visible=True,
        vertical_visible=False,
        style="dashed",
        color=FRBSF_GRIDLINE_COLOR,
    )

    elements_positions: dict[str, Position] = {
        "title": Position(x=50, y=10),
        "legend": Position(x=50, y=40),
        "x_axis_label": Position(x=300, y=450),
        "y_axis_label": Position(x=10, y=250),
    }

    data_table = DataTableConfig(
        visible=True,
        position=Position(x=70, y=490),
        columns=numeric_cols,
        font_size=10,
        max_rows=5,
    )

    return ChartState(
        chart_type="line",
        title=title_element,
        axes=axes,
        series=series,
        legend=legend,
        gridlines=gridlines,
        annotations=[],
        data_table=data_table,
        elements_positions=elements_positions,
        dataset_path=dataset_path,
        dataset_columns=columns,
    )


def _build_categorical_chart_state(
    *,
    df: pd.DataFrame,
    dataset_path: str,
    title: str,
    category_column: str,
    group_column: str,
    value_column: str,
) -> ChartState:
    """Build a chart state for categorical grouped bar chart data.

    The data has a category column (e.g., "Energy", "Food"), a group column
    (e.g., "12-month", "6-month"), and a value column. The chart groups bars
    by category with sub-bars for each group.
    """
    columns = list(df.columns)
    categories = df[category_column].unique().tolist()
    groups = df[group_column].unique().tolist()

    # Clean up category names (remove newlines)
    clean_categories = [re.sub(r"[\r\n]+", " ", str(c)).strip() for c in categories]

    # Build one series per group (each group gets a color)
    series: list[SeriesConfig] = []
    legend_entries: list[LegendEntry] = []
    for i, group in enumerate(groups):
        color = FRBSF_COLORS[i % len(FRBSF_COLORS)]
        group_name = re.sub(r"[\r\n]+", " ", str(group)).strip()
        series.append(
            SeriesConfig(
                name=group_name,
                column=group_name,
                chart_type="bar",
                color=color,
                line_width=2.0,
                visible=True,
            )
        )
        legend_entries.append(
            LegendEntry(label=group_name, color=color, series_name=group_name)
        )

    # Compute y-axis range
    numeric_vals = pd.to_numeric(df[value_column], errors="coerce").dropna()
    y_min_val = float(numeric_vals.min()) if len(numeric_vals) > 0 else 0
    y_max_val = float(numeric_vals.max()) if len(numeric_vals) > 0 else 100
    y_range = y_max_val - y_min_val
    if y_range > 0:
        y_min_val -= y_range * 0.05
        y_max_val += y_range * 0.05
    # If there are negative values, ensure y_min includes them
    if y_min_val > 0:
        y_min_val = 0

    title_element = ChartElementState(
        text=title,
        font_family=FRBSF_FONT_FAMILY,
        font_size=FRBSF_TITLE_FONT_SIZE,
        font_color=FRBSF_TITLE_COLOR,
        position=Position(x=50, y=10),
    )

    axes = AxesConfig(
        x_label=re.sub(r"[\r\n]+", " ", category_column).strip(),
        y_label=re.sub(r"[\r\n]+", " ", value_column).strip(),
        x_scale="linear",
        y_scale="linear",
        y_min=y_min_val,
        y_max=y_max_val,
    )

    legend = LegendConfig(
        visible=True,
        position=Position(x=50, y=40),
        entries=legend_entries,
    )

    gridlines = GridlineConfig(
        horizontal_visible=True,
        vertical_visible=False,
        style="dashed",
        color=FRBSF_GRIDLINE_COLOR,
    )

    elements_positions: dict[str, Position] = {
        "title": Position(x=50, y=10),
        "legend": Position(x=50, y=40),
        "x_axis_label": Position(x=300, y=450),
        "y_axis_label": Position(x=10, y=250),
    }

    return ChartState(
        chart_type="bar",
        title=title_element,
        axes=axes,
        series=series,
        legend=legend,
        gridlines=gridlines,
        annotations=[],
        data_table=None,
        elements_positions=elements_positions,
        dataset_path=dataset_path,
        dataset_columns=columns,
        bar_grouping="by_category",
        category_column=category_column,
        group_column=group_column,
    )


def _apply_image_spec_to_chart_state(
    chart_state: ChartState,
    spec: ChartSpecification,
    df: pd.DataFrame,
    vision: object | None = None,
) -> ChartState:
    """Merge image analysis results into an existing ``ChartState``.

    Applies extracted colors, chart type, axis config, legend layout,
    annotations, horizontal lines, vertical bands, y_format, gridlines,
    and font styles from the image analysis.
    """
    from backend.models.schemas import VisionResult as VR

    vision_result: VR | None = vision if isinstance(vision, VR) else None

    # Chart type
    chart_type = spec.chart_type or chart_state.chart_type

    # Apply colors and line widths from spec to existing series
    series: list[SeriesConfig] = []
    color_list = list(spec.color_mappings.values())
    line_widths = vision_result.series_line_widths if vision_result else []
    for i, s in enumerate(chart_state.series):
        color = color_list[i] if i < len(color_list) else s.color
        lw = line_widths[i] if i < len(line_widths) else s.line_width
        series.append(SeriesConfig(
            name=s.name,
            column=s.column,
            chart_type=chart_type if chart_type != "mixed" else s.chart_type,
            color=color,
            line_width=lw,
            visible=s.visible,
        ))

    # Axis config
    y_format = vision_result.y_format if vision_result else "auto"
    axis_lw = vision_result.axis_line_width if vision_result else 1.0
    tick_fs = vision_result.tick_font_size if vision_result else 10

    # Y-axis range: use Vision AI values only if compatible with actual data
    # Vision AI often misreads scale (e.g., returns 0.12 when data has 12.0)
    vision_y_min = spec.axis_config.y_min
    vision_y_max = spec.axis_config.y_max
    data_y_min = chart_state.axes.y_min
    data_y_max = chart_state.axes.y_max
    use_y_min = data_y_min
    use_y_max = data_y_max
    if (vision_y_min is not None and vision_y_max is not None
            and data_y_min is not None and data_y_max is not None):
        data_range = abs(data_y_max - data_y_min) or 1
        vision_range = abs(vision_y_max - vision_y_min) or 1
        # If ranges differ by more than 10x, Vision AI likely misread the scale
        if 0.1 <= vision_range / data_range <= 10:
            use_y_min = vision_y_min
            use_y_max = vision_y_max

    axes = AxesConfig(
        x_label=spec.axis_config.x_label or chart_state.axes.x_label,
        y_label=spec.axis_config.y_label or chart_state.axes.y_label,
        x_min=spec.axis_config.x_min if spec.axis_config.x_min is not None else chart_state.axes.x_min,
        x_max=spec.axis_config.x_max if spec.axis_config.x_max is not None else chart_state.axes.x_max,
        y_min=use_y_min,
        y_max=use_y_max,
        x_scale=chart_state.axes.x_scale,
        y_scale=chart_state.axes.y_scale,
        y_format=y_format,
        line_width=axis_lw,
        tick_font_size=tick_fs,
    )

    # Legend
    legend_position = chart_state.legend.position
    updated_legend_entries: list[LegendEntry] = []
    for i, entry in enumerate(chart_state.legend.entries):
        color = color_list[i] if i < len(color_list) else entry.color
        updated_legend_entries.append(LegendEntry(
            label=entry.label,
            color=color,
            series_name=entry.series_name,
        ))
    legend = LegendConfig(
        visible=chart_state.legend.visible,
        position=legend_position,
        entries=updated_legend_entries,
    )

    # Annotations: text annotations from image spec
    annotations: list[AnnotationConfig] = list(chart_state.annotations)
    for i, ann_spec in enumerate(spec.annotations):
        annotations.append(AnnotationConfig(
            id=f"img_ann_{i}",
            type="text",
            text=ann_spec.text,
            position=Position(x=ann_spec.x, y=ann_spec.y),
            font_size=ann_spec.font_size,
            font_color=ann_spec.font_color,
        ))

    # Horizontal lines from Vision
    if vision_result:
        for i, hl in enumerate(vision_result.horizontal_lines):
            if isinstance(hl, dict):
                annotations.append(AnnotationConfig(
                    id=f"img_hline_{i}",
                    type="horizontal_line",
                    text=hl.get("label", ""),
                    position=Position(x=0, y=0),
                    font_size=10,
                    font_color=hl.get("color", "#cc0000"),
                    line_value=hl.get("value"),
                    line_color=hl.get("color", "#cc0000"),
                    line_style=hl.get("style", "dotted"),
                    line_width=1.5,
                ))

        # Vertical bands from Vision
        for i, vb in enumerate(vision_result.vertical_bands):
            if isinstance(vb, dict):
                annotations.append(AnnotationConfig(
                    id=f"img_vband_{i}",
                    type="vertical_band",
                    text=None,
                    position=Position(x=200 + i * 80, y=0),
                    font_size=10,
                    font_color="#333333",
                    band_start=vb.get("start"),
                    band_end=vb.get("end"),
                    band_color=vb.get("color", "#cccccc"),
                ))

    # Gridlines from Vision
    gridline_style = vision_result.gridline_style if vision_result else chart_state.gridlines.style
    gridline_color = vision_result.gridline_color if vision_result else chart_state.gridlines.color
    gridlines = GridlineConfig(
        horizontal_visible=gridline_style != "none",
        vertical_visible=chart_state.gridlines.vertical_visible,
        style=gridline_style if gridline_style != "none" else "dashed",
        color=gridline_color,
    )

    # Title from Vision
    title_text = vision_result.title if vision_result and vision_result.title else chart_state.title.text
    title = ChartElementState(
        text=title_text,
        font_family=spec.font_styles.title.family,
        font_size=spec.font_styles.title.size if spec.font_styles.title.size > 0 else 16,
        font_color=spec.font_styles.title.color,
        position=chart_state.title.position,
    )

    # Data table — always use actual DataFrame numeric column names for value lookups
    numeric_only_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    data_table = chart_state.data_table
    if spec.data_table is not None:
        max_rows = spec.data_table.num_sampled_dates if spec.data_table.num_sampled_dates else 5
        data_table = DataTableConfig(
            visible=spec.data_table.visible,
            position=chart_state.data_table.position if chart_state.data_table else Position(x=70, y=490),
            columns=numeric_only_cols,
            font_size=spec.data_table.font_size,
            max_rows=max_rows,
        )

        # Computed column processing
        if spec.data_table.computed_columns:
            data_table.computed_columns = list(spec.data_table.computed_columns)

            # Compute sampled indices (same logic as frontend DataTableElement)
            total_rows = len(df)
            count = min(data_table.max_rows, total_rows)
            if count <= 0:
                sampled_indices: list[int] = []
            else:
                # Use the last N rows (most recent dates)
                start_idx = total_rows - count
                sampled_indices = list(range(start_idx, total_rows))

            computed_values: dict[str, float | None] = {}
            for series_col in numeric_only_cols:
                for cc in spec.data_table.computed_columns:
                    # Resolve operand indices (negative indices reference from end of sampled_indices)
                    operand_values: list[float | None] = []
                    for op_idx in cc.operands:
                        # Resolve negative index relative to sampled_indices
                        resolved = op_idx if op_idx >= 0 else len(sampled_indices) + op_idx
                        if 0 <= resolved < len(sampled_indices):
                            row_idx = sampled_indices[resolved]
                            if 0 <= row_idx < total_rows:
                                val = df[series_col].iloc[row_idx]
                                if pd.isna(val):
                                    operand_values.append(None)
                                else:
                                    operand_values.append(float(val))
                            else:
                                operand_values.append(None)
                        else:
                            operand_values.append(None)

                    result = _compute_derived_value(cc.formula, operand_values)
                    # Sanitize NaN to None for JSON compliance
                    if result is not None and pd.isna(result):
                        result = None
                    computed_values[f"{series_col}:{cc.label}"] = result

            data_table.computed_values = computed_values

    elif data_table is None:
        data_table = DataTableConfig(
            visible=True,
            position=Position(x=70, y=490),
            columns=numeric_only_cols,
            font_size=10,
            max_rows=5,
        )

    return ChartState(
        chart_type=chart_type,
        title=title,
        axes=axes,
        series=series,
        legend=legend,
        gridlines=gridlines,
        annotations=annotations,
        data_table=data_table,
        elements_positions=chart_state.elements_positions,
        dataset_path=chart_state.dataset_path,
        dataset_columns=chart_state.dataset_columns,
        bar_grouping=chart_state.bar_grouping,
        category_column=chart_state.category_column,
        group_column=chart_state.group_column,
    )
