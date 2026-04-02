# Vertical Annotation Fix — Bugfix Design

## Overview

Vertical line annotations render at x=0 and have overlapping label text due to three interrelated issues: (1) the backend `AnnotationConfig.line_value` field is typed `float | None`, causing date strings to be lost during Pydantic validation, (2) the frontend falls back to `config.position.x` (which is 0) when `line_value` is null, and (3) the label text is rotated 90° at only 4px offset, causing it to visually cross the line. The fix widens the `line_value` type to accept strings, preserves date values through the pipeline, and adjusts the label offset to prevent overlap.

## Glossary

- **Bug_Condition (C)**: A vertical_line annotation is created with a date-based `line_value` (e.g., "2008", "2020-03") — the date string is lost and the line renders at x=0, and/or the label text overlaps the line
- **Property (P)**: Vertical lines render at the correct x-coordinate for their date, and labels are readable without overlapping the line
- **Preservation**: Horizontal lines, vertical bands, text annotations, drag behavior, and x-axis filtering must remain unchanged
- **AnnotationConfig**: Pydantic model in `backend/models/schemas.py` defining annotation shape including `line_value`
- **AnnotationElement**: React component in `frontend/src/components/chart/AnnotationElement.tsx` that renders all annotation types on the Konva canvas
- **dateToFraction**: Helper in `AnnotationElement.tsx` that converts a date string to a 0..1 fraction within the xLabels array
- **line_value**: Field on AnnotationConfig used for horizontal_line y-values and vertical_line x-values (date or numeric)

## Bug Details

### Bug Condition

The bug manifests when a vertical_line annotation is created with a date-based `line_value`. The `AnnotationConfig` schema types `line_value` as `float | None`, so Pydantic either coerces the date string to 0.0 or drops it to None. The frontend then falls back to `config.position.x` (default 0), placing the line at the left edge. Additionally, the label text is rendered at `x={px + 4}` with `rotation={90}`, causing it to overlap the line.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type AnnotationConfig
  OUTPUT: boolean

  RETURN input.type == "vertical_line"
         AND (
           (input.line_value IS a date string AND line_value was coerced/lost to null/0)
           OR (input.text IS NOT null AND label overlaps the vertical line)
         )
END FUNCTION
```

### Examples

- User asks AI to "add a vertical line at 2008": AI sets `line_value: "2008"`, Pydantic coerces to `line_value: null` or `0.0`, line renders at x=0 instead of the 2008 date position
- User asks for vertical lines at "2020-03" and "2020-06": both lines render at x=0, stacked on top of each other, indistinguishable
- Vertical line with label "Recession Start": text rendered at `px + 4` with 90° rotation causes the text baseline to cross the line, appearing as strikethrough
- Vertical line at numeric value 2008 (float): `dateToFraction` converts `String(2008)` → "2008" and searches xLabels, but the value never reaches the frontend because Pydantic drops it

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Horizontal line annotations with numeric `line_value` must continue to position at the correct y-coordinate
- Vertical band annotations with `band_start`/`band_end` date strings must continue to render at the correct x-axis range
- Text annotations with explicit positions must continue to render at specified (x, y) coordinates
- Dragging any annotation must continue to update its position via the drag-end handler
- X-axis date filtering via `x_min`/`x_max` must continue to correctly position all annotation types within the filtered label set

**Scope:**
All inputs that do NOT involve vertical_line annotations should be completely unaffected by this fix. This includes:
- Horizontal line annotations (numeric line_value)
- Vertical band annotations (band_start/band_end)
- Text annotations (position-based)
- Mouse drag interactions on any annotation
- Chart rendering with x-axis date filtering

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **Schema Type Mismatch**: `AnnotationConfig.line_value` in `backend/models/schemas.py` is typed as `float | None`. When the AI assistant generates a vertical_line annotation with a date string like `"2008"`, Pydantic validation either coerces it to `0.0` (failed float parse) or drops it to `None`. The date information is lost before it reaches the frontend.

2. **Frontend Fallback to position.x**: In `AnnotationElement.tsx`, the vertical_line branch checks `config.line_value != null` before calling `dateToFraction`. When `line_value` is null (due to the schema issue), it falls back to `config.position.x`, which defaults to 0, placing the line at the left edge.

3. **TypeScript Type Mismatch**: `frontend/src/types/index.ts` defines `line_value: number | null`, mirroring the backend. This needs to accept `string | number | null` to carry date values.

4. **Label Overlap**: The label text is positioned at `x={px + 4}` with `rotation={90}`. A 90° rotation pivots around the text origin, causing the text to extend downward from a point only 4px right of the line. The text visually crosses the line. The offset needs to be increased to clear the line.

## Correctness Properties

Property 1: Bug Condition — Vertical Lines Render at Correct Date Position

_For any_ vertical_line annotation where `line_value` is a date string (e.g., "2008", "2020-03") and a matching date exists in the chart's xLabels, the fixed system SHALL preserve the date string through the backend schema, deliver it to the frontend, and render the vertical line at the x-coordinate corresponding to that date on the x-axis.

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition — Vertical Line Labels Do Not Overlap the Line

_For any_ vertical_line annotation with non-null label text, the fixed system SHALL render the label text with sufficient offset from the line so that the text does not visually cross or overlap the vertical line.

**Validates: Requirements 2.3**

Property 3: Preservation — Horizontal Line Positioning Unchanged

_For any_ horizontal_line annotation with a numeric `line_value`, the fixed system SHALL produce the same y-coordinate positioning as the original system, preserving horizontal line rendering.

**Validates: Requirements 3.1**

Property 4: Preservation — Vertical Band, Text, Drag, and Filtering Unchanged

_For any_ annotation that is NOT a vertical_line (vertical_band, text, horizontal_line) or any drag/filter interaction, the fixed system SHALL produce exactly the same behavior as the original system.

**Validates: Requirements 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/models/schemas.py`

**Class**: `AnnotationConfig`

**Specific Changes**:
1. **Widen `line_value` type**: Change `line_value: float | None = None` to `line_value: float | str | None = None` so that date strings survive Pydantic validation.

**File**: `frontend/src/types/index.ts`

**Interface**: `AnnotationConfig`

**Specific Changes**:
2. **Widen `line_value` type**: Change `line_value: number | null` to `line_value: number | string | null` so the frontend can receive date strings.

**File**: `frontend/src/components/chart/AnnotationElement.tsx`

**Function**: vertical_line rendering branch

**Specific Changes**:
3. **Use `line_value` as date string directly**: When `config.line_value` is a string, pass it directly to `dateToFraction` instead of converting via `String(config.line_value)` (which already works, but now the value will actually be present).
4. **Fix label offset**: Change the label text position from `x={px + 4}` to `x={px + 8}` (or a similar increased offset) to prevent the rotated text from overlapping the vertical line.

**File**: `backend/services/ai_assistant.py`

**Function**: `_parse_chart_delta` (vertical_line defaults block)

**Specific Changes**:
5. **Preserve string line_value**: In the vertical_line defaults block, ensure that when `line_value` is a date string from the AI response, it is kept as-is rather than being coerced to float. The current code already assigns `ann["line_value"]` from the AI response dict, but the downstream `AnnotationConfig` validation was dropping it. With the schema fix, this should now work. No code change needed here, but verify the flow.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that create `AnnotationConfig` instances with date-string `line_value` values and verify the value is preserved through schema validation. Write frontend tests that render vertical_line annotations with date-based line_values and check x-positioning. Run these tests on the UNFIXED code to observe failures.

**Test Cases**:
1. **Schema Validation Test**: Create `AnnotationConfig(type="vertical_line", line_value="2008", ...)` — will fail on unfixed code because Pydantic rejects/coerces the string
2. **Multiple Vertical Lines Test**: Create two vertical_line annotations with different dates — will show both at x=0 on unfixed code
3. **Label Overlap Test**: Render a vertical_line with label text and measure the text offset from the line — will show overlap on unfixed code
4. **Round-Trip Test**: Serialize an annotation with date line_value to JSON and back — will lose the date on unfixed code

**Expected Counterexamples**:
- `AnnotationConfig(line_value="2008")` either raises ValidationError or coerces to `line_value=0.0`
- Frontend renders vertical line at x=0 regardless of date value
- Label text visually crosses the line at 4px offset with 90° rotation

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  config := AnnotationConfig(type="vertical_line", line_value=input.dateString, ...)
  ASSERT config.line_value == input.dateString  // preserved through schema
  px := dateToFraction(config.line_value, xLabels) * chartWidth
  ASSERT px > 0  // not at left edge
  ASSERT labelOffset >= 8  // no overlap
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT AnnotationConfig_fixed(input) == AnnotationConfig_original(input)
  ASSERT render_fixed(input) == render_original(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for horizontal_line, vertical_band, and text annotations, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Horizontal Line Preservation**: Verify that horizontal_line annotations with numeric line_value continue to produce the same y-coordinate positioning after the fix
2. **Vertical Band Preservation**: Verify that vertical_band annotations with band_start/band_end continue to render at the same x-axis range after the fix
3. **Text Annotation Preservation**: Verify that text annotations continue to render at the same (x, y) coordinates after the fix
4. **Drag Behavior Preservation**: Verify that dragging annotations continues to update position correctly after the fix

### Unit Tests

- Test `AnnotationConfig` schema accepts `line_value` as string, float, and None
- Test `dateToFraction` with various date formats ("2008", "2020-03", "2020-06-15")
- Test vertical_line rendering produces correct x-position for date-based line_value
- Test label text offset is sufficient to avoid overlap with the line
- Test horizontal_line rendering is unchanged with numeric line_value

### Property-Based Tests

- Generate random date strings and verify they survive AnnotationConfig round-trip (schema preservation)
- Generate random AnnotationConfig inputs with type != "vertical_line" and verify the fixed schema produces identical output to the original schema
- Generate random numeric line_values for horizontal_line and verify positioning is unchanged

### Integration Tests

- Test full AI assistant flow: send "add a vertical line at 2008" and verify the resulting annotation has line_value="2008" preserved
- Test that multiple vertical lines at different dates render at distinct x-positions on the canvas
- Test that existing horizontal lines and vertical bands are unaffected after the schema change
