"""Export Service for the FRBSF Chart Builder.

Generates standalone Python (matplotlib), R (ggplot2), and PDF exports
from a ChartState, embedding the dataset inline so exports are fully
self-contained.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from backend.models.schemas import ChartState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FRBSF branding constants
# ---------------------------------------------------------------------------

_FRBSF_BLUE = "#003A70"
_FRBSF_LIGHT_BLUE = "#0072CE"
_FRBSF_GRAY = "#6C757D"
_FRBSF_FONT = "Helvetica"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_dataset(dataset_path: str) -> pd.DataFrame:
    """Load a dataset from the given path (CSV or Excel)."""
    path = Path(dataset_path)
    if path.suffix in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def _df_to_python_literal(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a Python dict-of-lists literal string."""
    lines = ["data = {"]
    for col in df.columns:
        values = df[col].tolist()
        # Represent values as Python literals
        formatted = []
        for v in values:
            if pd.isna(v):
                formatted.append("None")
            elif isinstance(v, str):
                formatted.append(repr(v))
            else:
                formatted.append(repr(v))
        lines.append(f"    {repr(str(col))}: [{', '.join(formatted)}],")
    lines.append("}")
    return "\n".join(lines)


def _df_to_r_literal(df: pd.DataFrame) -> str:
    """Convert a DataFrame to an R data.frame() literal string."""
    col_parts = []
    for col in df.columns:
        values = df[col].tolist()
        formatted = []
        for v in values:
            if pd.isna(v):
                formatted.append("NA")
            elif isinstance(v, str):
                formatted.append(f'"{v}"')
            else:
                formatted.append(str(v))
        safe_name = str(col).replace(" ", ".").replace("-", ".")
        col_parts.append(f'  {safe_name} = c({", ".join(formatted)})')
    inner = ",\n".join(col_parts)
    return f"data <- data.frame(\n{inner}\n)"


# ---------------------------------------------------------------------------
# Python export
# ---------------------------------------------------------------------------


def _generate_python_script(chart_state: ChartState, df: pd.DataFrame) -> str:
    """Generate a standalone matplotlib Python script."""
    # Build series plotting code
    plot_lines: list[str] = []
    for s in chart_state.series:
        if not s.visible:
            continue
        col = s.column
        if s.chart_type == "bar":
            plot_lines.append(
                f'ax.bar(df.index, df["{col}"], color="{s.color}", '
                f'label="{s.name}", width=0.8)'
            )
        else:
            plot_lines.append(
                f'ax.plot(df.index, df["{col}"], color="{s.color}", '
                f'label="{s.name}", linewidth={s.line_width})'
            )

    plot_code = "\n".join(f"    {line}" for line in plot_lines)

    # Gridline config
    grid_lines: list[str] = []
    if chart_state.gridlines.horizontal_visible:
        style_map = {"dashed": "--", "dotted": ":", "solid": "-"}
        ls = style_map.get(chart_state.gridlines.style, "--")
        grid_lines.append(
            f'    ax.yaxis.grid(True, linestyle="{ls}", '
            f'color="{chart_state.gridlines.color}")'
        )
    if chart_state.gridlines.vertical_visible:
        style_map = {"dashed": "--", "dotted": ":", "solid": "-"}
        ls = style_map.get(chart_state.gridlines.style, "--")
        grid_lines.append(
            f'    ax.xaxis.grid(True, linestyle="{ls}", '
            f'color="{chart_state.gridlines.color}")'
        )
    grid_code = "\n".join(grid_lines) if grid_lines else "    pass  # no gridlines"

    # Axis limits
    axis_limits: list[str] = []
    if chart_state.axes.x_min is not None and chart_state.axes.x_max is not None:
        axis_limits.append(
            f"    ax.set_xlim({chart_state.axes.x_min}, {chart_state.axes.x_max})"
        )
    if chart_state.axes.y_min is not None and chart_state.axes.y_max is not None:
        axis_limits.append(
            f"    ax.set_ylim({chart_state.axes.y_min}, {chart_state.axes.y_max})"
        )
    axis_limit_code = "\n".join(axis_limits) if axis_limits else ""

    # Scale
    scale_code = ""
    if chart_state.axes.y_scale == "logarithmic":
        scale_code = '    ax.set_yscale("log")\n'
    if chart_state.axes.x_scale == "logarithmic":
        scale_code += '    ax.set_xscale("log")\n'

    # --- Task 7.1: Title positioning via fig.text() ---
    _stage_w, _stage_h = 860, 560
    title_fig_x = chart_state.title.position.x / _stage_w
    title_fig_y = 1.0 - chart_state.title.position.y / _stage_h
    title_code = (
        f'    fig.text({title_fig_x:.4f}, {title_fig_y:.4f}, '
        f'"{chart_state.title.text}", fontsize={chart_state.title.font_size},\n'
        f'             fontfamily="{chart_state.title.font_family}", '
        f'color="{chart_state.title.font_color}", ha="left", va="top")'
    )

    # --- Task 7.2: Vertical line annotations ---
    vline_lines: list[str] = []
    for ann in chart_state.annotations:
        if ann.type == "vertical_line" and ann.line_value is not None:
            style_map_vl = {"dashed": "--", "dotted": ":", "solid": "-"}
            ls_vl = style_map_vl.get(ann.line_style, "--")
            xval = ann.line_value
            if isinstance(xval, str):
                vline_lines.append(
                    f'    ax.axvline(x=pd.Timestamp("{xval}"), '
                    f'color="{ann.line_color}", linestyle="{ls_vl}", '
                    f'linewidth={ann.line_width})'
                )
            else:
                # Numeric — interpret as year
                try:
                    year_int = int(xval)
                    vline_lines.append(
                        f'    ax.axvline(x=pd.Timestamp(year={year_int}, month=1, day=1), '
                        f'color="{ann.line_color}", linestyle="{ls_vl}", '
                        f'linewidth={ann.line_width})'
                    )
                except (ValueError, TypeError):
                    vline_lines.append(
                        f'    ax.axvline(x={xval}, '
                        f'color="{ann.line_color}", linestyle="{ls_vl}", '
                        f'linewidth={ann.line_width})'
                    )
    vline_code = "\n".join(vline_lines) if vline_lines else ""

    # --- Task 7.3: Text annotations ---
    text_ann_lines: list[str] = []
    for ann in chart_state.annotations:
        if ann.type == "text" and ann.text:
            fig_x = ann.position.x / _stage_w
            fig_y = 1.0 - ann.position.y / _stage_h
            text_ann_lines.append(
                f'    fig.text({fig_x:.4f}, {fig_y:.4f}, '
                f'"{ann.text}", fontsize={ann.font_size}, '
                f'color="{ann.font_color}", ha="left", va="top")'
            )
    text_ann_code = "\n".join(text_ann_lines) if text_ann_lines else ""

    # --- Task 7.4: Floating legend ---
    legend_code = ""
    if chart_state.legend.visible and chart_state.series:
        # Check if any legend entries have floating positions
        floating_keys = [
            f"legend_entry_{entry.series_name}"
            for entry in chart_state.legend.entries
        ]
        has_floating = any(
            k in chart_state.elements_positions for k in floating_keys
        )
        if has_floating:
            legend_parts: list[str] = []
            legend_parts.append("    # Floating legend entries")
            for entry in chart_state.legend.entries:
                pos_key = f"legend_entry_{entry.series_name}"
                pos = chart_state.elements_positions.get(pos_key)
                if pos is None:
                    continue
                lfx = pos.x / _stage_w
                lfy = 1.0 - pos.y / _stage_h
                legend_parts.append(
                    f'    fig.text({lfx:.4f}, {lfy:.4f}, '
                    f'"\\u25CF {entry.label}", fontsize={entry.font_size}, '
                    f'color="{entry.color}", fontfamily="{entry.font_family}", '
                    f'ha="left", va="center")'
                )
            legend_code = "\n".join(legend_parts)
        else:
            legend_code = '    ax.legend(loc="best")'

    # --- Task 7.5: Data table code generation ---
    data_table_code = ""
    if chart_state.data_table is not None and chart_state.data_table.visible:
        dt = chart_state.data_table
        # Determine which series to show
        series_to_show = [s.column for s in chart_state.series if s.visible]
        n_samples = dt.max_rows if dt.max_rows else 6

        dt_lines: list[str] = []
        dt_lines.append("    # --- Data table ---")
        dt_lines.append(f"    _n_samples = min({n_samples}, len(df))")
        dt_lines.append("    if _n_samples > 0 and len(df) > 0:")
        dt_lines.append("        if len(df) <= _n_samples:")
        dt_lines.append("            _sampled_idx = list(range(len(df)))")
        dt_lines.append("        else:")
        dt_lines.append("            _sampled_idx = [int(round(i * (len(df) - 1) / (_n_samples - 1))) for i in range(_n_samples)]")

        # Build date labels — use first column as date
        first_col = str(df.columns[0])
        dt_lines.append(f'        _date_labels = [str(df["{first_col}"].iloc[i]) for i in _sampled_idx]')

        # Computed column headers
        computed_headers = [cc.label for cc in dt.computed_columns]
        dt_lines.append(f"        _computed_headers = {computed_headers!r}")
        dt_lines.append("        _col_labels = _date_labels + _computed_headers")

        # Build cell text and row labels
        dt_lines.append("        _cell_text = []")
        dt_lines.append("        _row_labels = []")
        dt_lines.append("        _row_colors = []")

        for s in chart_state.series:
            if not s.visible or s.column not in series_to_show:
                continue
            dt_lines.append(f'        _row_labels.append("{s.name}")')
            dt_lines.append(f'        _row_colors.append("{s.color}")')
            dt_lines.append("        _row_vals = []")
            dt_lines.append(f'        if "{s.column}" in df.columns:')
            dt_lines.append("            for idx in _sampled_idx:")
            dt_lines.append(f'                val = df["{s.column}"].iloc[idx]')
            dt_lines.append("                try:")
            dt_lines.append('                    _row_vals.append(f"{float(val):.2f}")')
            dt_lines.append("                except (ValueError, TypeError):")
            dt_lines.append("                    _row_vals.append(str(val))")
            dt_lines.append("        else:")
            dt_lines.append('            _row_vals = ["\\u2014"] * len(_sampled_idx)')

            # Computed column values
            for cc in dt.computed_columns:
                cv_key = f"{s.column}:{cc.label}"
                cv = dt.computed_values.get(cv_key)
                if cv is not None:
                    try:
                        dt_lines.append(f'        _row_vals.append("{float(cv):.2f}")')
                    except (ValueError, TypeError):
                        dt_lines.append(f'        _row_vals.append("{cv}")')
                else:
                    dt_lines.append('        _row_vals.append("\\u2014")')

            dt_lines.append("        _cell_text.append(_row_vals)")

        dt_lines.append("        if _cell_text and _col_labels:")
        dt_lines.append("            _table = ax.table(cellText=_cell_text, rowLabels=_row_labels,")
        dt_lines.append('                              colLabels=_col_labels, loc="bottom", cellLoc="center")')
        dt_lines.append("            _table.auto_set_font_size(False)")
        dt_lines.append(f"            _table.set_fontsize({dt.font_size})")
        dt_lines.append("            _table.scale(1, 1.4)")

        # Apply series colors to row label cells
        dt_lines.append("            for _i, _color in enumerate(_row_colors):")
        dt_lines.append("                try:")
        dt_lines.append("                    _table[_i + 1, -1].get_text().set_color(_color)")
        dt_lines.append("                except Exception:")
        dt_lines.append("                    pass")
        dt_lines.append("            plt.subplots_adjust(bottom=0.25)")

        data_table_code = "\n".join(dt_lines)

    # Build annotation comment sections
    annotations_code_parts: list[str] = []
    if vline_code:
        annotations_code_parts.append("\n    # Vertical line annotations")
        annotations_code_parts.append(vline_code)
    if text_ann_code:
        annotations_code_parts.append("\n    # Text annotations")
        annotations_code_parts.append(text_ann_code)
    annotations_code = "\n".join(annotations_code_parts) if annotations_code_parts else ""

    data_table_section = ""
    if data_table_code:
        data_table_section = f"\n{data_table_code}\n"

    script = f'''"""Auto-generated FRBSF chart — matplotlib."""

import pandas as pd
import matplotlib.pyplot as plt

# --- Load dataset from CSV ---
df = pd.read_csv("data.csv")

# --- Chart ---
if __name__ == "__main__":
    fig, ax = plt.subplots(figsize=(10, 6))

    # Title (positioned)
{title_code}

    # Axes labels
    ax.set_xlabel("{chart_state.axes.x_label}")
    ax.set_ylabel("{chart_state.axes.y_label}")

{scale_code}    # Series
{plot_code}

    # Gridlines
{grid_code}

{axis_limit_code}
{annotations_code}
{data_table_section}
{legend_code}

    plt.tight_layout()
    plt.savefig("chart.png", dpi=300)
    plt.show()
'''
    return script


# ---------------------------------------------------------------------------
# R export
# ---------------------------------------------------------------------------


def _generate_r_script(chart_state: ChartState, df: pd.DataFrame) -> str:
    """Generate a standalone ggplot2 R script."""
    # Determine the x column (first column) and y columns from series
    x_col = str(df.columns[0]).replace(" ", ".").replace("-", ".")

    # Build ggplot layers
    aes_layers: list[str] = []
    for s in chart_state.series:
        if not s.visible:
            continue
        y_col = str(s.column).replace(" ", ".").replace("-", ".")
        if s.chart_type == "bar":
            aes_layers.append(
                f'  geom_bar(aes(x = {x_col}, y = {y_col}), '
                f'stat = "identity", fill = "{s.color}")'
            )
        else:
            aes_layers.append(
                f'  geom_line(aes(x = {x_col}, y = {y_col}), '
                f'color = "{s.color}", linewidth = {s.line_width / 2})'
            )

    layers_code = " +\n".join(aes_layers) if aes_layers else '  geom_blank()'

    # --- Task 8.2: Vertical line annotations ---
    vline_layers: list[str] = []
    for ann in chart_state.annotations:
        if ann.type == "vertical_line" and ann.line_value is not None:
            style_map_vl = {"dashed": "dashed", "dotted": "dotted", "solid": "solid"}
            ls_vl = style_map_vl.get(ann.line_style, "dashed")
            xval = ann.line_value
            if isinstance(xval, str):
                vline_layers.append(
                    f'  geom_vline(xintercept = as.Date("{xval}"), '
                    f'color = "{ann.line_color}", linetype = "{ls_vl}", '
                    f'linewidth = {ann.line_width / 2})'
                )
            else:
                try:
                    year_int = int(xval)
                    vline_layers.append(
                        f'  geom_vline(xintercept = as.Date("{year_int}-01-01"), '
                        f'color = "{ann.line_color}", linetype = "{ls_vl}", '
                        f'linewidth = {ann.line_width / 2})'
                    )
                except (ValueError, TypeError):
                    vline_layers.append(
                        f'  geom_vline(xintercept = {xval}, '
                        f'color = "{ann.line_color}", linetype = "{ls_vl}", '
                        f'linewidth = {ann.line_width / 2})'
                    )

    # --- Task 8.3: Text annotations ---
    text_ann_layers: list[str] = []
    _stage_w, _stage_h = 860, 560
    for ann in chart_state.annotations:
        if ann.type == "text" and ann.text:
            # Use normalized coordinates for annotation placement
            norm_x = ann.position.x / _stage_w
            norm_y = 1.0 - ann.position.y / _stage_h
            text_ann_layers.append(
                f'  annotate("text", x = {norm_x:.4f}, y = {norm_y:.4f}, '
                f'label = "{ann.text}", size = {ann.font_size / 3:.1f}, '
                f'color = "{ann.font_color}", hjust = 0, vjust = 1)'
            )

    # Combine extra layers
    extra_layers: list[str] = []
    extra_layers.extend(vline_layers)
    extra_layers.extend(text_ann_layers)
    extra_layers_code = ""
    if extra_layers:
        extra_layers_code = " +\n" + " +\n".join(extra_layers)

    # --- Task 8.1: Title positioning ---
    title_fig_x = chart_state.title.position.x / _stage_w
    # Use hjust for horizontal positioning in theme
    theme_parts = [
        f'    plot.title = element_text(size = {chart_state.title.font_size}, '
        f'colour = "{chart_state.title.font_color}", '
        f'hjust = {title_fig_x:.4f})'
    ]
    if not chart_state.gridlines.horizontal_visible:
        theme_parts.append("    panel.grid.major.y = element_blank()")
    if not chart_state.gridlines.vertical_visible:
        theme_parts.append("    panel.grid.major.x = element_blank()")
    theme_code = ",\n".join(theme_parts)

    # Scale
    scale_code = ""
    if chart_state.axes.y_scale == "logarithmic":
        scale_code += "  scale_y_log10() +\n"
    if chart_state.axes.x_scale == "logarithmic":
        scale_code += "  scale_x_log10() +\n"

    # --- Task 8.4: Floating legend ---
    floating_keys = [
        f"legend_entry_{entry.series_name}"
        for entry in chart_state.legend.entries
    ]
    has_floating = chart_state.legend.visible and any(
        k in chart_state.elements_positions for k in floating_keys
    )

    legend_annotation_layers: list[str] = []
    if has_floating:
        legend_annotation_layers.append("  theme(legend.position = \"none\")")
        for entry in chart_state.legend.entries:
            pos_key = f"legend_entry_{entry.series_name}"
            pos = chart_state.elements_positions.get(pos_key)
            if pos is None:
                continue
            lfx = pos.x / _stage_w
            lfy = 1.0 - pos.y / _stage_h
            legend_annotation_layers.append(
                f'  annotate("text", x = {lfx:.4f}, y = {lfy:.4f}, '
                f'label = "{entry.label}", size = {entry.font_size / 3:.1f}, '
                f'color = "{entry.color}", hjust = 0, vjust = 0.5)'
            )
            # Colored point as bullet
            legend_annotation_layers.append(
                f'  annotate("point", x = {lfx - 0.02:.4f}, y = {lfy:.4f}, '
                f'color = "{entry.color}", size = 3)'
            )

    legend_layers_code = ""
    if legend_annotation_layers:
        legend_layers_code = " +\n" + " +\n".join(legend_annotation_layers)

    # --- Task 8.5: Data table code generation ---
    data_table_r_code = ""
    if chart_state.data_table is not None and chart_state.data_table.visible:
        dt = chart_state.data_table
        series_to_show = [s.column for s in chart_state.series if s.visible]
        n_samples = dt.max_rows if dt.max_rows else 6
        first_col = str(df.columns[0]).replace(" ", ".").replace("-", ".")

        dt_r_lines: list[str] = []
        dt_r_lines.append("")
        dt_r_lines.append("# --- Data table ---")
        dt_r_lines.append("library(gridExtra)")
        dt_r_lines.append(f"n_samples <- min({n_samples}, nrow(data))")
        dt_r_lines.append("if (n_samples > 0) {")
        dt_r_lines.append("  sampled_idx <- round(seq(1, nrow(data), length.out = n_samples))")
        dt_r_lines.append(f'  date_labels <- as.character(data${first_col}[sampled_idx])')

        # Build the table data frame
        dt_r_lines.append("  table_data <- data.frame(row.names = NULL)")
        dt_r_lines.append(f'  table_data$Series <- c({", ".join(repr(s.name) for s in chart_state.series if s.visible and s.column in series_to_show)})')

        # For each sampled date, add a column
        dt_r_lines.append("  for (i in seq_along(sampled_idx)) {")
        dt_r_lines.append("    col_vals <- c()")
        for s in chart_state.series:
            if not s.visible or s.column not in series_to_show:
                continue
            r_col = str(s.column).replace(" ", ".").replace("-", ".")
            dt_r_lines.append(f'    col_vals <- c(col_vals, round(data${r_col}[sampled_idx[i]], 2))')
        dt_r_lines.append("    table_data[[date_labels[i]]] <- col_vals")
        dt_r_lines.append("  }")

        # Computed columns
        for cc in dt.computed_columns:
            dt_r_lines.append(f'  comp_vals <- c()')
            for s in chart_state.series:
                if not s.visible or s.column not in series_to_show:
                    continue
                cv_key = f"{s.column}:{cc.label}"
                cv = dt.computed_values.get(cv_key)
                if cv is not None:
                    try:
                        dt_r_lines.append(f'  comp_vals <- c(comp_vals, {float(cv):.2f})')
                    except (ValueError, TypeError):
                        dt_r_lines.append(f'  comp_vals <- c(comp_vals, NA)')
                else:
                    dt_r_lines.append(f'  comp_vals <- c(comp_vals, NA)')
            dt_r_lines.append(f'  table_data${cc.label.replace(" ", ".")} <- comp_vals')

        dt_r_lines.append("  table_grob <- tableGrob(table_data, rows = NULL)")
        dt_r_lines.append("  grid.arrange(p, table_grob, nrow = 2, heights = c(3, 1))")
        dt_r_lines.append("}")

        data_table_r_code = "\n".join(dt_r_lines)

    script = f'''# Auto-generated FRBSF chart — ggplot2
library(ggplot2)

# --- Load dataset from CSV ---
data <- read.csv("data.csv")

# --- Chart ---
p <- ggplot(data) +
{layers_code}{extra_layers_code} +
{scale_code}  labs(
    title = "{chart_state.title.text}",
    x = "{chart_state.axes.x_label}",
    y = "{chart_state.axes.y_label}"
  ) +
  theme_minimal() +
  theme(
{theme_code}
  ){legend_layers_code}

print(p)
ggsave("chart.png", plot = p, width = 10, height = 6, dpi = 300)
{data_table_r_code}
'''
    return script


_INSTALL_PACKAGES_R = '''# Install required R packages
packages <- c("ggplot2")

install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  }
}

invisible(lapply(packages, install_if_missing))
cat("All packages installed.\\n")
'''


# ---------------------------------------------------------------------------
# PDF export (reportlab)
# ---------------------------------------------------------------------------


def _render_chart_image(chart_state: ChartState, df: pd.DataFrame) -> bytes:
    """Render the chart to a PNG image in memory at 300 DPI."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Detect and parse date column for x-axis
    date_col = None
    x_values = df.index
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
                if parsed.notna().sum() > len(df) * 0.5:
                    date_col = col
                    x_values = parsed
                    break
            except Exception:
                pass

    # Filter by x_min/x_max if they are date strings
    mask = pd.Series([True] * len(df), index=df.index)
    x_min = chart_state.axes.x_min
    x_max = chart_state.axes.x_max
    if date_col and isinstance(x_min, str):
        try:
            mask &= pd.to_datetime(df[date_col], errors="coerce") >= pd.Timestamp(x_min)
        except Exception:
            pass
    if date_col and isinstance(x_max, str):
        try:
            mask &= pd.to_datetime(df[date_col], errors="coerce") <= pd.Timestamp(x_max)
        except Exception:
            pass
    df_filtered = df[mask].reset_index(drop=True)
    if date_col:
        x_values = pd.to_datetime(df_filtered[date_col], errors="coerce", format="mixed")
    else:
        x_values = df_filtered.index

    # Title — positioned using canvas coordinates via fig.text()
    try:
        _stage_w, _stage_h = 860, 560
        _title_fig_x = chart_state.title.position.x / _stage_w
        _title_fig_y = 1.0 - chart_state.title.position.y / _stage_h
        fig.text(
            _title_fig_x,
            _title_fig_y,
            chart_state.title.text,
            fontsize=chart_state.title.font_size,
            color=chart_state.title.font_color,
            fontfamily=chart_state.title.font_family,
            ha="left",
            va="top",
        )
    except Exception:
        # Fallback to default centered title if positioning fails
        ax.set_title(
            chart_state.title.text,
            fontsize=chart_state.title.font_size,
            color=chart_state.title.font_color,
        )
    ax.set_xlabel(chart_state.axes.x_label)
    ax.set_ylabel(chart_state.axes.y_label)

    # Scale
    if chart_state.axes.y_scale == "logarithmic":
        ax.set_yscale("log")

    # Series
    for s in chart_state.series:
        if not s.visible:
            continue
        col = s.column
        if col not in df_filtered.columns:
            continue
        y_data = pd.to_numeric(df_filtered[col], errors="coerce")
        if s.chart_type == "bar":
            ax.bar(x_values, y_data, color=s.color, label=s.name, width=20)
        elif s.chart_type == "area":
            ax.fill_between(x_values, y_data, alpha=0.3, color=s.color, label=s.name)
            ax.plot(x_values, y_data, color=s.color, linewidth=s.line_width)
        else:
            ax.plot(x_values, y_data, color=s.color, label=s.name, linewidth=s.line_width)

    # Horizontal line annotations
    for ann in chart_state.annotations:
        if ann.type == "horizontal_line" and ann.line_value is not None:
            style_map_ann = {"dashed": "--", "dotted": ":", "solid": "-"}
            ls = style_map_ann.get(ann.line_style, ":")
            ax.axhline(y=ann.line_value, color=ann.line_color, linestyle=ls,
                       linewidth=ann.line_width, label=ann.text or None)

    # Vertical band annotations
    for ann in chart_state.annotations:
        if ann.type == "vertical_band" and ann.band_start and ann.band_end:
            try:
                ax.axvspan(pd.Timestamp(ann.band_start), pd.Timestamp(ann.band_end),
                           alpha=0.3, color=ann.band_color or "#cccccc")
            except Exception:
                pass

    # Vertical line annotations
    _vline_style_map = {"dashed": "--", "dotted": ":", "solid": "-"}
    for ann in chart_state.annotations:
        if ann.type == "vertical_line" and ann.line_value is not None:
            try:
                ls = _vline_style_map.get(ann.line_style, "--")
                xval = ann.line_value
                if isinstance(xval, str):
                    xval = pd.Timestamp(xval)
                else:
                    # Numeric value — try interpreting as a year
                    try:
                        xval = pd.Timestamp(year=int(xval), month=1, day=1)
                    except Exception:
                        pass
                ax.axvline(
                    x=xval,
                    color=ann.line_color,
                    linestyle=ls,
                    linewidth=ann.line_width,
                    label=ann.text or None,
                )
            except Exception:
                pass

    # Text annotations
    _stage_w_ann, _stage_h_ann = 860, 560
    for ann in chart_state.annotations:
        if ann.type == "text" and ann.text:
            try:
                fig_x = ann.position.x / _stage_w_ann
                fig_y = 1.0 - ann.position.y / _stage_h_ann
                fig.text(
                    fig_x,
                    fig_y,
                    ann.text,
                    fontsize=ann.font_size,
                    color=ann.font_color,
                    ha="left",
                    va="top",
                )
            except Exception:
                pass

    # Gridlines
    style_map = {"dashed": "--", "dotted": ":", "solid": "-"}
    if chart_state.gridlines.horizontal_visible:
        ls = style_map.get(chart_state.gridlines.style, "--")
        ax.yaxis.grid(True, linestyle=ls, color=chart_state.gridlines.color)
    if chart_state.gridlines.vertical_visible:
        ls = style_map.get(chart_state.gridlines.style, "--")
        ax.xaxis.grid(True, linestyle=ls, color=chart_state.gridlines.color)

    # Y-axis limits
    if chart_state.axes.y_min is not None and chart_state.axes.y_max is not None:
        ax.set_ylim(float(chart_state.axes.y_min), float(chart_state.axes.y_max))

    # Y-axis format
    y_fmt = getattr(chart_state.axes, 'y_format', 'auto')
    if y_fmt == "percent":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    elif y_fmt == "integer":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}"))

    # Legend — floating entries if positions exist, otherwise matplotlib default
    if chart_state.legend.visible and chart_state.series:
        _legend_stage_w, _legend_stage_h = 860, 560
        # Check if any legend entries have floating positions
        _floating_keys = [
            f"legend_entry_{entry.series_name}"
            for entry in chart_state.legend.entries
        ]
        _has_floating = any(
            k in chart_state.elements_positions for k in _floating_keys
        )
        if _has_floating:
            try:
                for entry in chart_state.legend.entries:
                    pos_key = f"legend_entry_{entry.series_name}"
                    pos = chart_state.elements_positions.get(pos_key)
                    if pos is None:
                        continue
                    lfx = pos.x / _legend_stage_w
                    lfy = 1.0 - pos.y / _legend_stage_h
                    # Draw colored bullet + label
                    fig.text(
                        lfx,
                        lfy,
                        f"\u25CF {entry.label}",
                        fontsize=entry.font_size,
                        color=entry.color,
                        fontfamily=entry.font_family,
                        ha="left",
                        va="center",
                    )
            except Exception:
                ax.legend(loc="best")
        else:
            ax.legend(loc="best")

    fig.autofmt_xdate()

    # Data table rendering
    if chart_state.data_table is not None and chart_state.data_table.visible:
        try:
            _dt = chart_state.data_table
            # Determine sampled indices (evenly spaced across df_filtered)
            n_rows = len(df_filtered)
            n_samples = _dt.max_rows if _dt.max_rows else min(6, n_rows)
            if n_rows > 0 and n_samples > 0:
                if n_rows <= n_samples:
                    sampled_indices = list(range(n_rows))
                else:
                    sampled_indices = [
                        int(round(i * (n_rows - 1) / (n_samples - 1)))
                        for i in range(n_samples)
                    ]

                # Build date labels for sampled columns
                date_labels = []
                for idx in sampled_indices:
                    if date_col and date_col in df_filtered.columns:
                        date_labels.append(str(df_filtered[date_col].iloc[idx]))
                    else:
                        date_labels.append(str(idx))

                # Determine which series to show
                series_to_show = [
                    s.column for s in chart_state.series if s.visible
                ]

                # Build computed column headers
                computed_headers = [cc.label for cc in _dt.computed_columns]

                # Column headers: sampled dates + computed columns
                col_labels = date_labels + computed_headers

                # Build cell text: rows = series, columns = sampled dates + computed
                cell_text = []
                cell_colors = []
                row_labels = []
                for s in chart_state.series:
                    if not s.visible or s.column not in series_to_show:
                        continue
                    row_labels.append(s.name)
                    cell_colors.append(s.color)
                    row_vals = []
                    if s.column in df_filtered.columns:
                        for idx in sampled_indices:
                            val = df_filtered[s.column].iloc[idx]
                            try:
                                row_vals.append(f"{float(val):.2f}")
                            except (ValueError, TypeError):
                                row_vals.append(str(val))
                    else:
                        row_vals = ["—"] * len(sampled_indices)

                    # Append computed column values
                    for cc in _dt.computed_columns:
                        cv_key = f"{s.column}:{cc.label}"
                        cv = _dt.computed_values.get(cv_key)
                        if cv is not None:
                            try:
                                row_vals.append(f"{float(cv):.2f}")
                            except (ValueError, TypeError):
                                row_vals.append(str(cv))
                        else:
                            row_vals.append("—")

                    cell_text.append(row_vals)

                if cell_text and col_labels:
                    # Render table below the chart using ax.table()
                    table = ax.table(
                        cellText=cell_text,
                        rowLabels=row_labels,
                        colLabels=col_labels,
                        loc="bottom",
                        cellLoc="center",
                    )
                    table.auto_set_font_size(False)
                    table.set_fontsize(_dt.font_size)
                    table.scale(1, 1.4)

                    # Apply series colors to row label cells
                    for i, color in enumerate(cell_colors):
                        try:
                            cell = table[i + 1, -1]  # row label cells
                            cell.get_text().set_color(color)
                        except Exception:
                            pass

                    # Make room for the table
                    plt.subplots_adjust(bottom=0.25)
        except Exception:
            pass

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _build_pdf(chart_image_bytes: bytes, summary: str) -> bytes:
    """Build a PDF with chart image at top, summary at bottom, FRBSF branding."""
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # FRBSF branded styles
    title_style = ParagraphStyle(
        "FRBSFTitle",
        parent=styles["Title"],
        fontName=_FRBSF_FONT,
        fontSize=18,
        textColor=rl_colors.HexColor(_FRBSF_BLUE),
        spaceAfter=12,
    )

    body_style = ParagraphStyle(
        "FRBSFBody",
        parent=styles["BodyText"],
        fontName=_FRBSF_FONT,
        fontSize=11,
        textColor=rl_colors.HexColor(_FRBSF_GRAY),
        leading=15,
        spaceAfter=8,
    )

    elements = []

    # Header
    elements.append(
        Paragraph("Federal Reserve Bank of San Francisco", title_style)
    )
    elements.append(Spacer(1, 6))

    # Chart image
    img_buf = io.BytesIO(chart_image_bytes)
    # letter width minus margins = 7 inches; keep aspect ratio
    img = RLImage(img_buf, width=7 * inch, height=4.2 * inch)
    elements.append(img)
    elements.append(Spacer(1, 18))

    # Summary
    subtitle_style = ParagraphStyle(
        "FRBSFSubtitle",
        parent=styles["Heading2"],
        fontName=_FRBSF_FONT,
        fontSize=14,
        textColor=rl_colors.HexColor(_FRBSF_LIGHT_BLUE),
        spaceAfter=8,
    )
    elements.append(Paragraph("Executive Summary", subtitle_style))

    # Split summary into paragraphs
    for para in summary.split("\n"):
        stripped = para.strip()
        if stripped:
            elements.append(Paragraph(stripped, body_style))

    doc.build(elements)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Export Service (public API)
# ---------------------------------------------------------------------------


class ExportService:
    """Generates Python, R, and PDF exports from a ChartState."""

    async def export_python(self, chart_state: ChartState) -> bytes:
        """Generate a zip with ``chart.py``, ``data.csv``, and ``requirements.txt``.

        The dataset is included as a CSV file and loaded via ``pd.read_csv``.
        """
        df = _load_dataset(chart_state.dataset_path)
        script = _generate_python_script(chart_state, df)

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_content = csv_buf.getvalue()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("chart.py", script)
            zf.writestr("data.csv", csv_content)
            zf.writestr("requirements.txt", "matplotlib\npandas\n")
        buf.seek(0)
        return buf.read()

    async def export_r(self, chart_state: ChartState) -> bytes:
        """Generate a zip with ``chart.R``, ``data.csv``, and ``install_packages.R``.

        The dataset is included as a CSV file and loaded via ``read.csv``.
        """
        df = _load_dataset(chart_state.dataset_path)
        script = _generate_r_script(chart_state, df)

        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        csv_content = csv_buf.getvalue()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("chart.R", script)
            zf.writestr("data.csv", csv_content)
            zf.writestr("install_packages.R", _INSTALL_PACKAGES_R)
        buf.seek(0)
        return buf.read()

    async def export_pdf(
        self, chart_state: ChartState, summary: str
    ) -> bytes:
        """Generate a PDF with chart image (300 DPI) at top, summary at bottom,
        and FRBSF branding.
        """
        df = _load_dataset(chart_state.dataset_path)
        chart_image = _render_chart_image(chart_state, df)
        return _build_pdf(chart_image, summary)

    async def export_pdf_from_image(
        self, image_bytes: bytes, summary: str
    ) -> bytes:
        """Generate a PDF using a pre-rendered canvas image and summary text."""
        return _build_pdf(image_bytes, summary)
