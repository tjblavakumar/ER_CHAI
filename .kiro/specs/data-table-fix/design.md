# Data Table Fix — Bugfix Design

## Overview

The data table rendered below the chart has three bugs: (1) date columns are included in `DataTableConfig.columns` causing them to appear as data rows, (2) the vision analysis only extracts column names and visibility for data tables instead of the full structure (layout style, sampled dates, series shown), and (3) `DataTableElement` renders all text in hardcoded `#333` instead of using each series' assigned color. The fix targets the backend ingestion pipeline (`_build_chart_state_from_df`, `_apply_image_spec_to_chart_state`), the vision prompt and `DataTableSpec` schema, and the frontend `DataTableElement` component.

## Glossary

- **Bug_Condition (C)**: The set of conditions that trigger the three bugs — date columns in data table columns, incomplete vision extraction, and hardcoded text color
- **Property (P)**: The desired behavior — numeric-only columns, rich data table spec from vision, and series-colored text
- **Preservation**: Existing behaviors that must remain unchanged — FRED single-series ingestion (no data table), drag positioning, annotations, legend, gridlines
- **`_build_chart_state_from_df`**: Function in `backend/services/ingestion.py` that creates a default `ChartState` from an uploaded DataFrame
- **`_apply_image_spec_to_chart_state`**: Function in `backend/services/ingestion.py` that merges vision analysis results into an existing `ChartState`
- **`DataTableSpec`**: Pydantic model in `backend/models/schemas.py` used by the vision pipeline to represent extracted data table info
- **`DataTableConfig`**: Pydantic model in `backend/models/schemas.py` used in `ChartState` to configure the rendered data table
- **`DataTableElement`**: React component in `frontend/src/components/chart/DataTableElement.tsx` that renders the transposed data table on the Konva canvas

## Bug Details

### Bug Condition

The bugs manifest across three code paths:

1. **Column filtering bug**: When a CSV is ingested, `_build_chart_state_from_df` sets `DataTableConfig.columns = columns` (all DataFrame columns including date). Similarly, `_apply_image_spec_to_chart_state` falls back to `list(df.columns)` when vision columns are empty.

2. **Vision extraction bug**: When the vision model analyzes a reference image with a data table, `_parse_vision_response` only extracts `columns`, `visible`, and `font_size` into `DataTableSpec`. It does not capture layout style (transposed vs. standard), number of sampled date columns, or which series are displayed.

3. **Text color bug**: When `DataTableElement` renders series rows, it uses `fill="#333"` for all series name labels and value cells regardless of the series' assigned color.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type {df: DataFrame, visionSpec: DataTableSpec | null, renderContext: DataTableRenderProps}
  OUTPUT: boolean

  // Bug 1: date column included in data table columns
  dateColumnsIncluded := ANY col IN input.df.columns
    WHERE NOT is_numeric(input.df[col]) AND col IN dataTableConfig.columns

  // Bug 2: vision spec missing structural details
  visionIncomplete := input.visionSpec IS NOT NULL
    AND input.visionSpec.layout IS NULL
    AND input.visionSpec.num_sampled_dates IS NULL
    AND input.visionSpec.series_shown IS NULL

  // Bug 3: hardcoded text color
  hardcodedColor := input.renderContext.seriesTextColor == "#333"
    AND input.renderContext.series.color != "#333"

  RETURN dateColumnsIncluded OR visionIncomplete OR hardcodedColor
END FUNCTION
```

### Examples

- **Bug 1 example**: CSV with columns `["date", "PCE", "Core PCE"]` → `DataTableConfig.columns` is set to `["date", "PCE", "Core PCE"]` → the data table renders a "date" row with date values as numeric cells. Expected: columns should be `["PCE", "Core PCE"]` only.
- **Bug 2 example**: Reference image shows a transposed data table with 5 sampled dates and 2 series → vision extracts `{"columns": ["PCE", "Core PCE"], "visible": true, "font_size": 10}` → loses layout style and sample count. Expected: vision should also extract `layout: "transposed"`, `num_sampled_dates: 5`, `series_shown: ["PCE", "Core PCE"]`.
- **Bug 3 example**: Series "PCE" has color `#003B5C` → DataTableElement renders "PCE" label and its value cells with `fill="#333"`. Expected: label and values should render with `fill="#003B5C"`.
- **Edge case**: A DataFrame with only numeric columns and no date column → `DataTableConfig.columns` should include all columns (no filtering needed since there's no date column to exclude).

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- FRED single-series ingestion must continue to produce `data_table: None` (no data table)
- The transposed table layout (series as rows, sampled dates as columns) must continue to work when given a correctly filtered numeric-only columns list
- Vision analysis of images with no data table must continue to return `data_table: null`
- Existing annotations, legend entries, gridlines, and other chart elements must remain unchanged
- Data table drag positioning via `elements_positions` must continue to work
- The data table must remain floating/draggable — no positioning changes

**Scope:**
All inputs that do NOT involve data table column construction, vision data table extraction, or data table text rendering should be completely unaffected by this fix. This includes:
- FRED URL ingestion (single-series, no data table)
- Chart type, title, axes, series line rendering
- Legend rendering and positioning
- Annotation rendering
- Gridline rendering
- Mouse/keyboard interactions unrelated to data table

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **Column filtering omission in `_build_chart_state_from_df`**: Line `columns=columns` passes all DataFrame columns (including date) to `DataTableConfig.columns`. The function already computes `numeric_cols` but doesn't use it for the data table.

2. **Column filtering omission in `_apply_image_spec_to_chart_state`**: The fallback `list(df.columns)` includes all columns. When `spec.data_table.columns` is empty, it also falls back to all columns instead of filtering to numeric-only.

3. **Minimal `DataTableSpec` schema**: The `DataTableSpec` model only has `columns`, `visible`, and `font_size` fields. The vision prompt only asks for these three fields. The `_parse_vision_response` method only extracts these three fields. All three need to be extended to capture layout style, sampled date count, and series shown.

4. **Hardcoded fill color in `DataTableElement`**: The component receives `config` (which has `columns`) and `seriesLabels` but does not receive series color information. The `fill="#333"` is hardcoded in multiple `<Text>` elements for both series name labels and value cells.

## Correctness Properties

Property 1: Bug Condition — Numeric-Only Columns in DataTableConfig

_For any_ DataFrame ingested via `_build_chart_state_from_df` or processed via `_apply_image_spec_to_chart_state`, the resulting `DataTableConfig.columns` SHALL contain only numeric column names, excluding any date or non-numeric columns.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Rich Vision Data Table Extraction

_For any_ reference image containing a visible data table, the vision analysis pipeline SHALL extract and store the full data table structure including layout style, number of sampled date columns, and which series are displayed, in an enhanced `DataTableSpec` schema.

**Validates: Requirements 2.3**

Property 3: Bug Condition — Series-Colored Text in DataTableElement

_For any_ series row rendered in the `DataTableElement`, the component SHALL use the corresponding series color (from `SeriesConfig.color`) for that row's label text and value cell text, not a hardcoded color.

**Validates: Requirements 2.4**

Property 4: Preservation — FRED Ingestion Unchanged

_For any_ FRED URL ingestion (single-series), the system SHALL continue to produce `data_table: None` in the resulting `ChartState`, preserving the existing behavior where single-series FRED charts have no data table.

**Validates: Requirements 3.1**

Property 5: Preservation — Non-Data-Table Elements Unchanged

_For any_ chart state processed through the fix, all annotations, legend entries, gridlines, series configurations, title, axes, and element positions SHALL remain identical to their pre-fix values, preserving all existing non-data-table functionality.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/models/schemas.py`

**Models**: `DataTableSpec`

**Specific Changes**:
1. **Extend `DataTableSpec`**: Add fields for `layout` (str, default `"transposed"`), `num_sampled_dates` (int | None), and `series_shown` (list[str] | None) to capture the full table structure from vision analysis.

**File**: `backend/services/ingestion.py`

**Functions**: `_build_chart_state_from_df`, `_apply_image_spec_to_chart_state`

**Specific Changes**:
2. **Filter columns in `_build_chart_state_from_df`**: Change `columns=columns` to `columns=numeric_cols` in the `DataTableConfig` constructor so only numeric columns are included.
3. **Filter columns in `_apply_image_spec_to_chart_state`**: Replace `list(df.columns)` fallbacks with a filtered list that excludes non-numeric columns. Use `[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]`.
4. **Map new `DataTableSpec` fields**: When `spec.data_table` has the new fields (`layout`, `num_sampled_dates`, `series_shown`), propagate `num_sampled_dates` to `DataTableConfig.max_rows` if present.

**File**: `backend/services/image_analyzer.py`

**Function**: `_bedrock_vision_analyze` (prompt), `_parse_vision_response`

**Specific Changes**:
5. **Enhance vision prompt**: Update the DATA TABLE section of the prompt to ask for `layout` ("transposed" or "standard"), `num_sampled_dates` (how many date columns are shown), and `series_shown` (which series appear in the table).
6. **Update `_parse_vision_response`**: Parse the new fields from the vision response into the enhanced `DataTableSpec`.

**File**: `frontend/src/components/chart/DataTableElement.tsx`

**Component**: `DataTableElement`

**Specific Changes**:
7. **Accept series colors**: Add a `seriesColors` prop (or use existing data to build a color map) of type `Record<string, string>` mapping column names to hex colors.
8. **Use series colors for text**: Replace hardcoded `fill="#333"` on series name `<Text>` and value cell `<Text>` elements with the corresponding series color from the color map.

**File**: `frontend/src/components/CanvasEditor.tsx`

**Component**: `CanvasEditor`

**Specific Changes**:
9. **Build and pass `seriesColors` map**: Create a `seriesColors` memo that maps `series.column` (or `series.name`) to `series.color` from `chartState.series`, and pass it to `DataTableElement`.

**File**: `frontend/src/types/index.ts`

**No changes needed**: The `DataTableConfig` TypeScript type doesn't need new fields since the new `DataTableSpec` fields are backend-only (used during ingestion to set `max_rows`).

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that call `_build_chart_state_from_df` and `_apply_image_spec_to_chart_state` with DataFrames containing date columns, and inspect the resulting `DataTableConfig.columns`. Run these tests on the UNFIXED code to observe failures.

**Test Cases**:
1. **Column filtering in `_build_chart_state_from_df`**: Create a DataFrame with `["date", "PCE", "Core PCE"]`, call `_build_chart_state_from_df`, assert `data_table.columns` does not contain `"date"` (will fail on unfixed code)
2. **Column filtering in `_apply_image_spec_to_chart_state`**: Create a chart state with a `DataTableSpec` with empty columns, call `_apply_image_spec_to_chart_state`, assert `data_table.columns` does not contain date column (will fail on unfixed code)
3. **Vision extraction completeness**: Mock a vision response with a data table that includes layout and sampled dates, parse it, assert the `DataTableSpec` has `layout` and `num_sampled_dates` fields (will fail on unfixed code since fields don't exist)
4. **Text color in DataTableElement**: Render `DataTableElement` with series that have non-`#333` colors, assert the rendered text uses the series color (will fail on unfixed code)

**Expected Counterexamples**:
- `_build_chart_state_from_df` returns `data_table.columns = ["date", "PCE", "Core PCE"]` instead of `["PCE", "Core PCE"]`
- `_apply_image_spec_to_chart_state` returns `data_table.columns` including the date column
- `DataTableSpec` has no `layout` field, so parsing fails or ignores the data

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed functions produce the expected behavior.

**Pseudocode:**
```
FOR ALL df WHERE has_date_column(df) AND has_numeric_columns(df) DO
  result := _build_chart_state_from_df_fixed(df)
  ASSERT all(is_numeric(df[col]) FOR col IN result.data_table.columns)
  ASSERT no date columns IN result.data_table.columns
END FOR

FOR ALL (chartState, spec, df) WHERE spec.data_table IS NOT NULL DO
  result := _apply_image_spec_to_chart_state_fixed(chartState, spec, df)
  ASSERT all(is_numeric(df[col]) FOR col IN result.data_table.columns)
END FOR

FOR ALL seriesRow IN DataTableElement.render() DO
  ASSERT seriesRow.textColor == correspondingSeries.color
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed functions produce the same result as the original functions.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalFunction(input) = fixedFunction(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many DataFrames with varying column compositions to verify numeric filtering is correct
- It catches edge cases like DataFrames with all-numeric columns (no filtering needed) or mixed types
- It provides strong guarantees that non-data-table chart elements are unchanged

**Test Plan**: Observe behavior on UNFIXED code first for FRED ingestion and non-data-table elements, then write property-based tests capturing that behavior.

**Test Cases**:
1. **FRED Ingestion Preservation**: Verify that FRED URL ingestion continues to produce `data_table: None` after the fix
2. **Non-Data-Table Elements Preservation**: Verify that annotations, legend, gridlines, title, axes remain unchanged when data table columns are filtered
3. **All-Numeric DataFrame Preservation**: Verify that a DataFrame with only numeric columns (no date column) produces the same `data_table.columns` before and after the fix
4. **Drag Position Preservation**: Verify that data table position from `elements_positions` continues to be honored

### Unit Tests

- Test `_build_chart_state_from_df` with various DataFrame column compositions (date + numeric, all numeric, multiple date-like columns)
- Test `_apply_image_spec_to_chart_state` with empty and non-empty `DataTableSpec.columns`
- Test `_parse_vision_response` with enhanced data table fields
- Test `DataTableElement` renders correct colors for each series row

### Property-Based Tests

- Generate random DataFrames with mixed column types and verify `DataTableConfig.columns` contains only numeric columns
- Generate random `ChartState` + `ChartSpecification` pairs and verify non-data-table elements are preserved through `_apply_image_spec_to_chart_state`
- Generate random series color assignments and verify `DataTableElement` uses the correct color for each row

### Integration Tests

- Test full CSV upload flow with reference image and verify the resulting chart state has numeric-only data table columns, enhanced vision spec, and correct rendering
- Test that saving and loading a project preserves the data table configuration
- Test that the AI assistant chat can modify data table properties without reintroducing the bugs
