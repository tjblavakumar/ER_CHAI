"""Bug condition exploration test for vertical line annotation date positioning.

This test demonstrates the bug where AnnotationConfig.line_value typed as
float | None causes date strings like "2008", "2020-03", "2020-06-15" to be
lost during Pydantic validation. Vertical lines then render at x=0 instead
of the correct date position.

**Validates: Requirements 1.1, 1.2, 1.3**

EXPECTED OUTCOME: This test FAILS on unfixed code — failure proves the bug exists.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.models.schemas import AnnotationConfig, Position


# Concrete date strings that represent the bug condition
DATE_LINE_VALUES = ["2008", "2020-03", "2020-06-15"]


def _make_vertical_line_annotation(line_value: str) -> AnnotationConfig:
    """Attempt to create a vertical_line AnnotationConfig with a date string line_value."""
    return AnnotationConfig(
        id="test-vline",
        type="vertical_line",
        line_value=line_value,
        position=Position(x=0, y=0),
    )


class TestVerticalLineDatePreservation:
    """Bug Condition: Vertical line annotations with date string line_value.

    The bug is that line_value is typed as float | None, so date strings
    are either rejected by Pydantic or coerced to a numeric value, losing
    the date information needed to position the line on the x-axis.
    """

    @pytest.mark.parametrize("date_str", DATE_LINE_VALUES)
    def test_date_string_preserved_through_validation(self, date_str: str):
        """Date string line_value must survive Pydantic validation as a string.

        **Validates: Requirements 1.1, 1.2**

        On unfixed code, Pydantic will either:
        - Raise ValidationError (strict mode rejects string for float field)
        - Coerce "2008" to 2008.0 (losing the string type)
        - Coerce "2020-03" to ValidationError (not a valid float)
        """
        config = _make_vertical_line_annotation(date_str)
        # The date string must be preserved exactly as provided
        assert config.line_value == date_str, (
            f"line_value should be the string '{date_str}' but got {config.line_value!r} "
            f"(type={type(config.line_value).__name__}). "
            "Date string was lost or coerced during Pydantic validation."
        )

    @given(
        date_str=st.sampled_from(DATE_LINE_VALUES),
    )
    @settings(max_examples=10)
    def test_property_date_string_roundtrip(self, date_str: str):
        """Property: For all date-string line_values, the value is preserved as a string.

        **Validates: Requirements 1.1, 1.2**

        Bug Condition: isBugCondition(input) where input.type == "vertical_line"
        AND input.line_value IS a date string.
        """
        config = _make_vertical_line_annotation(date_str)
        assert isinstance(config.line_value, str), (
            f"line_value should be str but is {type(config.line_value).__name__}. "
            f"Input: '{date_str}', Got: {config.line_value!r}"
        )
        assert config.line_value == date_str, (
            f"line_value should be '{date_str}' but got '{config.line_value}'"
        )
