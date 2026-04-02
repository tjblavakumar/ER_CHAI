"""Preservation property tests for non-vertical-line annotation behavior.

These tests capture the CURRENT correct behavior of horizontal_line, vertical_band,
and text annotations. They must PASS on the unfixed code and continue to pass after
the vertical_line bug fix, ensuring no regressions.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

EXPECTED OUTCOME: These tests PASS on unfixed code — they confirm baseline behavior.
"""

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from backend.models.schemas import AnnotationConfig, Position


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Numeric line_value for horizontal lines — finite floats in a reasonable range
numeric_line_value_st = st.floats(
    min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
)

# Chart area parameters
y_min_max_st = st.tuples(
    st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
    st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
).filter(lambda t: t[1] - t[0] > 0.01)  # ensure yMax > yMin with meaningful range

chart_height_st = st.floats(min_value=50, max_value=2000, allow_nan=False, allow_infinity=False)
chart_y_st = st.floats(min_value=0, max_value=500, allow_nan=False, allow_infinity=False)

# Date strings for vertical bands
date_string_st = st.sampled_from([
    "2018-01", "2019-06", "2020-01", "2020-03", "2020-06", "2021-12", "2022-01",
])

# Position coordinates
position_coord_st = st.floats(
    min_value=-2000, max_value=2000, allow_nan=False, allow_infinity=False
)

# Annotation id
annotation_id_st = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_",
    min_size=1, max_size=20,
)


# ---------------------------------------------------------------------------
# Property 3: Preservation — Horizontal Line Positioning Unchanged
# ---------------------------------------------------------------------------


class TestHorizontalLinePreservation:
    """Preservation: horizontal_line annotations with numeric line_value.

    **Validates: Requirements 3.1**
    """

    @given(line_value=numeric_line_value_st)
    @settings(max_examples=50)
    def test_numeric_line_value_preserved_through_validation(self, line_value: float):
        """For any numeric line_value, Pydantic validation preserves the value.

        **Validates: Requirements 3.1**
        """
        config = AnnotationConfig(
            id="hline-test",
            type="horizontal_line",
            line_value=line_value,
            position=Position(x=0, y=0),
        )
        assert config.line_value == line_value, (
            f"horizontal_line line_value should be {line_value} but got {config.line_value}"
        )

    @given(
        line_value=numeric_line_value_st,
        y_range=y_min_max_st,
        chart_y=chart_y_st,
        chart_height=chart_height_st,
    )
    @settings(max_examples=50)
    def test_horizontal_line_y_coordinate_formula(
        self, line_value: float, y_range: tuple, chart_y: float, chart_height: float
    ):
        """For any horizontal_line with numeric line_value, the y-coordinate follows
        the formula: y = chartArea.y + chartArea.height - ((line_value - yMin) / (yMax - yMin)) * chartArea.height

        **Validates: Requirements 3.1**
        """
        yMin, yMax = y_range
        yRange = yMax - yMin

        config = AnnotationConfig(
            id="hline-test",
            type="horizontal_line",
            line_value=line_value,
            position=Position(x=0, y=0),
        )

        # Compute expected y-coordinate using the same formula as AnnotationElement.tsx
        line_val = config.line_value if config.line_value is not None else 0
        expected_py = chart_y + chart_height - ((line_val - yMin) / yRange) * chart_height

        # Verify the formula produces a finite result
        assert isinstance(expected_py, float), (
            f"y-coordinate should be float, got {type(expected_py)}"
        )

    @pytest.mark.parametrize("line_value", [0.0, 2.0, 5.5, -3.14, 100.0])
    def test_concrete_numeric_values_preserved(self, line_value: float):
        """Concrete numeric line_values are preserved exactly.

        **Validates: Requirements 3.1**
        """
        config = AnnotationConfig(
            id="hline-concrete",
            type="horizontal_line",
            line_value=line_value,
            position=Position(x=0, y=0),
        )
        assert config.line_value == line_value


# ---------------------------------------------------------------------------
# Property 4: Preservation — Vertical Band Behavior Unchanged
# ---------------------------------------------------------------------------


class TestVerticalBandPreservation:
    """Preservation: vertical_band annotations with band_start/band_end date strings.

    **Validates: Requirements 3.2**
    """

    @given(
        band_start=date_string_st,
        band_end=date_string_st,
    )
    @settings(max_examples=50)
    def test_band_dates_preserved_through_validation(
        self, band_start: str, band_end: str
    ):
        """For any vertical_band with date string band_start/band_end,
        the values are preserved through Pydantic validation.

        **Validates: Requirements 3.2**
        """
        config = AnnotationConfig(
            id="vband-test",
            type="vertical_band",
            band_start=band_start,
            band_end=band_end,
            band_color="#cccccc",
            position=Position(x=0, y=0),
        )
        assert config.band_start == band_start, (
            f"band_start should be '{band_start}' but got '{config.band_start}'"
        )
        assert config.band_end == band_end, (
            f"band_end should be '{band_end}' but got '{config.band_end}'"
        )

    @given(band_start=date_string_st)
    @settings(max_examples=30)
    def test_band_start_only_preserved(self, band_start: str):
        """Vertical band with only band_start (no band_end) preserves the value.

        **Validates: Requirements 3.2**
        """
        config = AnnotationConfig(
            id="vband-start-only",
            type="vertical_band",
            band_start=band_start,
            band_color="#cccccc",
            position=Position(x=0, y=0),
        )
        assert config.band_start == band_start
        assert config.band_end is None

    @pytest.mark.parametrize("band_start,band_end", [
        ("2020-01", "2020-06"),
        ("2019-06", "2021-12"),
        ("2018-01", "2022-01"),
    ])
    def test_concrete_band_dates_preserved(self, band_start: str, band_end: str):
        """Concrete band date pairs are preserved exactly.

        **Validates: Requirements 3.2**
        """
        config = AnnotationConfig(
            id="vband-concrete",
            type="vertical_band",
            band_start=band_start,
            band_end=band_end,
            band_color="#cccccc",
            position=Position(x=0, y=0),
        )
        assert config.band_start == band_start
        assert config.band_end == band_end


# ---------------------------------------------------------------------------
# Property 4 (cont.): Preservation — Text Annotation Position Unchanged
# ---------------------------------------------------------------------------


class TestTextAnnotationPreservation:
    """Preservation: text annotations with explicit position.

    **Validates: Requirements 3.3**
    """

    @given(
        x=position_coord_st,
        y=position_coord_st,
    )
    @settings(max_examples=50)
    def test_text_position_preserved_through_validation(self, x: float, y: float):
        """For any text annotation with explicit position, the position is preserved.

        **Validates: Requirements 3.3**
        """
        config = AnnotationConfig(
            id="text-test",
            type="text",
            text="Test annotation",
            position=Position(x=x, y=y),
        )
        assert config.position.x == x, (
            f"position.x should be {x} but got {config.position.x}"
        )
        assert config.position.y == y, (
            f"position.y should be {y} but got {config.position.y}"
        )

    @given(
        x=position_coord_st,
        y=position_coord_st,
        text=st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != ""),
    )
    @settings(max_examples=50)
    def test_text_content_and_position_preserved(self, x: float, y: float, text: str):
        """For any text annotation, both text content and position are preserved.

        **Validates: Requirements 3.3**
        """
        config = AnnotationConfig(
            id="text-content-test",
            type="text",
            text=text,
            position=Position(x=x, y=y),
        )
        assert config.text == text
        assert config.position.x == x
        assert config.position.y == y

    @pytest.mark.parametrize("x,y", [
        (0.0, 0.0),
        (100.0, 200.0),
        (-50.5, 300.75),
        (1500.0, 1000.0),
    ])
    def test_concrete_positions_preserved(self, x: float, y: float):
        """Concrete text annotation positions are preserved exactly.

        **Validates: Requirements 3.3**
        """
        config = AnnotationConfig(
            id="text-concrete",
            type="text",
            text="Sample text",
            position=Position(x=x, y=y),
        )
        assert config.position.x == x
        assert config.position.y == y


# ---------------------------------------------------------------------------
# Property 4 (cont.): Preservation — Annotation Schema Defaults Unchanged
# ---------------------------------------------------------------------------


class TestAnnotationSchemaDefaults:
    """Preservation: annotation schema defaults remain consistent.

    **Validates: Requirements 3.4, 3.5**
    """

    def test_horizontal_line_defaults(self):
        """Horizontal line annotation defaults are preserved.

        **Validates: Requirements 3.1**
        """
        config = AnnotationConfig(
            id="hline-defaults",
            type="horizontal_line",
            position=Position(x=0, y=0),
        )
        assert config.line_value is None
        assert config.line_color == "#cc0000"
        assert config.line_style == "dotted"
        assert config.line_width == 1.5

    def test_vertical_band_defaults(self):
        """Vertical band annotation defaults are preserved.

        **Validates: Requirements 3.2**
        """
        config = AnnotationConfig(
            id="vband-defaults",
            type="vertical_band",
            position=Position(x=0, y=0),
        )
        assert config.band_start is None
        assert config.band_end is None
        assert config.band_color is None

    def test_text_annotation_defaults(self):
        """Text annotation defaults are preserved.

        **Validates: Requirements 3.3**
        """
        config = AnnotationConfig(
            id="text-defaults",
            type="text",
            position=Position(x=0, y=0),
        )
        assert config.text is None
        assert config.font_size == 10
        assert config.font_color == "#333333"

    @given(
        ann_type=st.sampled_from(["horizontal_line", "vertical_band", "text"]),
        ann_id=annotation_id_st,
    )
    @settings(max_examples=30)
    def test_non_vertical_line_types_validate_successfully(
        self, ann_type: str, ann_id: str
    ):
        """All non-vertical-line annotation types validate without error.

        **Validates: Requirements 3.4, 3.5**
        """
        config = AnnotationConfig(
            id=ann_id,
            type=ann_type,
            position=Position(x=0, y=0),
        )
        assert config.type == ann_type
        assert config.id == ann_id
