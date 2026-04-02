"""Bug condition exploration tests for data table column filtering and vision extraction.

This test demonstrates two bugs:

Bug 1: `_build_chart_state_from_df` sets `DataTableConfig.columns` to ALL DataFrame
columns (including the date column), causing the date column to appear as a data row
in the transposed data table.

Bug 2: `_parse_vision_response` only extracts `columns`, `visible`, and `font_size`
into `DataTableSpec`, missing structural fields like `layout`, `num_sampled_dates`,
and `series_shown` that vary per chart.

**Validates: Requirements 1.1, 1.3, 2.1, 2.3**

EXPECTED OUTCOME: These tests FAIL on unfixed code — failure proves the bugs exist.
"""

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.models.schemas import DataTableSpec
from backend.services.image_analyzer import ImageAnalyzer
from backend.services.ingestion import _build_chart_state_from_df


# ---------------------------------------------------------------------------
# Bug 1 — Column filtering in _build_chart_state_from_df
# ---------------------------------------------------------------------------


class TestDataTableColumnFiltering:
    """Bug Condition: Date column included in DataTableConfig.columns.

    The bug is that `_build_chart_state_from_df` sets `columns=columns`
    (all DataFrame columns) instead of `columns=numeric_cols`, causing
    the date/non-numeric column to appear in the data table.
    """

    def test_date_column_excluded_from_data_table(self):
        """Date column must NOT appear in data_table.columns.

        **Validates: Requirements 1.1, 2.1**

        On unfixed code, data_table.columns will be ["date", "PCE", "Core PCE"]
        instead of the expected ["PCE", "Core PCE"].
        """
        df = pd.DataFrame({
            "date": ["2020-01", "2020-02", "2020-03"],
            "PCE": [1.5, 1.6, 1.7],
            "Core PCE": [1.3, 1.4, 1.5],
        })

        result = _build_chart_state_from_df(
            df=df, dataset_path="data/test.csv", title="Test"
        )

        assert result.data_table is not None, "data_table should not be None"
        assert "date" not in result.data_table.columns, (
            f"data_table.columns should NOT contain 'date' but got {result.data_table.columns}. "
            "The date column is incorrectly included because columns=columns passes all columns."
        )
        assert result.data_table.columns == ["PCE", "Core PCE"], (
            f"data_table.columns should be ['PCE', 'Core PCE'] but got {result.data_table.columns}"
        )

    @given(
        num_numeric=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=20)
    def test_property_only_numeric_columns_in_data_table(self, num_numeric: int):
        """Property: For any DataFrame with a date column + numeric columns,
        data_table.columns contains ONLY the numeric column names.

        **Validates: Requirements 1.1, 2.1**

        Bug Condition: isBugCondition(input) where dateColumnsIncluded is true.
        """
        numeric_col_names = [f"series_{i}" for i in range(num_numeric)]
        data = {"date": [f"2020-{m:02d}" for m in range(1, 4)]}
        for col in numeric_col_names:
            data[col] = [1.0, 2.0, 3.0]

        df = pd.DataFrame(data)

        result = _build_chart_state_from_df(
            df=df, dataset_path="data/test.csv", title="Test"
        )

        assert result.data_table is not None
        for col in result.data_table.columns:
            assert col != "date", (
                f"data_table.columns contains 'date' but should only have numeric columns. "
                f"Got: {result.data_table.columns}, Expected: {numeric_col_names}"
            )


# ---------------------------------------------------------------------------
# Bug 2 — Vision extraction completeness
# ---------------------------------------------------------------------------


class TestVisionExtractionCompleteness:
    """Bug Condition: DataTableSpec lacks layout, num_sampled_dates, series_shown.

    The bug is that `_parse_vision_response` only extracts `columns`, `visible`,
    and `font_size` from the vision response, ignoring structural fields that
    vary per chart.
    """

    def test_vision_data_table_has_layout_field(self):
        """Parsed DataTableSpec must have a `layout` attribute.

        **Validates: Requirements 1.3, 2.3**

        On unfixed code, DataTableSpec has no `layout` field, so this will fail.
        """
        data = {
            "chart_type": "line",
            "title": "Test Chart",
            "axis_config": {"x_label": "Date", "y_label": "Value"},
            "legend_entries": [],
            "annotations": [],
            "data_table": {
                "columns": ["PCE"],
                "visible": True,
                "font_size": 10,
                "layout": "transposed",
                "num_sampled_dates": 5,
                "series_shown": ["PCE"],
            },
            "layout_description": "",
        }

        result = ImageAnalyzer._parse_vision_response(data)

        assert result.data_table is not None, "data_table should not be None"
        assert hasattr(result.data_table, "layout"), (
            "DataTableSpec should have a 'layout' attribute but it doesn't. "
            "The vision extraction is incomplete."
        )
        assert result.data_table.layout == "transposed", (
            f"DataTableSpec.layout should be 'transposed' but got {getattr(result.data_table, 'layout', 'MISSING')}"
        )

    def test_vision_data_table_has_num_sampled_dates(self):
        """Parsed DataTableSpec must have a `num_sampled_dates` attribute.

        **Validates: Requirements 1.3, 2.3**

        On unfixed code, DataTableSpec has no `num_sampled_dates` field.
        """
        data = {
            "chart_type": "line",
            "title": "Test Chart",
            "axis_config": {"x_label": "Date", "y_label": "Value"},
            "legend_entries": [],
            "annotations": [],
            "data_table": {
                "columns": ["PCE"],
                "visible": True,
                "font_size": 10,
                "layout": "transposed",
                "num_sampled_dates": 5,
                "series_shown": ["PCE"],
            },
            "layout_description": "",
        }

        result = ImageAnalyzer._parse_vision_response(data)

        assert result.data_table is not None
        assert hasattr(result.data_table, "num_sampled_dates"), (
            "DataTableSpec should have a 'num_sampled_dates' attribute but it doesn't."
        )
        assert result.data_table.num_sampled_dates == 5, (
            f"DataTableSpec.num_sampled_dates should be 5 but got "
            f"{getattr(result.data_table, 'num_sampled_dates', 'MISSING')}"
        )

    def test_vision_data_table_has_series_shown(self):
        """Parsed DataTableSpec must have a `series_shown` attribute.

        **Validates: Requirements 1.3, 2.3**

        On unfixed code, DataTableSpec has no `series_shown` field.
        """
        data = {
            "chart_type": "line",
            "title": "Test Chart",
            "axis_config": {"x_label": "Date", "y_label": "Value"},
            "legend_entries": [],
            "annotations": [],
            "data_table": {
                "columns": ["PCE"],
                "visible": True,
                "font_size": 10,
                "layout": "transposed",
                "num_sampled_dates": 5,
                "series_shown": ["PCE"],
            },
            "layout_description": "",
        }

        result = ImageAnalyzer._parse_vision_response(data)

        assert result.data_table is not None
        assert hasattr(result.data_table, "series_shown"), (
            "DataTableSpec should have a 'series_shown' attribute but it doesn't."
        )
        assert result.data_table.series_shown == ["PCE"], (
            f"DataTableSpec.series_shown should be ['PCE'] but got "
            f"{getattr(result.data_table, 'series_shown', 'MISSING')}"
        )
