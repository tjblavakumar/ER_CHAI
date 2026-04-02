# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** — Vertical Line Date Positioning
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to concrete failing cases — date-string `line_value` values like "2008", "2020-03", "2020-06-15"
  - Test that `AnnotationConfig(type="vertical_line", line_value="2008", ...)` preserves the date string through Pydantic validation (from Bug Condition: `isBugCondition` — `input.type == "vertical_line" AND input.line_value IS a date string`)
  - Test that the TypeScript `AnnotationConfig` type accepts `string | number | null` for `line_value`
  - Test that `dateToFraction(String(config.line_value), xLabels)` returns a non-zero fraction for date-based line_values
  - Test that the label offset is sufficient (>= 8px) to prevent overlap with the vertical line (from Bug Condition: label overlaps the vertical line at 4px offset with 90° rotation)
  - Run test on UNFIXED code — expect FAILURE (Pydantic will reject/coerce date strings, label offset is only 4px)
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists)
  - Document counterexamples found: e.g., `AnnotationConfig(line_value="2008")` raises ValidationError or coerces to 0.0; label at px+4 overlaps line
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** — Non-Vertical-Line Annotation Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - **Step 1 — Observe on UNFIXED code:**
    - Observe: `AnnotationConfig(type="horizontal_line", line_value=2.0, ...)` preserves `line_value=2.0` and computes correct y-coordinate
    - Observe: `AnnotationConfig(type="vertical_band", band_start="2020-01", band_end="2020-06", ...)` renders at correct x-axis range
    - Observe: `AnnotationConfig(type="text", position=Position(x=100, y=200), ...)` renders at (100, 200)
    - Observe: Drag-end handler updates annotation position correctly for all types
  - **Step 2 — Write property-based tests capturing observed behavior:**
    - For all `horizontal_line` annotations with numeric `line_value`: y-coordinate = `chartArea.y + chartArea.height - ((line_value - yMin) / (yMax - yMin)) * chartArea.height` (from Preservation Requirements 3.1)
    - For all `vertical_band` annotations with `band_start`/`band_end`: x-position and width computed via `dateToFraction` match observed values (from Preservation Requirements 3.2)
    - For all `text` annotations: render position equals `config.position` (from Preservation Requirements 3.3)
    - For all annotations: drag-end handler fires with correct element id (from Preservation Requirements 3.4)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix vertical line annotation rendering

  - [x] 3.1 Widen `line_value` type in backend schema
    - In `backend/models/schemas.py`, change `AnnotationConfig.line_value` from `float | None = None` to `float | str | None = None`
    - This allows date strings like "2008", "2020-03" to survive Pydantic validation
    - _Bug_Condition: isBugCondition(input) where input.type == "vertical_line" AND input.line_value is a date string_
    - _Expected_Behavior: config.line_value == input.dateString (preserved through schema)_
    - _Preservation: horizontal_line annotations with numeric line_value must continue to validate and position correctly_
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Widen `line_value` type in frontend TypeScript types
    - In `frontend/src/types/index.ts`, change `line_value: number | null` to `line_value: number | string | null`
    - This allows the frontend to receive and use date string values from the backend
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Fix label offset in AnnotationElement vertical_line branch
    - In `frontend/src/components/chart/AnnotationElement.tsx`, in the `vertical_line` rendering branch, change label text position from `x={px + 4}` to `x={px + 8}` to prevent rotated text from overlapping the line
    - _Bug_Condition: label text at px + 4 with rotation={90} causes text to visually cross the line_
    - _Expected_Behavior: label text offset >= 8px so text does not overlap the vertical line_
    - _Requirements: 2.3_

  - [x] 3.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** — Vertical Line Date Positioning
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms: date strings survive schema validation, vertical lines render at correct x-positions, and labels don't overlap
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** — Non-Vertical-Line Annotation Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm horizontal_line, vertical_band, text annotations, drag behavior, and x-axis filtering all work identically to before the fix
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint — Ensure all tests pass
  - Run full test suite to confirm no regressions
  - Ensure all property-based tests (bug condition + preservation) pass
  - Ensure existing unit tests in `tests/` continue to pass
  - Ask the user if questions arise
