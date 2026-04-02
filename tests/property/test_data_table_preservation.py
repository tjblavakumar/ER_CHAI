"""Preservation property tests for data table fix.

These tests capture EXISTING behavior on UNFIXED code. They must PASS before
and after the fix to ensure no regressions are introduced.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

from __future__ import annotations

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.models.schemas import (
    AnnotationConfig,
    AnnotationSpec,
    AxisConfig,
    AxesConfig,
    ChartElementState,
    ChartSpecification,
    ChartState,
    DataTableConfig,
    DataTableSpec,
    FontSpec,
    FontStyles,
    GridlineConfig,
    LegendConfig,
    LegendEntry,
    LegendLayout,
    Position,
    SeriesConfig,
)
from backend.services.image_analyzer import ImageAnalyzer
from backend.services.ingestion import (
    _apply_image_spec_to_chart_state,
    _build_chart_state_from_df,
    _build_default_chart_state,
)


def _make_fred_dataset(series_id="PCEPI", title="PCE Price Index"):
    from backend.models.schemas import FREDDataset, Observation
    return FREDDataset(
        series_id=series_id, title=title, units="Index", frequency="Monthly",
        observations=[
            Observation(date="2020-01-01", value=100.0),
            Observation(date="2020-02-01", value=101.0),
        ],
    )


def _make_chart_state(num_series=2, num_annotations=1, dt_columns=None):
    colors = ["#003B5C", "#5B9BD5", "#A5C8E1", "#6D6E71"]
    series = [
        SeriesConfig(name=f"s{i}", column=f"s{i}", chart_type="line",
                     color=colors[i % len(colors)], line_width=2.0, visible=True)
        for i in range(num_series)
    ]
    legend_entries = [
        LegendEntry(label=f"s{i}", color=colors[i % len(colors)], series_name=f"s{i}")
        for i in range(num_series)
    ]
    annotations = [
        AnnotationConfig(id=f"a{i}", type="text", text=f"Note {i}",
                         position=Position(x=100.0, y=200.0), font_size=10, font_color="#333")
        for i in range(num_annotations)
    ]
    dt = None
    if dt_columns is not None:
        dt = DataTableConfig(visible=True, position=Position(x=70, y=490),
                             columns=dt_columns, font_size=10, max_rows=5)
    return ChartState(
        chart_type="line",
        title=ChartElementState(text="T", font_family="Arial", font_size=16,
                                font_color="#003B5C", position=Position(x=50, y=10)),
        axes=AxesConfig(x_label="Date", y_label="Value"),
        series=series,
        legend=LegendConfig(visible=True, position=Position(x=50, y=40), entries=legend_entries),
        gridlines=GridlineConfig(horizontal_visible=True, vertical_visible=False,
                                 style="dashed", color="#D1D3D4"),
        annotations=annotations,
        data_table=dt,
        elements_positions={"title": Position(x=50, y=10)},
        dataset_path="data/test.csv",
        dataset_columns=["date"] + [f"s{i}" for i in range(num_series)],
    )


def _make_spec(num_series=2, num_ann=0, data_table=None):
    colors = ["#003B5C", "#5B9BD5", "#A5C8E1", "#6D6E71"]
    cm = {f"s{i}": colors[i % len(colors)] for i in range(num_series)}
    anns = [AnnotationSpec(text=f"Img {i}", x=150.0, y=250.0) for i in range(num_ann)]
    return ChartSpecification(
        chart_type="line", color_mappings=cm,
        font_styles=FontStyles(
            title=FontSpec(family="Arial", size=16, color="#003B5C", weight="bold"),
            axis_label=FontSpec(family="Arial", size=12, color="#333333"),
            tick_label=FontSpec(family="Arial", size=10, color="#333333"),
            legend=FontSpec(family="Arial", size=11, color="#333333"),
            annotation=FontSpec(family="Arial", size=10, color="#333333"),
        ),
        axis_config=AxisConfig(x_label="Date", y_label="Value"),
        legend_layout=LegendLayout(position="bottom", orientation="horizontal"),
        annotations=anns, data_table=data_table, vertical_bands=[],
    )


# ---------------------------------------------------------------------------
# Preservation 1 - FRED single-series ingestion produces no data table
# ---------------------------------------------------------------------------


class TestFredIngestionNoDataTable:
    """**Validates: Requirements 3.1**"""

    def test_fred_ingestion_data_table_is_none(self):
        ds = _make_fred_dataset()
        df = pd.DataFrame({"date": ["2020-01-01", "2020-02-01"], "value": [100.0, 101.0]})
        result = _build_default_chart_state(
            dataset=ds, dataset_path="data/pcepi.csv", columns=list(df.columns), df=df,
        )
        assert result.data_table is None

    @given(
        series_id=st.from_regex(r"[A-Z]{2,6}", fullmatch=True),
        title=st.text(min_size=1, max_size=30).filter(lambda s: s.strip()),
    )
    @settings(max_examples=15)
    def test_property_fred_always_no_data_table(self, series_id, title):
        """Property: for all FRED datasets, data_table is None.

        **Validates: Requirements 3.1**
        """
        ds = _make_fred_dataset(series_id=series_id, title=title)
        df = pd.DataFrame({"date": ["2020-01-01"], "value": [1.0]})
        result = _build_default_chart_state(
            dataset=ds, dataset_path="data/t.csv", columns=list(df.columns), df=df,
        )
        assert result.data_table is None


# ---------------------------------------------------------------------------
# Preservation 2 - Non-data-table elements unchanged
# ---------------------------------------------------------------------------


class TestNonDataTableElementsPreserved:
    """**Validates: Requirements 3.2, 3.4**"""

    def test_annotations_preserved(self):
        cs = _make_chart_state(num_annotations=2, dt_columns=["s0", "s1"])
        sp = _make_spec(num_ann=1)
        df = pd.DataFrame({"date": ["2020-01"], "s0": [1.0], "s1": [2.0]})
        orig_texts = {a.text for a in cs.annotations if a.text}
        result = _apply_image_spec_to_chart_state(cs, sp, df)
        result_texts = {a.text for a in result.annotations if a.text}
        assert orig_texts.issubset(result_texts)

    def test_legend_entry_count_preserved(self):
        cs = _make_chart_state(num_series=3, dt_columns=["s0", "s1", "s2"])
        sp = _make_spec(num_series=3)
        df = pd.DataFrame({"date": ["2020-01"], "s0": [1.0], "s1": [2.0], "s2": [3.0]})
        result = _apply_image_spec_to_chart_state(cs, sp, df)
        assert len(result.legend.entries) == len(cs.legend.entries)

    def test_gridline_vertical_visible_preserved(self):
        cs = _make_chart_state(dt_columns=["s0", "s1"])
        sp = _make_spec()
        df = pd.DataFrame({"date": ["2020-01"], "s0": [1.0], "s1": [2.0]})
        result = _apply_image_spec_to_chart_state(cs, sp, df)
        assert result.gridlines.vertical_visible == cs.gridlines.vertical_visible

    @given(
        num_ann=st.integers(min_value=0, max_value=3),
        num_series=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=15)
    def test_property_elements_preserved(self, num_ann, num_series):
        """Property: non-data-table elements preserved for all inputs.

        **Validates: Requirements 3.2, 3.4**
        """
        cols = [f"s{i}" for i in range(num_series)]
        cs = _make_chart_state(num_series=num_series, num_annotations=num_ann, dt_columns=cols)
        sp = _make_spec(num_series=num_series)
        data = {"date": ["2020-01"]}
        for c in cols:
            data[c] = [1.0]
        df = pd.DataFrame(data)
        result = _apply_image_spec_to_chart_state(cs, sp, df)
        assert len(result.annotations) >= num_ann
        assert len(result.legend.entries) == len(cs.legend.entries)
        assert result.gridlines.vertical_visible == cs.gridlines.vertical_visible


# ---------------------------------------------------------------------------
# Preservation 3 - All-numeric DataFrame produces same columns
# ---------------------------------------------------------------------------


class TestAllNumericDataFrameColumns:
    """**Validates: Requirements 3.2**"""

    def test_all_numeric_columns_in_data_table(self):
        df = pd.DataFrame({"metric_a": [1.0, 2.0], "metric_b": [3.0, 4.0]})
        result = _build_chart_state_from_df(df=df, dataset_path="data/t.csv", title="T")
        assert result.data_table is not None
        assert result.data_table.columns == list(df.columns)

    @given(num_cols=st.integers(min_value=1, max_value=4))
    @settings(max_examples=15)
    def test_property_all_numeric_columns_preserved(self, num_cols):
        """Property: all-numeric DataFrames keep all columns.

        **Validates: Requirements 3.2**
        """
        cols = [f"c{i}" for i in range(num_cols)]
        df = pd.DataFrame({c: [1.0, 2.0] for c in cols})
        result = _build_chart_state_from_df(df=df, dataset_path="data/t.csv", title="T")
        assert result.data_table is not None
        assert result.data_table.columns == cols


# ---------------------------------------------------------------------------
# Preservation 4 - DataTableConfig default position is (70, 490)
# ---------------------------------------------------------------------------


class TestDataTableDefaultPosition:
    """**Validates: Requirements 3.5**"""

    def test_default_position(self):
        df = pd.DataFrame({"date": ["2020-01"], "value": [1.0]})
        result = _build_chart_state_from_df(df=df, dataset_path="data/t.csv", title="T")
        assert result.data_table is not None
        assert result.data_table.position.x == 70.0
        assert result.data_table.position.y == 490.0

    def test_apply_image_spec_preserves_existing_position(self):
        cs = _make_chart_state(dt_columns=["s0", "s1"])
        cs.data_table.position = Position(x=100, y=500)
        sp = _make_spec(data_table=DataTableSpec(columns=["s0"], visible=True, font_size=10))
        df = pd.DataFrame({"date": ["2020-01"], "s0": [1.0], "s1": [2.0]})
        result = _apply_image_spec_to_chart_state(cs, sp, df)
        assert result.data_table is not None
        assert result.data_table.position.x == 100.0
        assert result.data_table.position.y == 500.0


# ---------------------------------------------------------------------------
# Preservation 5 - Vision analysis with no data table returns null
# ---------------------------------------------------------------------------


class TestVisionNoDataTableReturnsNull:
    """**Validates: Requirements 3.3**"""

    def test_null_data_table_preserved(self):
        data = {
            "chart_type": "line", "title": "T",
            "axis_config": {"x_label": "", "y_label": ""},
            "legend_entries": [], "annotations": [],
            "data_table": None, "layout_description": "",
        }
        result = ImageAnalyzer._parse_vision_response(data)
        assert result.data_table is None

    def test_missing_data_table_key_returns_null(self):
        data = {
            "chart_type": "line", "title": "T",
            "axis_config": {"x_label": "", "y_label": ""},
            "legend_entries": [], "annotations": [],
            "layout_description": "",
        }
        result = ImageAnalyzer._parse_vision_response(data)
        assert result.data_table is None

    @given(
        chart_type=st.sampled_from(["line", "bar", "mixed", "area"]),
        title=st.text(min_size=0, max_size=20),
    )
    @settings(max_examples=15)
    def test_property_no_data_table_always_null(self, chart_type, title):
        """Property: vision responses with no data table always return None.

        **Validates: Requirements 3.3**
        """
        data = {
            "chart_type": chart_type, "title": title,
            "axis_config": {"x_label": "", "y_label": ""},
            "legend_entries": [], "annotations": [],
            "data_table": None, "layout_description": "",
        }
        result = ImageAnalyzer._parse_vision_response(data)
        assert result.data_table is None
