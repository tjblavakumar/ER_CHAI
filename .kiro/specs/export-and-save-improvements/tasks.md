# Implementation Plan: Export and Save Improvements

## Overview

Incremental implementation of three improvement areas: (1) Named chart saves with a save dialog, (2) CSV-based Python/R exports replacing inline data literals, (3) Full canvas export rendering all visible elements in PDF, Python, and R outputs. Each task builds on the previous, with property tests validating correctness properties from the design.

## Tasks

- [ ] 1. Add named save dialog to the frontend
  - [x] 1.1 Add `currentProjectName` state and setter to `appStore.ts`
    - Add `currentProjectName: string | null` field, `setCurrentProjectName` action
    - Set it when a project is loaded in `ProjectList.tsx` (`handleLoad`), clear on `resetForNewChart`
    - _Requirements: 1.1, 2.1_

  - [x] 1.2 Create `SaveDialog` component in `ProjectList.tsx`
    - Inline modal with text input, confirm/cancel buttons
    - Pre-populate with `currentProjectName` (existing project) or `Chart <datetime>` (new project)
    - Validate trimmed name is non-empty; show inline error if empty/whitespace-only
    - Close on cancel or Escape without saving
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3_

  - [x] 1.3 Wire `SaveDialog` into `handleSave` flow in `ProjectList.tsx`
    - Show dialog instead of immediately saving
    - On confirm: call `createProject` with entered name (new) or `updateProject` with name + chart state + summary (existing)
    - Pass name to `ProjectCreate` / `ProjectUpdate` payloads in `api/client.ts`
    - Update `currentProjectName` in store after successful save
    - _Requirements: 1.2, 2.2, 2.3_

- [x] 2. Checkpoint — Verify named save works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 3. Implement CSV-based exports in the backend
  - [x] 3.1 Modify `export_python` to include `data.csv` and use `pd.read_csv`
    - Write `df.to_csv(buf, index=False)` into the zip as `data.csv`
    - Update `_generate_python_script` to emit `pd.read_csv("data.csv")` instead of calling `_df_to_python_literal`
    - Keep `_df_to_python_literal` in the codebase (no deletion) but stop calling it from `export_python`
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 Modify `export_r` to include `data.csv` and use `read.csv`
    - Write `df.to_csv(buf, index=False)` into the zip as `data.csv`
    - Update `_generate_r_script` to emit `read.csv("data.csv")` instead of calling `_df_to_r_literal`
    - Keep `_df_to_r_literal` in the codebase (no deletion) but stop calling it from `export_r`
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 3.3 Write property test: Python export zip contains data.csv and script references it
    - **Property 2: Python export zip contains data.csv and script references it**
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 3.4 Write property test: R export zip contains data.csv and script references it
    - **Property 3: R export zip contains data.csv and script references it**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]* 3.5 Write property test: CSV dataset round-trip fidelity
    - **Property 4: CSV dataset round-trip fidelity**
    - **Validates: Requirements 11.3**

- [x] 4. Checkpoint — Verify CSV-based exports
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement full canvas rendering in `_render_chart_image` (PDF export)
  - [x] 5.1 Add title positioning using `fig.text()` at canvas coordinates
    - Replace `ax.set_title()` with `fig.text()` using `_canvas_to_fig` coordinate mapping
    - Use font family, font size, and font color from `chart_state.title`
    - _Requirements: 8.1, 8.2_

  - [x] 5.2 Add vertical line annotation rendering
    - For annotations with `type == "vertical_line"`, call `ax.axvline()` at the `line_value` date position
    - Apply specified color, line style, and line width
    - _Requirements: 7.2_

  - [x] 5.3 Add text annotation rendering
    - For annotations with `type == "text"`, call `ax.text()` at the annotation position
    - Apply specified font size and font color
    - _Requirements: 7.4_

  - [x] 5.4 Add floating legend rendering
    - Disable matplotlib's built-in legend when floating legend entries have positions in `elements_positions`
    - Iterate `chart_state.legend.entries` and draw each at its position using `fig.text()` with a color marker
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.5 Add data table rendering
    - When `chart_state.data_table` is visible, render the transposed table below the chart area
    - Display series rows with legend colors, sampled date columns, and computed columns with values
    - Use `matplotlib.table.Table` or manual `ax.text()` calls
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 5.6 Write property test: Chart image renders without error for all element combinations
    - **Property 5: Chart image renders without error for all element combinations**
    - **Validates: Requirements 5.1, 6.1, 7.1, 7.2, 7.3, 7.4**

- [x] 6. Checkpoint — Verify full canvas PDF rendering
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement full canvas code generation in `_generate_python_script`
  - [x] 7.1 Add title positioning via `fig.text()` in generated Python script
    - Replace `ax.set_title()` with `fig.text()` using canvas-to-figure coordinate mapping
    - _Requirements: 9.5_

  - [x] 7.2 Add `ax.axvline()` calls for vertical line annotations in generated Python script
    - Emit `ax.axvline()` for each annotation with `type == "vertical_line"`
    - _Requirements: 9.3_

  - [x] 7.3 Add `ax.text()` / `ax.annotate()` calls for text annotations in generated Python script
    - Emit text annotation code for each annotation with `type == "text"`
    - _Requirements: 9.4_

  - [x] 7.4 Add floating legend code generation in Python script
    - Emit per-entry `fig.text()` with colored markers instead of `ax.legend()`
    - _Requirements: 9.2_

  - [x] 7.5 Add data table code generation in Python script
    - Emit matplotlib table rendering code when `data_table` is visible
    - Include transposed layout with series colors and computed columns
    - _Requirements: 9.1_

  - [ ]* 7.6 Write property test: Python script contains rendering code for all visible elements
    - **Property 6: Python script contains rendering code for all visible elements**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

  - [ ]* 7.7 Write property test: Generated Python script compiles without syntax errors
    - **Property 8: Generated Python script compiles without syntax errors**
    - **Validates: Requirements 11.1, 3.3**

- [ ] 8. Implement full canvas code generation in `_generate_r_script`
  - [x] 8.1 Add title positioning in generated R script
    - Use `grid::grid.text()` or `theme(plot.title = ...)` with coordinates from `ChartState.title.position`
    - _Requirements: 10.5_

  - [x] 8.2 Add `geom_vline()` calls for vertical line annotations in generated R script
    - Emit `geom_vline()` for each annotation with `type == "vertical_line"`
    - _Requirements: 10.3_

  - [x] 8.3 Add `annotate("text", ...)` calls for text annotations in generated R script
    - Emit text annotation code for each annotation with `type == "text"`
    - _Requirements: 10.4_

  - [x] 8.4 Add floating legend code generation in R script
    - Emit per-entry `annotate()` calls with colored points/labels instead of ggplot2 auto legend
    - _Requirements: 10.2_

  - [x] 8.5 Add data table code generation in R script
    - Emit `gridExtra::tableGrob()` or `annotation_custom()` code when `data_table` is visible
    - Include transposed layout with series colors and computed columns
    - _Requirements: 10.1_

  - [ ]* 8.6 Write property test: R script contains rendering code for all visible elements
    - **Property 7: R script contains rendering code for all visible elements**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

  - [ ]* 8.7 Write property test: Generated R script is syntactically well-formed
    - **Property 9: Generated R script is syntactically well-formed**
    - **Validates: Requirements 11.2, 4.3**

- [x] 9. Update existing unit tests for new export behavior
  - Update `tests/unit/test_export.py` to reflect CSV-based exports (zip now contains `data.csv`, script uses `pd.read_csv` / `read.csv`)
  - Add unit test cases for chart states with all annotation types, data table, and floating legend
  - _Requirements: 3.1, 3.2, 4.1, 4.2, 5.1, 6.1, 7.1, 7.2, 7.3, 7.4_

- [ ]* 10. Write property test: Whitespace-only names are rejected
  - **Property 1: Whitespace-only names are rejected**
  - **Validates: Requirements 1.3**

- [x] 11. Final checkpoint — Run full test suite
  - Ensure ALL tests pass including all previous specs' tests (`pytest tests/` covering unit, property, and all spec test files)
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- All changes are additive — existing functionality must continue to work
- The `_df_to_python_literal` and `_df_to_r_literal` helpers are kept but no longer called by export methods
