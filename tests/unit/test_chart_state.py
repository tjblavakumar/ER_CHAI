"""Unit tests for chart state management utilities."""

from __future__ import annotations

import copy

import pytest

from backend.models.schemas import (
    AnnotationConfig,
    AxesConfig,
    ChartConfigDelta,
    ChartElementState,
    ChartState,
    DataTableConfig,
    GridlineConfig,
    LegendConfig,
    LegendEntry,
    Position,
    SeriesConfig,
)
from backend.services.chart_state_utils import (
    apply_delta,
    update_element_position,
    update_text_element_property,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_state(**overrides) -> ChartState:
    """Build a minimal valid ChartState, with optional overrides."""
    defaults = dict(
        chart_type="line",
        title=ChartElementState(
            text="GDP Growth", font_family="Arial", font_size=14,
            font_color="#000000", position=Position(x=100, y=10),
        ),
        axes=AxesConfig(x_label="Date", y_label="Value"),
        series=[
            SeriesConfig(name="s1", column="col1", chart_type="line", color="#0000ff"),
        ],
        legend=LegendConfig(
            visible=True, position=Position(x=300, y=10),
            entries=[LegendEntry(label="s1", color="#0000ff", series_name="s1")],
        ),
        gridlines=GridlineConfig(),
        annotations=[],
        data_table=None,
        elements_positions={},
        dataset_path="data/test.csv",
        dataset_columns=["date", "col1"],
    )
    defaults.update(overrides)
    return ChartState(**defaults)


# ---------------------------------------------------------------------------
# apply_delta tests
# ---------------------------------------------------------------------------

class TestApplyDelta:
    """Tests for apply_delta."""

    def test_empty_delta_returns_equal_state(self):
        state = _make_state()
        delta = ChartConfigDelta()
        result = apply_delta(state, delta)
        assert result == state

    def test_original_state_not_mutated(self):
        state = _make_state()
        original_dump = state.model_dump()
        delta = ChartConfigDelta(chart_type="bar")
        apply_delta(state, delta)
        assert state.model_dump() == original_dump

    def test_chart_type_changed(self):
        state = _make_state(chart_type="line")
        delta = ChartConfigDelta(chart_type="bar")
        result = apply_delta(state, delta)
        assert result.chart_type == "bar"

    def test_title_replaced(self):
        state = _make_state()
        new_title = ChartElementState(
            text="New Title", font_family="Helvetica", font_size=18,
            font_color="#ff0000", position=Position(x=50, y=5),
        )
        delta = ChartConfigDelta(title=new_title)
        result = apply_delta(state, delta)
        assert result.title == new_title
        # Other fields unchanged
        assert result.chart_type == state.chart_type

    def test_axes_replaced(self):
        state = _make_state()
        new_axes = AxesConfig(x_label="Year", y_label="Percent", y_scale="logarithmic")
        delta = ChartConfigDelta(axes=new_axes)
        result = apply_delta(state, delta)
        assert result.axes.x_label == "Year"
        assert result.axes.y_scale == "logarithmic"

    def test_series_replaced(self):
        state = _make_state()
        new_series = [
            SeriesConfig(name="a", column="colA", chart_type="bar", color="#aaaaaa"),
            SeriesConfig(name="b", column="colB", chart_type="line", color="#bbbbbb"),
        ]
        delta = ChartConfigDelta(series=new_series)
        result = apply_delta(state, delta)
        assert len(result.series) == 2
        assert result.series[0].name == "a"

    def test_gridlines_replaced(self):
        state = _make_state()
        new_grid = GridlineConfig(horizontal_visible=False, vertical_visible=True, style="solid", color="#111111")
        delta = ChartConfigDelta(gridlines=new_grid)
        result = apply_delta(state, delta)
        assert result.gridlines.horizontal_visible is False
        assert result.gridlines.style == "solid"

    def test_legend_replaced(self):
        state = _make_state()
        new_legend = LegendConfig(
            visible=False, position=Position(x=0, y=0), entries=[],
        )
        delta = ChartConfigDelta(legend=new_legend)
        result = apply_delta(state, delta)
        assert result.legend.visible is False

    def test_annotations_replaced(self):
        state = _make_state()
        ann = AnnotationConfig(id="a1", type="text", text="Note", position=Position(x=10, y=20))
        delta = ChartConfigDelta(annotations=[ann])
        result = apply_delta(state, delta)
        assert len(result.annotations) == 1
        assert result.annotations[0].id == "a1"

    def test_data_table_set(self):
        state = _make_state(data_table=None)
        dt = DataTableConfig(visible=True, position=Position(x=0, y=400), columns=["date", "val"], font_size=9)
        delta = ChartConfigDelta(data_table=dt)
        result = apply_delta(state, delta)
        assert result.data_table is not None
        assert result.data_table.visible is True

    def test_multiple_fields_in_one_delta(self):
        state = _make_state()
        delta = ChartConfigDelta(
            chart_type="mixed",
            gridlines=GridlineConfig(horizontal_visible=False, style="dotted"),
        )
        result = apply_delta(state, delta)
        assert result.chart_type == "mixed"
        assert result.gridlines.horizontal_visible is False
        assert result.gridlines.style == "dotted"


# ---------------------------------------------------------------------------
# update_element_position tests
# ---------------------------------------------------------------------------

class TestUpdateElementPosition:
    """Tests for update_element_position."""

    def test_add_new_position(self):
        state = _make_state(elements_positions={})
        result = update_element_position(state, "legend", Position(x=50, y=60))
        assert result.elements_positions["legend"] == Position(x=50, y=60)

    def test_overwrite_existing_position(self):
        state = _make_state(elements_positions={"legend": Position(x=0, y=0)})
        result = update_element_position(state, "legend", Position(x=99, y=88))
        assert result.elements_positions["legend"] == Position(x=99, y=88)

    def test_original_state_not_mutated(self):
        state = _make_state(elements_positions={})
        update_element_position(state, "title", Position(x=1, y=2))
        assert "title" not in state.elements_positions

    def test_other_positions_preserved(self):
        state = _make_state(elements_positions={
            "legend": Position(x=10, y=20),
            "title": Position(x=30, y=40),
        })
        result = update_element_position(state, "legend", Position(x=99, y=99))
        assert result.elements_positions["title"] == Position(x=30, y=40)

    def test_negative_coordinates(self):
        state = _make_state()
        result = update_element_position(state, "el", Position(x=-100, y=-200))
        assert result.elements_positions["el"].x == -100


# ---------------------------------------------------------------------------
# update_text_element_property tests
# ---------------------------------------------------------------------------

class TestUpdateTextElementProperty:
    """Tests for update_text_element_property."""

    # --- title ---

    def test_title_font_size(self):
        state = _make_state()
        result = update_text_element_property(state, "title", "font_size", 24)
        assert result.title.font_size == 24
        # Other title props unchanged
        assert result.title.font_family == state.title.font_family
        assert result.title.font_color == state.title.font_color
        assert result.title.text == state.title.text

    def test_title_font_color(self):
        state = _make_state()
        result = update_text_element_property(state, "title", "font_color", "#ff0000")
        assert result.title.font_color == "#ff0000"
        assert result.title.font_size == state.title.font_size

    def test_title_font_family(self):
        state = _make_state()
        result = update_text_element_property(state, "title", "font_family", "Courier")
        assert result.title.font_family == "Courier"

    # --- annotation ---

    def test_annotation_font_size(self):
        ann = AnnotationConfig(id="a1", type="text", text="Hi", position=Position(x=0, y=0), font_size=10, font_color="#333333")
        state = _make_state(annotations=[ann])
        result = update_text_element_property(state, "annotation:a1", "font_size", 16)
        assert result.annotations[0].font_size == 16
        assert result.annotations[0].font_color == "#333333"

    def test_annotation_font_color(self):
        ann = AnnotationConfig(id="a1", type="text", text="Hi", position=Position(x=0, y=0))
        state = _make_state(annotations=[ann])
        result = update_text_element_property(state, "annotation:a1", "font_color", "#00ff00")
        assert result.annotations[0].font_color == "#00ff00"

    def test_annotation_not_found_raises(self):
        state = _make_state(annotations=[])
        with pytest.raises(ValueError, match="not found"):
            update_text_element_property(state, "annotation:missing", "font_size", 12)

    # --- data_table ---

    def test_data_table_font_size(self):
        dt = DataTableConfig(visible=True, position=Position(x=0, y=400), columns=["a"], font_size=10)
        state = _make_state(data_table=dt)
        result = update_text_element_property(state, "data_table", "font_size", 8)
        assert result.data_table.font_size == 8
        assert result.data_table.visible is True

    def test_data_table_none_raises(self):
        state = _make_state(data_table=None)
        with pytest.raises(ValueError, match="No data_table"):
            update_text_element_property(state, "data_table", "font_size", 10)

    # --- edge cases ---

    def test_unsupported_property_raises(self):
        state = _make_state()
        with pytest.raises(ValueError, match="Unsupported property"):
            update_text_element_property(state, "title", "text", "bad")

    def test_unsupported_element_id_raises(self):
        state = _make_state()
        with pytest.raises(ValueError, match="Unsupported element_id"):
            update_text_element_property(state, "unknown_element", "font_size", 12)

    def test_original_state_not_mutated(self):
        state = _make_state()
        original_size = state.title.font_size
        update_text_element_property(state, "title", "font_size", 99)
        assert state.title.font_size == original_size


# ---------------------------------------------------------------------------
# Undo pattern (immutability) tests
# ---------------------------------------------------------------------------

class TestUndoPattern:
    """Verify that the immutable pattern supports undo by keeping old states."""

    def test_undo_after_delta(self):
        original = _make_state(chart_type="line")
        modified = apply_delta(original, ChartConfigDelta(chart_type="bar"))
        assert modified.chart_type == "bar"
        # "Undo" is simply using the original reference
        assert original.chart_type == "line"

    def test_undo_after_position_update(self):
        original = _make_state(elements_positions={"legend": Position(x=0, y=0)})
        modified = update_element_position(original, "legend", Position(x=999, y=999))
        assert modified.elements_positions["legend"].x == 999
        assert original.elements_positions["legend"].x == 0

    def test_undo_after_property_change(self):
        original = _make_state()
        modified = update_text_element_property(original, "title", "font_size", 48)
        assert modified.title.font_size == 48
        assert original.title.font_size == 14
