# Requirements Document

## Introduction

This feature extends the FRBSF Chart Builder to detect and reproduce computed columns in data tables from reference chart images. Currently, the DataTableElement only renders raw sampled values from the dataset. Reference images (e.g., PCE.PNG) often include derived columns such as "chg" (month-over-month change between the last two sampled values). The system must detect these computed columns via vision analysis, compute the derived values from the actual dataset, and render them alongside the raw sampled values — all driven by what the reference image shows, with nothing hardcoded.

## Glossary

- **Vision_Analyzer**: The Bedrock Vision analysis pipeline (`ImageAnalyzer`) that extracts chart structure from reference images.
- **Computed_Column**: A derived data table column whose values are calculated from raw dataset values using a formula (e.g., difference, percentage change), as detected from the reference image.
- **Computed_Column_Definition**: A structured description of a computed column including its label, formula type, and the operand columns or indices it references.
- **Data_Table_Spec**: The `DataTableSpec` model returned by vision analysis describing the data table structure observed in the reference image.
- **Data_Table_Config**: The `DataTableConfig` model used in `ChartState` to configure data table rendering, including column definitions and computed column definitions.
- **Ingestion_Service**: The `DataIngestionService` that processes uploaded data and reference images, builds chart state, and computes data table values.
- **Data_Table_Element**: The frontend React component (`DataTableElement`) that renders the data table on the canvas.
- **Formula_Type**: A string identifier for a computation method (e.g., "difference", "percent_change", "ratio") that describes how a computed column derives its value from raw values.
- **Sampled_Index**: A positional index into the evenly-sampled date columns of the data table, used as an operand reference in computed column formulas.

## Requirements

### Requirement 1: Vision Detection of Computed Columns

**User Story:** As a user, I want the vision analysis to detect computed columns in the reference image's data table, so that the system can reproduce them from my actual data.

#### Acceptance Criteria

1. WHEN a reference image containing a data table with computed columns is analyzed, THE Vision_Analyzer SHALL identify each computed column and return a Computed_Column_Definition including the column label, the Formula_Type, and the operand references.
2. WHEN a reference image containing a data table with no computed columns is analyzed, THE Vision_Analyzer SHALL return an empty list of Computed_Column_Definitions in the Data_Table_Spec.
3. THE Vision_Analyzer SHALL detect at minimum the following Formula_Types: "difference" (value_a - value_b) and "percent_change" ((value_a - value_b) / value_b * 100).
4. WHEN a computed column label is visible in the reference image (e.g., "chg"), THE Vision_Analyzer SHALL extract the exact label text and include it in the Computed_Column_Definition.
5. THE Vision_Analyzer SHALL describe operand references using Sampled_Index values (e.g., index -1 for the last sampled date, index -2 for the second-to-last sampled date).

### Requirement 2: Schema Support for Computed Column Definitions

**User Story:** As a developer, I want the data models to represent computed column definitions, so that computed columns can flow from vision analysis through ingestion to rendering.

#### Acceptance Criteria

1. THE Data_Table_Spec SHALL include an optional field for a list of Computed_Column_Definitions, each containing: a label (string), a Formula_Type (string), and a list of operand references (list of Sampled_Index integers).
2. THE Data_Table_Config SHALL include an optional field for a list of Computed_Column_Definitions with the same structure as in Data_Table_Spec.
3. WHEN no computed columns are detected, THE Data_Table_Spec SHALL default the Computed_Column_Definitions field to an empty list.
4. THE Computed_Column_Definition schema SHALL be defined as a standalone model reusable by both Data_Table_Spec and Data_Table_Config.

### Requirement 3: Backend Computation of Derived Values

**User Story:** As a user, I want the system to compute derived column values from my actual dataset, so that the data table shows accurate computed results matching the reference image's layout.

#### Acceptance Criteria

1. WHEN the Ingestion_Service builds a Data_Table_Config containing Computed_Column_Definitions, THE Ingestion_Service SHALL compute the derived value for each Computed_Column_Definition for each series using the sampled data values and the specified Formula_Type and operand references.
2. WHEN the Formula_Type is "difference", THE Ingestion_Service SHALL compute the value as: value_at(operand_1) - value_at(operand_2), where operand_1 and operand_2 are Sampled_Index references.
3. WHEN the Formula_Type is "percent_change", THE Ingestion_Service SHALL compute the value as: (value_at(operand_1) - value_at(operand_2)) / value_at(operand_2) * 100.
4. IF a computed value cannot be calculated (e.g., division by zero, missing operand data), THEN THE Ingestion_Service SHALL use null for that cell value.
5. THE Ingestion_Service SHALL include the computed values in the data passed to the frontend, keyed by a generated column identifier that associates each computed value with its series and Computed_Column_Definition.
6. WHEN no Computed_Column_Definitions are present, THE Ingestion_Service SHALL produce data table output identical to the current behavior (raw sampled values only).

### Requirement 4: Frontend Rendering of Computed Columns

**User Story:** As a user, I want to see computed columns rendered in the data table alongside the raw sampled values, so that the reproduced chart matches the reference image's data table layout.

#### Acceptance Criteria

1. WHEN the Data_Table_Config contains Computed_Column_Definitions, THE Data_Table_Element SHALL render one additional column per Computed_Column_Definition after the last sampled date column for each series row.
2. THE Data_Table_Element SHALL display the Computed_Column_Definition label as the column header for each computed column.
3. THE Data_Table_Element SHALL display the precomputed derived value in each series row under the corresponding computed column header.
4. WHEN a computed cell value is null, THE Data_Table_Element SHALL display a dash character ("—").
5. WHEN no Computed_Column_Definitions are present in the Data_Table_Config, THE Data_Table_Element SHALL render identically to the current behavior (sampled date columns only).
6. THE Data_Table_Element SHALL adjust the total table width to accommodate the additional computed columns.

### Requirement 5: TypeScript Type Definitions

**User Story:** As a developer, I want TypeScript types that mirror the backend computed column models, so that the frontend has type-safe access to computed column data.

#### Acceptance Criteria

1. THE TypeScript type definitions SHALL include a ComputedColumnDefinition interface with fields: label (string), formula (string), and operands (number array).
2. THE DataTableConfig TypeScript interface SHALL include an optional computed_columns field typed as an array of ComputedColumnDefinition.
3. THE TypeScript types SHALL remain backward-compatible — existing code that does not reference computed_columns SHALL continue to compile and function without changes.

### Requirement 6: End-to-End Round-Trip Integrity

**User Story:** As a developer, I want to verify that computed column definitions survive serialization and deserialization across the full pipeline, so that no data is lost between vision analysis, backend processing, and frontend rendering.

#### Acceptance Criteria

1. FOR ALL valid Computed_Column_Definitions, serializing a Data_Table_Config to JSON and deserializing it back SHALL produce an equivalent Data_Table_Config (round-trip property).
2. FOR ALL valid ChartState objects containing Computed_Column_Definitions, serializing to JSON and deserializing back SHALL preserve the computed column definitions exactly.
3. WHEN a Data_Table_Config with Computed_Column_Definitions is sent from backend to frontend, THE frontend SHALL receive the computed_columns array with all fields intact.
