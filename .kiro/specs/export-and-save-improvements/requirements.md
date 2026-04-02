# Requirements Document

## Introduction

This feature bundles three improvements to the FRBSF Chart Builder's save and export workflows:

1. Named Chart Saves — allow users to provide and edit a custom name when saving a chart project, replacing the current auto-generated timestamp name.
2. CSV-Based Exports — include the dataset as a `data.csv` file inside the Python and R zip archives instead of embedding the entire dataset as a code literal, referencing it via `pd.read_csv("data.csv")` / `read.csv("data.csv")`.
3. Full Canvas Export — ensure PDF, Python, and R exports render every visible canvas element: data table (transposed layout with series colors and computed columns), individually positioned floating legend entries, all annotation types (horizontal lines, vertical lines, vertical bands, text annotations), and the title with its user-defined position.

## Glossary

- **Chart_Builder**: The FRBSF Chart Builder web application comprising a React frontend and a FastAPI backend.
- **Project**: A persisted chart configuration stored in the SQLite database, identified by a UUID and carrying a user-visible name.
- **Save_Dialog**: A UI component that prompts the user to enter or edit a project name before saving.
- **Export_Service**: The backend module (`export_service.py`) responsible for generating Python, R, and PDF export artifacts.
- **Canvas**: The Konva-based drawing area in the frontend that renders the chart, data table, legend entries, annotations, and title.
- **Data_Table**: A transposed table element on the Canvas showing sampled date columns, series rows with legend colors, and computed columns.
- **Floating_Legend**: A set of individually draggable legend entries on the Canvas, each with its own position stored in `elements_positions`.
- **Annotation**: A canvas element of type `text`, `horizontal_line`, `vertical_line`, or `vertical_band` defined in `ChartState.annotations`.
- **Zip_Archive**: The `.zip` file produced by Python and R exports containing the script and supporting files.
- **CSV_File**: A `data.csv` file included in the Zip_Archive containing the chart dataset.

## Requirements

### Requirement 1: Named Chart Save — New Project

**User Story:** As a chart author, I want to provide a custom name when saving a new chart, so that I can identify my saved charts by meaningful names instead of auto-generated timestamps.

#### Acceptance Criteria

1. WHEN the user clicks the Save button and no current Project exists, THE Save_Dialog SHALL display a text input pre-populated with a default name of the format `Chart <current date-time>`.
2. WHEN the user confirms the Save_Dialog with a non-empty name, THE Chart_Builder SHALL create a new Project using the entered name.
3. IF the user submits the Save_Dialog with an empty or whitespace-only name, THEN THE Save_Dialog SHALL prevent submission and display a validation message indicating that a name is required.
4. WHEN the user dismisses the Save_Dialog without confirming, THE Chart_Builder SHALL cancel the save operation and leave the application state unchanged.

### Requirement 2: Named Chart Save — Rename Existing Project

**User Story:** As a chart author, I want to rename an existing saved chart, so that I can keep my project names up to date as the chart evolves.

#### Acceptance Criteria

1. WHEN the user clicks the Save button and a current Project exists, THE Save_Dialog SHALL display a text input pre-populated with the existing Project name.
2. WHEN the user confirms the Save_Dialog with a modified name, THE Chart_Builder SHALL update the Project name along with the chart state and summary text.
3. WHEN the user confirms the Save_Dialog without changing the name, THE Chart_Builder SHALL save the chart state and summary text using the existing name.

### Requirement 3: CSV-Based Python Export

**User Story:** As a data analyst, I want the Python export to reference an external CSV file instead of embedding the dataset as a code literal, so that the generated script is concise and the data is easy to inspect or replace.

#### Acceptance Criteria

1. WHEN the Export_Service generates a Python Zip_Archive, THE Zip_Archive SHALL contain a `data.csv` file with the full dataset in CSV format.
2. WHEN the Export_Service generates a Python Zip_Archive, THE generated `chart.py` script SHALL load the dataset using `pd.read_csv("data.csv")` instead of an inline data literal.
3. THE generated `chart.py` script SHALL produce the same chart output as the current inline-literal approach when executed from the Zip_Archive directory.

### Requirement 4: CSV-Based R Export

**User Story:** As a data analyst, I want the R export to reference an external CSV file instead of embedding the dataset as a code literal, so that the generated script is concise and the data is easy to inspect or replace.

#### Acceptance Criteria

1. WHEN the Export_Service generates an R Zip_Archive, THE Zip_Archive SHALL contain a `data.csv` file with the full dataset in CSV format.
2. WHEN the Export_Service generates an R Zip_Archive, THE generated `chart.R` script SHALL load the dataset using `read.csv("data.csv")` instead of an inline `data.frame()` literal.
3. THE generated `chart.R` script SHALL produce the same chart output as the current inline-literal approach when executed from the Zip_Archive directory.

### Requirement 5: Full Canvas PDF Export — Data Table

**User Story:** As a chart author, I want the PDF export to include the data table exactly as it appears on the canvas, so that the exported document matches what I see on screen.

#### Acceptance Criteria

1. WHILE the Data_Table is visible on the Canvas, WHEN the Export_Service generates a PDF, THE rendered chart image SHALL include the Data_Table in its transposed layout.
2. THE rendered Data_Table in the PDF SHALL display series rows using the corresponding legend colors for each series.
3. WHILE computed columns are defined on the Data_Table, THE rendered Data_Table in the PDF SHALL include computed column headers and their calculated values.

### Requirement 6: Full Canvas PDF Export — Floating Legend

**User Story:** As a chart author, I want the PDF export to render each floating legend entry at its individually positioned location, so that the exported chart preserves my custom legend layout.

#### Acceptance Criteria

1. WHILE the Floating_Legend is visible on the Canvas, WHEN the Export_Service generates a PDF, THE rendered chart image SHALL include each legend entry at its stored position from `elements_positions`.
2. THE rendered legend entries in the PDF SHALL display the color swatch and label text matching the Canvas appearance.
3. WHEN the Export_Service renders the Floating_Legend, THE Export_Service SHALL use per-entry positions from `elements_positions` instead of matplotlib's built-in legend placement.

### Requirement 7: Full Canvas PDF Export — All Annotations

**User Story:** As a chart author, I want the PDF export to include all annotation types visible on the canvas, so that horizontal lines, vertical lines, vertical bands, and text annotations all appear in the exported PDF.

#### Acceptance Criteria

1. WHEN the chart state contains Annotations of type `horizontal_line`, THE rendered chart image SHALL draw each horizontal line at its `line_value` y-coordinate with the specified color, style, and width.
2. WHEN the chart state contains Annotations of type `vertical_line`, THE rendered chart image SHALL draw each vertical line at its `line_value` date position with the specified color, style, and width.
3. WHEN the chart state contains Annotations of type `vertical_band`, THE rendered chart image SHALL draw each vertical band between `band_start` and `band_end` dates with the specified color and opacity.
4. WHEN the chart state contains Annotations of type `text`, THE rendered chart image SHALL draw each text annotation at its stored position with the specified font size and color.

### Requirement 8: Full Canvas PDF Export — Title Positioning

**User Story:** As a chart author, I want the PDF export to render the chart title at the position I set on the canvas, so that the exported chart matches my layout.

#### Acceptance Criteria

1. WHEN the Export_Service renders the chart image, THE title SHALL be placed at the position defined in `ChartState.title.position` rather than matplotlib's default centered title placement.
2. THE rendered title SHALL use the font family, font size, and font color specified in `ChartState.title`.

### Requirement 9: Full Canvas Python Script Export — Canvas Elements

**User Story:** As a data analyst, I want the exported Python script to include code for all visible canvas elements, so that running the script reproduces the full chart as seen on the canvas.

#### Acceptance Criteria

1. WHILE the Data_Table is visible, THE generated `chart.py` script SHALL include matplotlib code to render the Data_Table in its transposed layout with series colors and computed columns.
2. WHILE the Floating_Legend is visible, THE generated `chart.py` script SHALL include code to position each legend entry at its stored canvas coordinates instead of using matplotlib's automatic legend.
3. WHEN Annotations of type `vertical_line` exist, THE generated `chart.py` script SHALL include `ax.axvline()` calls for each vertical line annotation.
4. WHEN Annotations of type `text` exist, THE generated `chart.py` script SHALL include `ax.annotate()` or `ax.text()` calls for each text annotation.
5. THE generated `chart.py` script SHALL position the title using `fig.text()` at the coordinates from `ChartState.title.position`.

### Requirement 10: Full Canvas R Script Export — Canvas Elements

**User Story:** As a data analyst, I want the exported R script to include code for all visible canvas elements, so that running the script reproduces the full chart as seen on the canvas.

#### Acceptance Criteria

1. WHILE the Data_Table is visible, THE generated `chart.R` script SHALL include ggplot2 or grid code to render the Data_Table in its transposed layout with series colors and computed columns.
2. WHILE the Floating_Legend is visible, THE generated `chart.R` script SHALL include code to position each legend entry at its stored canvas coordinates instead of using ggplot2's automatic legend.
3. WHEN Annotations of type `vertical_line` exist, THE generated `chart.R` script SHALL include `geom_vline()` calls for each vertical line annotation.
4. WHEN Annotations of type `text` exist, THE generated `chart.R` script SHALL include `annotate("text", ...)` calls for each text annotation.
5. THE generated `chart.R` script SHALL position the title using the coordinates from `ChartState.title.position`.

### Requirement 11: Script Round-Trip Fidelity

**User Story:** As a developer, I want confidence that the generated scripts faithfully reproduce the chart, so that exports are trustworthy.

#### Acceptance Criteria

1. FOR ALL valid ChartState objects with visible series, THE Python script generated by the Export_Service SHALL execute without errors when run with `python chart.py` from the Zip_Archive directory.
2. FOR ALL valid ChartState objects with visible series, THE R script generated by the Export_Service SHALL execute without errors when run with `Rscript chart.R` from the Zip_Archive directory.
3. FOR ALL datasets exported as CSV_File, reading the CSV_File back into a DataFrame SHALL produce a dataset equivalent to the original (round-trip property).
