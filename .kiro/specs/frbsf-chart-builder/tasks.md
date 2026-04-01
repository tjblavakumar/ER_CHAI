# Implementation Plan: FRBSF Chart Builder

## Overview

Incremental implementation of the FRBSF Chart Builder, starting with backend data models and config, then core services (ingestion, image analysis, AI, export), followed by the React + Konva.js frontend, and finally integration wiring. Each phase builds on the previous, with property-based and unit tests embedded alongside implementation tasks.

## Tasks

- [x] 1. Project scaffolding and data models
  - [x] 1.1 Set up Python project structure with FastAPI, dependencies, and test framework
    - Create `pyproject.toml` or `requirements.txt` with FastAPI, uvicorn, pydantic, pandas, openpyxl, opencv-python-headless, boto3, hypothesis, pytest, reportlab
    - Create directory structure: `backend/`, `backend/api/`, `backend/services/`, `backend/models/`, `tests/unit/`, `tests/property/`
    - Create `conftest.py` with shared fixtures and Hypothesis strategies
    - _Requirements: 1.1_

  - [x] 1.2 Define all Pydantic data models
    - Create `backend/models/schemas.py` with all models: `AppConfig`, `FREDDataset`, `Observation`, `OpenCVResult`, `VisionResult`, `ChartSpecification`, `ChartState`, `Position`, `ChartElementState`, `AxesConfig`, `SeriesConfig`, `LegendConfig`, `LegendEntry`, `GridlineConfig`, `AnnotationConfig`, `DataTableConfig`, `FontStyles`, `FontSpec`, `LegendLayout`, `VerticalBand`, `ChartContext`, `AIResponse`, `ChartConfigDelta`, `Project`, `ProjectCreate`, `ProjectUpdate`, `ProjectSummary`, `IngestionResult`, `DatasetInfo`, `ErrorResponse`
    - _Requirements: 1.3, 2.3, 3.3, 5.3, 6.2, 11.1_

  - [x] 1.3 Implement Config Loader (`backend/services/config.py`)
    - Implement `load_config(path)` to load YAML config file and return `AppConfig`
    - Raise `ConfigError` with descriptive message listing missing/malformed keys
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 1.4 Write property tests for Config Loader
    - **Property 1: Config loading round trip**
    - **Property 2: Config validation error specificity**
    - **Validates: Requirements 1.1, 1.2**

- [x] 2. Project Store and database layer
  - [x] 2.1 Implement Project Store (`backend/services/project_store.py`)
    - Create SQLite schema with `projects` table and `idx_projects_updated_at` index
    - Implement `create`, `get`, `list_all`, `update`, `delete` methods
    - Store `chart_state` as JSON blob in SQLite
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 2.2 Write property tests for Project Store
    - **Property 3: Project save/load round trip**
    - **Property 4: Project deletion removes record**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 12.5**

  - [ ]* 2.3 Write unit tests for Project Store
    - Test CRUD operations with specific examples
    - Test edge cases: special characters in names, large chart states, missing project ID
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. FRED Client and URL-based data ingestion
  - [x] 4.1 Implement FRED Client (`backend/services/fred_client.py`)
    - Implement `parse_fred_url(url)` to extract series ID from FRED URLs, raise `ValueError` on invalid format
    - Implement `download_series(series_id)` to call FRED API and return `FREDDataset`
    - Raise `FREDAuthError` on invalid API key, `FREDNotFoundError` on invalid series
    - Implement retry logic: up to 3 retries with exponential backoff (1s, 2s, 4s)
    - _Requirements: 3.1, 3.4, 3.5_

  - [ ]* 4.2 Write property tests for FRED URL parsing
    - **Property 5: FRED URL parsing extracts series ID**
    - **Validates: Requirements 3.1**

  - [ ]* 4.3 Write property test for invalid URL rejection
    - **Property 8: Invalid URL rejection**
    - **Validates: Requirements 3.4**

  - [x] 4.4 Implement Data Ingestion Service - URL path (`backend/services/ingestion.py`)
    - Implement `ingest_from_url(url)` to download FRED data, store locally in `data/` folder, generate default FRBSF-branded chart spec
    - Implement `_store_data(df, filename)` to persist DataFrame to local file
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 4.5 Write property test for data file storage round trip
    - **Property 6: Data file storage round trip**
    - **Validates: Requirements 3.2**

  - [ ]* 4.6 Write property test for chart generation from valid data
    - **Property 7: Chart generation from valid data**
    - **Validates: Requirements 3.3, 6.2, 6.3**

- [x] 5. File-based data ingestion
  - [x] 5.1 Implement file parsing in Data Ingestion Service
    - Implement `_parse_csv(content)` and `_parse_excel(content)` methods
    - Implement `ingest_from_file(file, reference_image)` to parse uploaded CSV/Excel, validate format, store data, and generate chart spec
    - Return descriptive errors for unsupported formats and malformed data
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 5.2 Write property tests for file parsing
    - **Property 9: File parsing produces correct tabular data**
    - **Property 10: Invalid file rejection**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**

  - [ ]* 5.3 Write unit tests for file ingestion edge cases
    - Test empty CSV, single-row CSV, multi-sheet Excel, encoding issues
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. Image Analyzer
  - [x] 6.1 Implement Image Analyzer (`backend/services/image_analyzer.py`)
    - Implement `_opencv_extract(image_bytes)` to extract dominant colors, text regions, contour data using OpenCV
    - Implement `_bedrock_vision_analyze(image_bytes)` to send image to Bedrock Vision API for semantic chart understanding
    - Implement `_merge_results(cv, vision)` to combine OpenCV and Vision results into unified `ChartSpecification`
    - Implement `analyze(image_bytes)` as the main entry point orchestrating the pipeline
    - Return descriptive error on unreadable or non-chart images
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 6.2 Write property test for image analysis merge
    - **Property 11: Image analysis merge produces complete specification**
    - **Validates: Requirements 5.3**

  - [ ]* 6.3 Write property test for ChartSpecification to ChartState conversion
    - **Property 12: ChartSpecification to ChartState conversion**
    - **Validates: Requirements 5.5**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. AI Assistant Handler
  - [x] 8.1 Implement AI Assistant Handler (`backend/services/ai_assistant.py`)
    - Implement in-memory session store (`_sessions: dict[str, list[dict]]`)
    - Implement `_classify_intent(message)` to classify user message as `"chart_modify"` or `"data_qa"` using Bedrock
    - Implement `_handle_chart_modify(session_id, message, chart_context)` to generate `ChartConfigDelta` from natural language
    - Implement `_handle_data_qa(session_id, message, chart_context)` to answer data questions
    - Implement `handle_message(session_id, message, chart_context)` to route to appropriate handler
    - Implement `reset_session(session_id)` to clear conversation history
    - Implement retry logic: up to 2 retries with 2s delay for Bedrock calls
    - _Requirements: 10.3, 10.4, 10.5, 11.1, 11.4, 13.1, 13.2, 13.3_

  - [ ]* 8.2 Write property tests for AI Assistant
    - **Property 15: AI session lifecycle**
    - **Property 16: AI intent classification output domain**
    - **Property 17: AI response structure validity**
    - **Validates: Requirements 10.3, 10.4, 10.5, 11.1, 13.1, 13.2**

- [x] 9. Chart state management utilities
  - [x] 9.1 Implement ChartConfigDelta application and undo logic
    - Create `backend/services/chart_state_utils.py`
    - Implement `apply_delta(state, delta)` to merge `ChartConfigDelta` into `ChartState`, producing a new valid state
    - Implement element position update logic for `elements_positions` dict
    - Implement chart element property change logic (font_size, font_color, font_family) preserving other properties
    - _Requirements: 7.3, 8.2, 9.5, 11.2, 11.3_

  - [ ]* 9.2 Write property tests for chart state management
    - **Property 13: Element position update persistence**
    - **Property 14: Chart element property changes applied correctly**
    - **Property 18: ChartConfigDelta application produces valid state**
    - **Property 19: Undo restores previous state**
    - **Validates: Requirements 7.3, 8.2, 9.5, 11.2, 11.3**

- [x] 10. Summary Generator
  - [x] 10.1 Implement Summary Generator (`backend/services/summary_generator.py`)
    - Implement `generate(dataset, chart_context)` to produce executive summary using Bedrock
    - Include trend analysis, peak/trough identification, predictions, economist-perspective interpretation
    - Use only provided dataset and Bedrock model knowledge (no web searches unless user requests)
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ]* 10.2 Write property test for summary generation
    - **Property 20: Summary generation returns non-empty result**
    - **Validates: Requirements 12.1**

- [x] 11. Export Service
  - [x] 11.1 Implement Export Service (`backend/services/export_service.py`)
    - Implement `export_python(chart_state)` to generate zip with `chart.py` (matplotlib) and `requirements.txt` (matplotlib, pandas), embedding dataset as DataFrame literal
    - Implement `export_r(chart_state)` to generate zip with `chart.R` (ggplot2) and `install_packages.R`, embedding dataset as inline data frame
    - Implement `export_pdf(chart_state, summary)` to generate PDF with chart image (300 DPI min) at top, summary text at bottom, FRBSF branding
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 15.1, 15.2, 15.3, 15.4, 16.1, 16.2, 16.3_

  - [ ]* 11.2 Write property tests for Export Service
    - **Property 21: Python export produces valid self-contained zip**
    - **Property 22: R export produces valid self-contained zip**
    - **Property 23: PDF export produces valid document**
    - **Validates: Requirements 14.1, 14.2, 14.3, 15.1, 15.2, 15.3, 16.1, 16.2**

  - [ ]* 11.3 Write unit tests for Export Service
    - Test specific chart configurations, edge cases (no data, single data point)
    - Verify Python script syntax, R script structure, PDF content
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 15.1, 15.2, 15.3, 15.4, 16.1, 16.2, 16.3_

- [x] 12. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Backend API Router
  - [x] 13.1 Implement API routes (`backend/api/routes.py`)
    - `POST /api/ingest/url` — accept FRED URL, call ingestion service, return chart config
    - `POST /api/ingest/upload` — accept multipart file + optional reference image, call ingestion service
    - `POST /api/ai/chat` — accept message + chart context, call AI assistant handler
    - `POST /api/ai/reset` — reset AI session
    - `POST /api/summary/generate` — accept dataset + chart context, return summary
    - `GET /api/export/python/{id}`, `GET /api/export/r/{id}`, `GET /api/export/pdf/{id}` — export endpoints returning file downloads
    - `GET/POST/PUT/DELETE /api/projects` and `GET /api/projects/{id}` — project CRUD
    - `GET /api/health` — health check
    - _Requirements: 3.1, 3.4, 3.5, 4.1, 4.3, 4.4, 5.4, 10.3, 11.2, 12.1, 14.1, 15.1, 16.1, 2.1, 2.2, 2.4, 2.5_

  - [x] 13.2 Implement structured error handling middleware
    - Return `ErrorResponse` JSON with appropriate HTTP status codes for all error scenarios
    - Map backend exceptions to error codes per the design error handling table
    - _Requirements: 1.2, 3.4, 3.5, 4.3, 4.4, 5.4_

  - [x] 13.3 Create FastAPI application entry point (`backend/main.py`)
    - Load config on startup, initialize all services, mount API router
    - Display descriptive error on config failure
    - Serve static frontend files
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 14. Checkpoint - Ensure backend is fully functional
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Frontend scaffolding and state management
  - [ ] 15.1 Set up React project with dependencies
    - Initialize React project with TypeScript, Konva.js (`react-konva`, `konva`), zustand for state management, axios for HTTP
    - Create directory structure: `src/components/`, `src/store/`, `src/api/`, `src/types/`
    - _Requirements: 6.1_

  - [ ] 15.2 Define TypeScript types and API client
    - Create `src/types/index.ts` with all frontend types matching backend models: `ChartState`, `ChartConfigDelta`, `ProjectSummary`, `ChatMessage`, `DatasetInfo`, etc.
    - Create `src/api/client.ts` with axios-based API client for all backend endpoints
    - Implement centralized error handler displaying toast notifications
    - _Requirements: 2.5, 3.4, 4.3_

  - [ ] 15.3 Implement Zustand store (`src/store/appStore.ts`)
    - Define `AppState` with project, chart, data, AI chat, summary, and UI state
    - Implement chart history (undo stack) with `chartHistory` and `historyIndex`
    - _Requirements: 2.2, 7.3, 11.3_

- [ ] 16. Canvas Editor and chart rendering
  - [ ] 16.1 Implement Canvas Editor (`src/components/CanvasEditor.tsx`)
    - Create Konva.js `Stage` and `Layer` components
    - Render chart elements as individual Konva nodes based on `ChartState`
    - Re-render affected elements within 500ms on chart config changes
    - _Requirements: 6.1, 6.4_

  - [ ] 16.2 Implement chart element components
    - Create `AxisElement`, `DataSeriesElement`, `LegendElement`, `GridlineElement`, `AnnotationElement`, `DataTableElement`, `TitleElement` as React-Konva components
    - Support line charts, bar charts, and mixed chart styles
    - Apply FRBSF branding styles (colors, fonts, layout) as defaults
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 16.3 Implement drag-and-drop for all chart elements
    - Make all chart elements draggable (legends, axis labels, annotations, data table, title, gridlines)
    - Update element position in real time during drag
    - Persist new position to chart state on drag end
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 16.4 Implement Context Menu (`src/components/ContextMenu.tsx`)
    - Show floating context menu on right-click over text-based chart elements
    - Provide options for font size, font color, font family
    - Apply changes immediately on selection
    - Close on outside click
    - _Requirements: 8.1, 8.2, 8.3_

- [ ] 17. Controls Panel and manual customization
  - [ ] 17.1 Implement Controls Panel (`src/components/ControlsPanel.tsx`)
    - Axis controls: labels, ranges (min/max), scales (linear, logarithmic)
    - Chart type selector: line, bar, mixed
    - Series color pickers
    - Font family/size selectors for text elements
    - Legend visibility and position controls
    - Gridline visibility and style controls
    - Annotation text and placement editor
    - Data table visibility toggle and label formatting
    - Apply changes to canvas immediately on value change
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 18. AI Chat interface
  - [ ] 18.1 Implement AI Chat Window (`src/components/AIChatWindow.tsx`)
    - Floating AI assistant icon in bottom-right corner
    - Click to open chat window overlay
    - Message list with user/assistant messages
    - Input field for natural language commands
    - Send message with current chart context to backend
    - Display undo button for last AI-driven chart modification
    - _Requirements: 10.1, 10.2, 10.3, 11.2, 11.3_

  - [ ] 18.2 Wire AI chat to chart state
    - On `chart_modify` response, apply `ChartConfigDelta` to chart state and push previous state to undo stack
    - On `data_qa` response, display text answer in chat
    - Reset AI session on new chart create/load
    - _Requirements: 10.4, 10.5, 11.1, 11.2, 11.3, 13.1, 13.2_

- [ ] 19. Summary Editor and Project List
  - [ ] 19.1 Implement Summary Editor (`src/components/SummaryEditor.tsx`)
    - Editable text area below the chart section
    - Display auto-generated summary
    - Persist user edits as current summary for the project
    - _Requirements: 12.4, 12.5_

  - [ ] 19.2 Implement Project List (`src/components/ProjectList.tsx`)
    - Sidebar list showing saved projects with name and last-modified timestamp
    - Click to load project (restore chart state, dataset, metadata to canvas)
    - Delete button per entry
    - Save action to persist current chart state, dataset, and metadata
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

- [ ] 20. Export Toolbar
  - [ ] 20.1 Implement Export Toolbar (`src/components/ExportToolbar.tsx`)
    - Buttons for Python, R, and PDF export
    - Trigger download of zip/PDF on click via backend export endpoints
    - _Requirements: 14.1, 15.1, 16.1_

- [ ] 21. App Shell and integration wiring
  - [ ] 21.1 Implement App Shell (`src/components/App.tsx`)
    - Top-level layout: project list sidebar, main canvas area, controls panel, summary editor, export toolbar, AI chat overlay
    - Wire all components to Zustand store
    - Implement network error persistent banner
    - _Requirements: 6.1, 9.1, 10.1, 12.4, 2.5_

  - [ ] 21.2 Wire data ingestion flows end-to-end
    - FRED URL input → backend ingestion → chart rendered on canvas
    - File upload (CSV/Excel + optional reference image) → backend ingestion → chart rendered on canvas
    - Auto-generate executive summary on chart creation/update
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.5, 5.5, 12.1_

- [ ] 22. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend (Python) is implemented first, then frontend (React + TypeScript), then integration
