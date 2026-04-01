"""Data Ingestion Service for the FRBSF Chart Builder.

Handles downloading FRED data from URLs, parsing uploaded CSV/Excel files,
storing datasets locally, and generating default FRBSF-branded chart
specifications.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path

import pandas as pd

from backend.models.schemas import (
    AnnotationConfig,
    AxesConfig,
    ChartElementState,
    ChartState,
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

    def __init__(self, fred_client: FREDClient, data_dir: str = DATA_DIR) -> None:
        self._fred = fred_client
        self._data_dir = data_dir

    # -- Public API ---------------------------------------------------------

    async def ingest_from_url(self, url: str) -> IngestionResult:
        """Download FRED data from *url*, store locally, and generate a
        default FRBSF-branded chart specification.

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
        )

        return IngestionResult(
            dataset_path=dataset_path,
            chart_state=chart_state,
            dataset_info=dataset_info,
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

        chart_state = _build_chart_state_from_df(
            df=df,
            dataset_path=dataset_path,
            title=os.path.splitext(filename)[0],
        )

        return IngestionResult(
            dataset_path=dataset_path,
            chart_state=chart_state,
            dataset_info=dataset_info,
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
) -> ChartState:
    """Create a default FRBSF-branded ``ChartState`` from a FRED dataset.

    Uses line chart, FRBSF blue palette, proper axis labels derived from
    the dataset metadata, default legend, gridlines, and title.
    """
    from backend.models.schemas import FREDDataset  # local to avoid circular at module level

    assert isinstance(dataset, FREDDataset)

    primary_color = FRBSF_COLORS[0]

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
            dates = pd.to_datetime(df[col], errors="coerce").dropna()
            if len(dates) > 0:
                return f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
        except Exception:
            continue
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
        y_label=numeric_cols[0] if numeric_cols else "Value",
        x_scale="linear",
        y_scale="linear",
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
        chart_type="line",
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
    )
