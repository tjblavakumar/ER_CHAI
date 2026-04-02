# Bugfix Requirements Document

## Introduction

The data table rendered below the chart area has three bugs that prevent it from matching the reference chart format (PCE.PNG). First, the date column is incorrectly included in the data table's series columns, causing it to appear as a data row. Second, the vision analysis does not robustly capture the data table's structure from the reference image — each chart may have a different table layout, number of sampled date columns, series shown, etc. Third, the DataTableElement renders all text in a hardcoded `#333` color instead of using each data series' assigned color for its row label and values.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a CSV file is ingested via `_build_chart_state_from_df` THEN the system sets `DataTableConfig.columns` to all DataFrame columns (including the date/non-numeric column), causing the date column to appear as a row in the transposed data table

1.2 WHEN `_apply_image_spec_to_chart_state` applies vision results and `spec.data_table.columns` is empty or not provided THEN the system falls back to `list(df.columns)` which again includes the date column in the data table columns

1.3 WHEN the vision model analyzes a reference image containing a data table THEN the system only extracts basic column names and visibility from the vision response via the `DataTableSpec` schema, failing to capture the full table structure which varies per chart — including the layout style (transposed vs. standard), the number of date columns sampled, which series are shown, and the overall table format

1.4 WHEN the `DataTableElement` frontend component renders series rows in the data table THEN the system uses a hardcoded fill color of `#333` for all series name labels and value cells, regardless of each series' assigned color (e.g., a series colored `#003B5C` still renders its row text in `#333`)

### Expected Behavior (Correct)

2.1 WHEN a CSV file is ingested via `_build_chart_state_from_df` THEN the system SHALL set `DataTableConfig.columns` to only the numeric/series columns, excluding any date or non-numeric columns

2.2 WHEN `_apply_image_spec_to_chart_state` applies vision results and needs to determine data table columns THEN the system SHALL use only the numeric columns from the DataFrame, excluding date/non-numeric columns

2.3 WHEN the vision model analyzes a reference image containing a data table THEN the system SHALL use robust extraction logic that captures the full data table structure as it appears in that specific chart — including layout style (transposed vs. standard), number of date columns sampled, which series are displayed, and any other structural details — storing these in an enhanced `DataTableSpec` schema that can represent varying table formats across different reference charts

2.4 WHEN the `DataTableElement` frontend component renders a series row in the data table THEN the system SHALL use the corresponding data series color for that row's label text and value cell text (e.g., if the series color is `#003B5C`, the row label and all value cells for that series SHALL be rendered in `#003B5C`)

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a FRED URL is ingested (single-series) THEN the system SHALL CONTINUE TO generate a chart state without a data table (data_table remains None)

3.2 WHEN the DataTableElement frontend component receives a correctly filtered columns list (numeric-only) THEN the system SHALL CONTINUE TO render the transposed table with series names as row labels and sampled dates as column headers

3.3 WHEN the vision model analyzes a reference image that has no data table THEN the system SHALL CONTINUE TO return `data_table: null` in the vision result

3.4 WHEN a chart has existing annotations, legend entries, gridlines, or other elements THEN the system SHALL CONTINUE TO preserve those elements unchanged when the data table fix is applied

3.5 WHEN the user drags the data table to a custom position THEN the system SHALL CONTINUE TO persist that position via `elements_positions` and honor it on re-render
