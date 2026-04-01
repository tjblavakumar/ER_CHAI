"""Shared fixtures and Hypothesis strategies for FRBSF Chart Builder tests."""

import string
import tempfile

import hypothesis.strategies as st
import pytest


# ---------------------------------------------------------------------------
# Hypothesis custom strategies
# ---------------------------------------------------------------------------

hex_color = st.from_regex(r"#[0-9a-fA-F]{6}", fullmatch=True)

non_empty_text = st.text(
    alphabet=string.ascii_letters + string.digits + " _-",
    min_size=1,
    max_size=60,
).filter(lambda s: s.strip() != "")

font_family = st.sampled_from(["Arial", "Helvetica", "Times New Roman", "Courier"])
font_size = st.integers(min_value=6, max_value=72)
font_weight = st.sampled_from(["normal", "bold"])
scale_type = st.sampled_from(["linear", "logarithmic"])
chart_type = st.sampled_from(["line", "bar", "mixed"])
gridline_style = st.sampled_from(["solid", "dashed", "dotted"])


# --- Position strategy ---
position_st = st.fixed_dictionaries(
    {"x": st.floats(min_value=-2000, max_value=2000, allow_nan=False),
     "y": st.floats(min_value=-2000, max_value=2000, allow_nan=False)}
)

# --- FontSpec strategy ---
font_spec_st = st.fixed_dictionaries({
    "family": font_family,
    "size": font_size,
    "color": hex_color,
    "weight": font_weight,
})

# --- FontStyles strategy ---
font_styles_st = st.fixed_dictionaries({
    "title": font_spec_st,
    "axis_label": font_spec_st,
    "tick_label": font_spec_st,
    "legend": font_spec_st,
    "annotation": font_spec_st,
})

# --- AxesConfig strategy ---
axes_config_st = st.fixed_dictionaries({
    "x_label": non_empty_text,
    "y_label": non_empty_text,
    "x_scale": scale_type,
    "y_scale": scale_type,
})

# --- SeriesConfig strategy ---
series_config_st = st.fixed_dictionaries({
    "name": non_empty_text,
    "column": non_empty_text,
    "chart_type": st.sampled_from(["line", "bar"]),
    "color": hex_color,
    "line_width": st.floats(min_value=0.5, max_value=10.0, allow_nan=False),
    "visible": st.booleans(),
})

# --- LegendEntry strategy ---
legend_entry_st = st.fixed_dictionaries({
    "label": non_empty_text,
    "color": hex_color,
    "series_name": non_empty_text,
})

# --- LegendConfig strategy ---
legend_config_st = st.fixed_dictionaries({
    "visible": st.booleans(),
    "position": position_st,
    "entries": st.lists(legend_entry_st, min_size=0, max_size=5),
})

# --- GridlineConfig strategy ---
gridline_config_st = st.fixed_dictionaries({
    "horizontal_visible": st.booleans(),
    "vertical_visible": st.booleans(),
    "style": gridline_style,
    "color": hex_color,
})

# --- ChartElementState strategy (for title) ---
chart_element_state_st = st.fixed_dictionaries({
    "text": non_empty_text,
    "font_family": font_family,
    "font_size": font_size,
    "font_color": hex_color,
    "position": position_st,
})

# --- AnnotationConfig strategy ---
annotation_config_st = st.fixed_dictionaries({
    "id": non_empty_text,
    "type": st.sampled_from(["text", "vertical_band"]),
    "text": st.one_of(st.none(), non_empty_text),
    "position": position_st,
    "font_size": font_size,
    "font_color": hex_color,
})

# --- DataTableConfig strategy ---
data_table_config_st = st.fixed_dictionaries({
    "visible": st.booleans(),
    "position": position_st,
    "columns": st.lists(non_empty_text, min_size=1, max_size=8),
    "font_size": font_size,
})

# --- ChartState strategy ---
def chart_state_st():
    """Strategy for generating valid ChartState dicts."""
    return st.fixed_dictionaries({
        "chart_type": chart_type,
        "title": chart_element_state_st,
        "axes": axes_config_st,
        "series": st.lists(series_config_st, min_size=1, max_size=6),
        "legend": legend_config_st,
        "gridlines": gridline_config_st,
        "annotations": st.lists(annotation_config_st, min_size=0, max_size=4),
        "data_table": st.one_of(st.none(), data_table_config_st),
        "elements_positions": st.dictionaries(
            non_empty_text, position_st, min_size=0, max_size=10
        ),
        "dataset_path": non_empty_text,
        "dataset_columns": st.lists(non_empty_text, min_size=1, max_size=8),
    })


# --- AppConfig strategy ---
valid_config_st = st.fixed_dictionaries({
    "fred_api_key": non_empty_text,
    "aws_region": st.sampled_from(["us-east-1", "us-west-2", "eu-west-1"]),
    "bedrock_model_id": st.just("anthropic.claude-3-sonnet-20240229-v1:0"),
}).map(lambda d: {**d, "bedrock_vision_model_id": d["bedrock_model_id"]})


# --- FRED URL strategies ---
fred_series_id = st.from_regex(r"[A-Z][A-Z0-9]{1,20}", fullmatch=True)

valid_fred_url_st = fred_series_id.map(
    lambda sid: f"https://fred.stlouisfed.org/series/{sid}"
)

invalid_fred_url_st = st.one_of(
    st.just("https://example.com/not-fred"),
    st.just("not-a-url"),
    st.just("https://fred.stlouisfed.org/"),
    st.just("https://fred.stlouisfed.org/graph/?g=abc"),
    non_empty_text.filter(lambda s: "fred.stlouisfed.org/series/" not in s),
)


# --- ProjectCreate strategy ---
project_create_st = st.fixed_dictionaries({
    "name": non_empty_text,
    "chart_state": chart_state_st(),
    "dataset_path": non_empty_text,
    "summary_text": st.text(min_size=0, max_size=200),
})


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_config_dict():
    """A minimal valid config dictionary."""
    return {
        "fred_api_key": "test-fred-key-123",
        "aws_region": "us-west-2",
        "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "bedrock_vision_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    }
