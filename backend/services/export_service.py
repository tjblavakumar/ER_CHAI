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
    data_literal = _df_to_python_literal(df)

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

    # Legend
    legend_code = ""
    if chart_state.legend.visible and chart_state.series:
        legend_code = '    ax.legend(loc="best")'

    script = f'''"""Auto-generated FRBSF chart — matplotlib."""

import pandas as pd
import matplotlib.pyplot as plt

# --- Embedded dataset ---
{data_literal}

df = pd.DataFrame(data)

# --- Chart ---
if __name__ == "__main__":
    fig, ax = plt.subplots(figsize=(10, 6))

    # Title
    ax.set_title("{chart_state.title.text}", fontsize={chart_state.title.font_size},
                 fontfamily="{chart_state.title.font_family}",
                 color="{chart_state.title.font_color}")

    # Axes labels
    ax.set_xlabel("{chart_state.axes.x_label}")
    ax.set_ylabel("{chart_state.axes.y_label}")

{scale_code}    # Series
{plot_code}

    # Gridlines
{grid_code}

{axis_limit_code}
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
    data_literal = _df_to_r_literal(df)

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

    # Theme / gridlines
    theme_parts = [f'    plot.title = element_text(size = {chart_state.title.font_size})']
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

    script = f'''# Auto-generated FRBSF chart — ggplot2
library(ggplot2)

# --- Embedded dataset ---
{data_literal}

# --- Chart ---
p <- ggplot(data) +
{layers_code} +
{scale_code}  labs(
    title = "{chart_state.title.text}",
    x = "{chart_state.axes.x_label}",
    y = "{chart_state.axes.y_label}"
  ) +
  theme_minimal() +
  theme(
{theme_code}
  )

print(p)
ggsave("chart.png", plot = p, width = 10, height = 6, dpi = 300)
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

    # Title
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
    if chart_state.axes.x_scale == "logarithmic":
        ax.set_xscale("log")

    # Series
    for s in chart_state.series:
        if not s.visible:
            continue
        col = s.column
        if col not in df.columns:
            continue
        if s.chart_type == "bar":
            ax.bar(df.index, df[col], color=s.color, label=s.name, width=0.8)
        else:
            ax.plot(df.index, df[col], color=s.color, label=s.name, linewidth=s.line_width)

    # Gridlines
    style_map = {"dashed": "--", "dotted": ":", "solid": "-"}
    if chart_state.gridlines.horizontal_visible:
        ls = style_map.get(chart_state.gridlines.style, "--")
        ax.yaxis.grid(True, linestyle=ls, color=chart_state.gridlines.color)
    if chart_state.gridlines.vertical_visible:
        ls = style_map.get(chart_state.gridlines.style, "--")
        ax.xaxis.grid(True, linestyle=ls, color=chart_state.gridlines.color)

    # Axis limits
    if chart_state.axes.x_min is not None and chart_state.axes.x_max is not None:
        ax.set_xlim(chart_state.axes.x_min, chart_state.axes.x_max)
    if chart_state.axes.y_min is not None and chart_state.axes.y_max is not None:
        ax.set_ylim(chart_state.axes.y_min, chart_state.axes.y_max)

    # Legend
    if chart_state.legend.visible and chart_state.series:
        ax.legend(loc="best")

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
        """Generate a zip with ``chart.py`` (matplotlib) and ``requirements.txt``.

        The dataset is embedded as a pandas DataFrame literal inside the script.
        """
        df = _load_dataset(chart_state.dataset_path)
        script = _generate_python_script(chart_state, df)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("chart.py", script)
            zf.writestr("requirements.txt", "matplotlib\npandas\n")
        buf.seek(0)
        return buf.read()

    async def export_r(self, chart_state: ChartState) -> bytes:
        """Generate a zip with ``chart.R`` (ggplot2) and ``install_packages.R``.

        The dataset is embedded as an inline ``data.frame()`` literal.
        """
        df = _load_dataset(chart_state.dataset_path)
        script = _generate_r_script(chart_state, df)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("chart.R", script)
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
