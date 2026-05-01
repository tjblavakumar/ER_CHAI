"""US recession periods loaded from recession_config.yaml.

Reads user-editable recession periods and generates vertical-band
annotations for any that overlap the chart's data range.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from backend.models.schemas import AnnotationConfig, Position

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config file path — sits at the project root next to config.yaml
# ---------------------------------------------------------------------------

_CONFIG_FILENAME = "recession_config.yaml"

# Search order: project root (cwd), then relative to this file's package
_SEARCH_PATHS = [
    Path(_CONFIG_FILENAME),                          # project root
    Path(__file__).resolve().parent.parent.parent / _CONFIG_FILENAME,  # repo root
]

DEFAULT_BAND_COLOR = "#d3d3d3"


def _load_config() -> tuple[list[dict], str]:
    """Load recession periods from recession_config.yaml.

    Returns (list of recession dicts, band_color).
    Each dict has keys: start, end, label (optional).
    """
    for path in _SEARCH_PATHS:
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    logger.warning("recession_config.yaml has unexpected format, skipping.")
                    return [], DEFAULT_BAND_COLOR
                band_color = data.get("band_color", DEFAULT_BAND_COLOR)
                recessions = data.get("recessions", [])
                if not isinstance(recessions, list):
                    logger.warning("recession_config.yaml 'recessions' is not a list, skipping.")
                    return [], band_color
                logger.info("Loaded %d recession period(s) from %s", len(recessions), path)
                return recessions, band_color
            except Exception as exc:
                logger.warning("Failed to read recession_config.yaml: %s", exc)
                return [], DEFAULT_BAND_COLOR

    logger.info("No recession_config.yaml found, recession bands disabled.")
    return [], DEFAULT_BAND_COLOR


def build_recession_annotations(
    df: pd.DataFrame,
    existing_annotations: list[AnnotationConfig] | None = None,
) -> list[AnnotationConfig]:
    """Return vertical-band annotations for recessions that overlap the data's date range.

    Scans the DataFrame for a date-like column, determines the data's time
    span, and creates a vertical band for each recession period that overlaps.

    Parameters
    ----------
    df : pd.DataFrame
        The dataset. The first parseable date column is used.
    existing_annotations : list[AnnotationConfig] | None
        Any annotations already present (returned unchanged alongside new ones).

    Returns
    -------
    list[AnnotationConfig]
        Combined list of existing + recession band annotations.
    """
    result = list(existing_annotations or [])

    recessions, band_color = _load_config()
    if not recessions:
        return result

    # Find the date column and parse it
    date_series: pd.Series | None = None
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            if parsed.notna().sum() > len(df) * 0.5:
                date_series = parsed.dropna()
                break
        except Exception:
            continue

    if date_series is None or len(date_series) == 0:
        return result

    data_start = date_series.min()
    data_end = date_series.max()

    for i, entry in enumerate(recessions):
        if not isinstance(entry, dict):
            continue
        rec_start_str = str(entry.get("start", ""))
        rec_end_str = str(entry.get("end", ""))
        label = entry.get("label") or None  # treat empty string as None

        if not rec_start_str or not rec_end_str:
            continue

        try:
            rec_start = datetime.strptime(rec_start_str, "%Y-%m-%d")
            rec_end = datetime.strptime(rec_end_str, "%Y-%m-%d")
        except ValueError:
            logger.warning("Skipping recession entry %d: invalid date format.", i)
            continue

        # Check overlap: recession overlaps data range
        if rec_end < data_start or rec_start > data_end:
            continue

        # Clamp to data range for cleaner display
        band_start = max(rec_start, data_start).strftime("%Y-%m-%d")
        band_end = min(rec_end, data_end).strftime("%Y-%m-%d")

        result.append(
            AnnotationConfig(
                id=f"recession_{i}",
                type="vertical_band",
                text=label,
                position=Position(x=0, y=0),
                font_size=14,
                font_color="#666666",
                band_start=band_start,
                band_end=band_end,
                band_color=band_color,
            )
        )

    added = len(result) - len(existing_annotations or [])
    if added > 0:
        logger.info("Added %d recession shading band(s) to chart.", added)

    return result
