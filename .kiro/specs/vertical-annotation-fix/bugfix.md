# Bugfix Requirements Document

## Introduction

Vertical annotation lines in the chart builder are broken in two ways. First, all vertical lines render at x-position 0 (the left edge of the chart area) instead of at the correct date position on the x-axis. This happens because the `line_value` field on `AnnotationConfig` is typed as `float | None`, so date-based values (e.g., "2008", "2020-03") are either lost during schema validation or coerced to a numeric 0. The `AnnotationElement` component falls back to `config.position.x` which defaults to 0, causing all vertical lines to stack on top of each other. Second, the annotation label text is rendered with `rotation={90}` at an offset of only 4px from the line, causing the rotated text to visually overlap the line and appear as strikethrough text.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a vertical_line annotation is created with a date-based `line_value` (e.g., "2008", "2020-03", "2020-06") THEN the system positions the vertical line at x=0 (the left edge of the chart area) because the `line_value` field is typed as `float | None` in the schema, causing date strings to be lost or coerced to 0 during validation.

1.2 WHEN multiple vertical_line annotations are created for different dates THEN the system renders all lines overlapping at the same x=0 position, making them indistinguishable from each other.

1.3 WHEN a vertical_line annotation has label text THEN the system renders the text with `rotation={90}` at `x={px + 4}`, causing the rotated text to overlap the vertical line and appear as strikethrough text, making it unreadable.

### Expected Behavior (Correct)

2.1 WHEN a vertical_line annotation is created with a date-based `line_value` (e.g., "2008", "2020-03", "2020-06") THEN the system SHALL position the vertical line at the correct x-coordinate corresponding to that date on the x-axis by matching the `line_value` against the chart's x-axis labels using the `dateToFraction` helper.

2.2 WHEN multiple vertical_line annotations are created for different dates THEN the system SHALL render each line at its own distinct x-position corresponding to its respective date, so that lines are visually separated.

2.3 WHEN a vertical_line annotation has label text THEN the system SHALL render the text adjacent to the line (offset sufficiently to avoid overlap) or at the top of the line, so that the text does not visually cross or overlap the vertical line.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a horizontal_line annotation is created with a numeric `line_value` THEN the system SHALL CONTINUE TO position the horizontal line at the correct y-coordinate corresponding to that value.

3.2 WHEN a vertical_band annotation is created with `band_start` and `band_end` date strings THEN the system SHALL CONTINUE TO render the band at the correct x-axis range.

3.3 WHEN a text annotation is created with an explicit position THEN the system SHALL CONTINUE TO render the text at the specified (x, y) coordinates.

3.4 WHEN a vertical_line annotation is dragged to a new position THEN the system SHALL CONTINUE TO update the element position via the drag-end handler.

3.5 WHEN the chart's x-axis date range is filtered (via `x_min`/`x_max`) THEN the system SHALL CONTINUE TO correctly position all annotation types within the filtered label set.
