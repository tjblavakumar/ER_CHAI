"""Utilities for applying ChartConfigDelta to ChartState and managing element updates.

Follows an immutable pattern: every mutation returns a new ChartState,
leaving the original untouched so callers can keep it for undo support.
"""

from __future__ import annotations

import copy

from backend.models.schemas import ChartConfigDelta, ChartState, Position


def apply_delta(state: ChartState, delta: ChartConfigDelta) -> ChartState:
    """Merge non-None fields from *delta* into *state*, returning a new ChartState.

    Only fields explicitly set (not None) in the delta are applied.
    The original *state* is never mutated.
    """
    state_dict = copy.deepcopy(state.model_dump())
    delta_dict = delta.model_dump(exclude_none=True)

    for key, value in delta_dict.items():
        state_dict[key] = value

    return ChartState(**state_dict)


def update_element_position(
    state: ChartState, element_id: str, new_position: Position
) -> ChartState:
    """Return a new ChartState with *element_id* mapped to *new_position*.

    If the element_id already exists its position is overwritten;
    otherwise a new entry is created.
    """
    state_dict = copy.deepcopy(state.model_dump())
    state_dict["elements_positions"][element_id] = new_position.model_dump()
    return ChartState(**state_dict)


def update_text_element_property(
    state: ChartState,
    element_id: str,
    property_name: str,
    value: object,
) -> ChartState:
    """Return a new ChartState with a single property changed on a text element.

    Supported *element_id* values and the sub-object they target:

    * ``"title"`` – ``state.title``
    * ``"annotation:<annotation_id>"`` – the matching ``AnnotationConfig``
    * ``"data_table"`` – ``state.data_table``

    Supported *property_name* values: ``font_size``, ``font_color``, ``font_family``.

    All other properties on the target element are preserved.

    Raises ``ValueError`` when *element_id* or *property_name* is not recognised.
    """
    allowed_properties = {"font_size", "font_color", "font_family"}
    if property_name not in allowed_properties:
        raise ValueError(
            f"Unsupported property '{property_name}'. "
            f"Allowed: {', '.join(sorted(allowed_properties))}"
        )

    state_dict = copy.deepcopy(state.model_dump())

    if element_id == "title":
        state_dict["title"][property_name] = value
    elif element_id.startswith("annotation:"):
        ann_id = element_id.split(":", 1)[1]
        for ann in state_dict["annotations"]:
            if ann["id"] == ann_id:
                ann[property_name] = value
                break
        else:
            raise ValueError(f"Annotation with id '{ann_id}' not found")
    elif element_id == "data_table":
        if state_dict["data_table"] is None:
            raise ValueError("No data_table present in chart state")
        state_dict["data_table"][property_name] = value
    else:
        raise ValueError(f"Unsupported element_id '{element_id}'")

    return ChartState(**state_dict)
