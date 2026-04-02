# Implementation Plan: Data Table Computed Columns

## Overview

Extend the FRBSF Chart Builder to detect computed columns in reference chart images via vision analysis, compute derived values from actual data on the backend, and render them in the frontend data table. The implementation flows through four layers: schema models, vision prompt/parsing, ingestion computation, and frontend rendering. Nothing is hardcoded — the system reproduces whatever the reference image shows.

## Tasks

- [x] 1. Add ComputedColumnDefinition model and extend backend schemas
  - [x] 1.1 Create `ComputedColumnDefinition` Pydantic model in `backend/models/schemas.py`
    - Add standalone model with fields: `label: str`, `formula: str`, `operands: list[int]`
    - This model is reused by both `DataTableSpec` and `DataTableConfig`
    - _Requirements: 2.1, 2.4_

  - [x] 1.2 Add `computed_columns` field to `DataTableSpec` in `backend/models/schemas.py`
    - Add `computed_columns: list[ComputedColumnDefinition] = []`
    - Default to empty list when no computed columns detected
    - _Requirements: 2.1, 2.3_

  - [x] 1.3 Add `computed_columns` and `computed_values` fields to `DataTableConfig` in `backend/models/schemas.py`
    - Add `computed_columns: list[ComputedColumnDefinition] = []`
    - Add `computed_values: dict[str, float | None] = {}`
    - _Requirements: 2.2, 2.3_

  - [ ]* 1.4 Write property test: Schema acceptance of computed column definitions (Property 3)
    - **Property 3: Schema acceptance of computed column definitions**
    - **Validates: Requirements 2.1, 2.2, 2.4**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random `ComputedColumnDefinition` lists, construct `DataTableSpec` and `DataTableConfig`, verify acceptance and round-trip through `model_dump()` / construction

  - [ ]* 1.5 Write property test: DataTableConfig serialization round-trip (Property 7)
    - **Property 7: DataTableConfig serialization round-trip**
    - **Validates: Requirements 6.1, 6.2**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random `DataTableConfig` with `computed_columns` and `computed_values`, serialize to JSON via `model_dump_json()`, deserialize back via `DataTableConfig.model_validate_json()`, verify equivalence

- [x] 2. Checkpoint — Ensure schema tests and all existing tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `pytest tests/ -v`

- [x] 3. Update vision prompt and parsing to detect computed columns
  - [x] 3.1 Update the vision prompt in `ImageAnalyzer._bedrock_vision_analyze` in `backend/services/image_analyzer.py`
    - Extend the DATA TABLE section of the prompt to ask the model to detect computed/derived columns
    - Ask for each computed column's label, formula type ("difference", "percent_change"), and which sampled date column indices it references (e.g., [-1, -2])
    - Do NOT hardcode specific column names — the prompt must ask the model to detect whatever is in the image
    - _Requirements: 1.1, 1.3, 1.4, 1.5_

  - [x] 3.2 Update `_parse_vision_response` in `backend/services/image_analyzer.py`
    - Parse `computed_columns` from the vision response's `data_table` object
    - Construct `ComputedColumnDefinition` instances for each valid entry
    - Skip malformed entries (missing fields), log a warning
    - Default to `[]` when `computed_columns` is absent or null
    - _Requirements: 1.1, 1.2_

  - [ ]* 3.3 Write property test: Vision parsing preserves computed columns (Property 1)
    - **Property 1: Vision parsing preserves computed columns**
    - **Validates: Requirements 1.1**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random vision JSON dicts with `computed_columns` arrays, parse via `_parse_vision_response`, verify field preservation

  - [ ]* 3.4 Write property test: Vision parsing defaults to empty computed columns (Property 2)
    - **Property 2: Vision parsing defaults to empty computed columns**
    - **Validates: Requirements 1.2, 2.3**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random vision JSON dicts without `computed_columns`, parse, verify `computed_columns == []`

- [x] 4. Implement backend computation of derived values in ingestion service
  - [x] 4.1 Add `_compute_derived_value` helper function in `backend/services/ingestion.py`
    - Implement formula computation: "difference" → `a - b`, "percent_change" → `(a - b) / b * 100`
    - Return `None` for division by zero, missing operands, or unrecognized formula types
    - _Requirements: 3.2, 3.3, 3.4_

  - [x] 4.2 Update `_apply_image_spec_to_chart_state` in `backend/services/ingestion.py`
    - When `spec.data_table.computed_columns` is non-empty, copy definitions to `DataTableConfig.computed_columns`
    - For each series column × each computed column definition, resolve sampled indices to actual data values and apply the formula via `_compute_derived_value`
    - Store results in `DataTableConfig.computed_values` keyed by `"{series_column}:{label}"`
    - When no computed columns are present, behavior must be identical to current (no computed_columns, no computed_values)
    - _Requirements: 3.1, 3.5, 3.6_

  - [ ]* 4.3 Write property test: Formula computation correctness (Property 4)
    - **Property 4: Formula computation correctness**
    - **Validates: Requirements 3.2, 3.3, 3.4**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random (a, b) float pairs, apply each formula, verify arithmetic; include zero and None edge cases

  - [ ]* 4.4 Write property test: Computation completeness (Property 5)
    - **Property 5: Computation completeness**
    - **Validates: Requirements 3.1, 3.5**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random DataFrames (1-4 numeric cols) and 1-3 computed column defs, run computation, verify N×M keys in `computed_values`

  - [ ]* 4.5 Write property test: No computed columns preserves backward compatibility (Property 6)
    - **Property 6: No computed columns preserves backward compatibility**
    - **Validates: Requirements 3.6, 4.5**
    - Test file: `tests/property/test_computed_columns.py`
    - Generate random DataFrames with empty `computed_columns`, verify output matches current behavior (empty computed_columns, empty computed_values)

- [x] 5. Checkpoint — Ensure backend tests and all existing tests pass
  - Ensure all tests pass, ask the user if questions arise.
  - Run: `pytest tests/ -v`

- [x] 6. Add TypeScript types and update frontend rendering
  - [x] 6.1 Add `ComputedColumnDefinition` interface to `frontend/src/types/index.ts`
    - Add interface with fields: `label: string`, `formula: string`, `operands: number[]`
    - _Requirements: 5.1_

  - [x] 6.2 Extend `DataTableConfig` TypeScript interface in `frontend/src/types/index.ts`
    - Add optional `computed_columns?: ComputedColumnDefinition[]`
    - Add optional `computed_values?: Record<string, number | null>`
    - Existing code that does not reference these fields must continue to compile
    - _Requirements: 5.2, 5.3_

  - [x] 6.3 Update `DataTableElement.tsx` to render computed columns
    - Read `computed_columns` and `computed_values` from config (default to `[]` and `{}` if undefined)
    - After the sampled date columns, render one additional column per `ComputedColumnDefinition`
    - Header text = the definition's `label`
    - Cell value = lookup `computed_values["{series_column}:{label}"]`, format as number or display "—" if null/undefined
    - Adjust `tableWidth` calculation to include the extra computed columns
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 7. Final checkpoint — Ensure ALL tests pass including all previous specs' tests
  - Run the FULL test suite: `pytest tests/ -v`
  - This MUST include ALL previous spec tests:
    - `tests/property/test_vertical_annotation_bug.py`
    - `tests/property/test_vertical_annotation_preservation.py`
    - `tests/property/test_data_table_bug.py`
    - `tests/property/test_data_table_preservation.py`
    - `tests/property/test_computed_columns.py`
  - Also includes all unit tests in `tests/unit/`
  - Verify no regressions in any existing functionality
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Checkpoints ensure incremental validation
- Nothing is hardcoded — the vision prompt asks the model to detect whatever computed columns exist in the reference image
- All existing data table functionality, vertical annotation fixes, and other features must continue to work
