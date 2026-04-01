# Requirements Document

## Introduction

FRBSF Chart Builder is a Python-based local web application that enables users to ingest economic data (via FRED API URLs or file uploads), replicate and customize FRBSF-branded charts using a canvas-based editor, generate AI-powered executive summaries, and export charts as runnable Python/R code or PDF. The application uses a FastAPI backend, React + Konva.js frontend, SQLite for metadata, and AWS Bedrock for LLM/vision capabilities.

## Glossary

- **Application**: The FRBSF Chart Builder local web application comprising a FastAPI backend and React frontend
- **Backend**: The FastAPI Python server handling API requests, data processing, and LLM interactions
- **Frontend**: The React + Konva.js browser-based user interface for chart editing and interaction
- **Canvas_Editor**: The Konva.js-based interactive chart editing surface where chart elements are rendered and manipulated
- **Data_Ingestion_Service**: The backend component responsible for downloading data from URLs and processing uploaded files
- **FRED_Client**: The backend component that communicates with the FRED API to download economic datasets
- **Image_Analyzer**: The backend component that uses OpenCV and Bedrock Vision API to extract chart properties from reference images
- **Chart_Renderer**: The frontend component that renders chart elements on the Konva.js canvas
- **AI_Assistant**: The chat-based interface that accepts natural language commands to modify charts and answer data questions
- **Summary_Generator**: The backend component that generates executive summaries using AWS Bedrock models
- **Export_Service**: The backend component that generates Python code, R code, and PDF exports
- **Project_Store**: The SQLite-backed storage system for saving and loading user projects and metadata
- **Config_File**: A local configuration file storing API keys for FRED and AWS credentials
- **Reference_Chart**: An image of an existing chart that the system analyzes to replicate styling and layout
- **FRBSF_Branding**: The standard visual styling (colors, fonts, layout) used by the Federal Reserve Bank of San Francisco for charts
- **Chart_Element**: Any visual component on the canvas including axes, legends, gridlines, annotations, data series, labels, and data tables
- **Context_Menu**: A right-click menu that appears on text-based chart elements for inline property editing

## Requirements

### Requirement 1: Application Configuration

**User Story:** As a user, I want to configure API keys in a local config file, so that the application can connect to FRED and AWS Bedrock without hardcoding credentials.

#### Acceptance Criteria

1. WHEN the Application starts, THE Backend SHALL load API keys from the Config_File located in the application root directory
2. IF the Config_File is missing or contains invalid keys, THEN THE Backend SHALL display a descriptive error message indicating which keys are missing or malformed
3. THE Config_File SHALL store the FRED API key and AWS credential configuration as key-value pairs
4. WHEN the Config_File is updated, THE Backend SHALL apply the new configuration on the next application restart

### Requirement 2: Project Persistence

**User Story:** As a user, I want to save and load chart projects, so that I can resume work on charts across sessions.

#### Acceptance Criteria

1. WHEN the user triggers a save action, THE Project_Store SHALL persist the current chart state, dataset, and metadata to the SQLite database
2. WHEN the user selects a saved project from the project list, THE Application SHALL restore the chart state, dataset, and metadata to the Canvas_Editor
3. THE Project_Store SHALL store project name, creation timestamp, last-modified timestamp, chart configuration, dataset reference, and executive summary text for each project
4. WHEN the user deletes a project, THE Project_Store SHALL remove the project record and associated metadata from the SQLite database
5. THE Frontend SHALL display a list of saved projects with project name and last-modified timestamp

### Requirement 3: URL-Based Data Ingestion

**User Story:** As a user, I want to provide a FRED data URL so that the application downloads the dataset and generates an FRBSF-branded chart automatically.

#### Acceptance Criteria

1. WHEN the user submits a valid FRED URL, THE FRED_Client SHALL download the corresponding dataset using the FRED API and the configured API key
2. WHEN the FRED_Client successfully downloads a dataset, THE Data_Ingestion_Service SHALL store the downloaded data as a file in a local data folder
3. WHEN the dataset download completes, THE Chart_Renderer SHALL generate an FRBSF-branded chart using the downloaded data and render it on the Canvas_Editor
4. IF the user provides an invalid or unreachable URL, THEN THE Data_Ingestion_Service SHALL return a descriptive error message to the Frontend
5. IF the FRED API key is missing or invalid, THEN THE FRED_Client SHALL return an authentication error message to the Frontend

### Requirement 4: File-Based Data Ingestion

**User Story:** As a user, I want to upload a CSV or Excel file along with a reference chart image, so that the application replicates the reference chart using my uploaded data.

#### Acceptance Criteria

1. WHEN the user uploads a CSV file, THE Data_Ingestion_Service SHALL parse the file and extract tabular data
2. WHEN the user uploads an Excel file, THE Data_Ingestion_Service SHALL parse the file and extract tabular data
3. IF the uploaded file has an unsupported format (not CSV or Excel), THEN THE Data_Ingestion_Service SHALL return an error message specifying the accepted formats
4. IF the uploaded file contains malformed or unparseable data, THEN THE Data_Ingestion_Service SHALL return a descriptive parsing error message
5. WHEN the user uploads a reference chart image alongside a dataset, THE Image_Analyzer SHALL analyze the image and THE Chart_Renderer SHALL replicate the chart on the Canvas_Editor using the uploaded data

### Requirement 5: Reference Image Analysis

**User Story:** As a user, I want the system to analyze a reference chart image and extract its visual properties, so that the replicated chart matches the original styling.

#### Acceptance Criteria

1. WHEN a reference chart image is provided, THE Image_Analyzer SHALL use OpenCV to extract color palette, font characteristics, chart type, axis value ranges, legend text and positions, data table content, horizontal annotation positions, and vertical band regions
2. WHEN OpenCV extraction completes, THE Image_Analyzer SHALL send the image to the Bedrock Vision API for deeper chart understanding and structural analysis
3. THE Image_Analyzer SHALL combine OpenCV results and Bedrock Vision API results into a unified chart specification object containing chart type, color mappings, font styles, axis configurations, legend layout, annotation positions, and data table structure
4. IF the image is unreadable or not a valid chart image, THEN THE Image_Analyzer SHALL return a descriptive error message indicating the analysis failure reason
5. WHEN the chart specification is produced, THE Chart_Renderer SHALL apply the extracted properties to render a replicated chart on the Canvas_Editor


### Requirement 6: Canvas-Based Chart Rendering

**User Story:** As a user, I want charts rendered on an interactive Konva.js canvas, so that I can visually inspect and manipulate chart elements directly.

#### Acceptance Criteria

1. THE Chart_Renderer SHALL render all chart elements (axes, data series, legends, gridlines, annotations, data tables, labels) as individual Konva.js objects on the Canvas_Editor
2. THE Canvas_Editor SHALL support line charts, bar charts, and mixed (line + bar) chart styles
3. THE Chart_Renderer SHALL apply FRBSF_Branding styles (colors, fonts, layout) as the default styling for generated charts
4. WHEN chart data or configuration changes, THE Chart_Renderer SHALL re-render the affected chart elements on the Canvas_Editor within 500ms

### Requirement 7: Draggable Chart Elements

**User Story:** As a user, I want all chart elements to be floating and draggable, so that I can reposition them freely on the canvas.

#### Acceptance Criteria

1. THE Canvas_Editor SHALL allow the user to click and drag any Chart_Element (legends, axis labels, annotations, data table, title, gridlines) to a new position on the canvas
2. WHEN the user drags a Chart_Element, THE Canvas_Editor SHALL update the element position in real time as the user moves the pointer
3. WHEN the user releases a dragged Chart_Element, THE Canvas_Editor SHALL persist the new position in the chart configuration state

### Requirement 8: Context Menu for Text Elements

**User Story:** As a user, I want to right-click on text elements to access a context menu for changing size, color, and font, so that I can quickly adjust text styling inline.

#### Acceptance Criteria

1. WHEN the user right-clicks on a text-based Chart_Element, THE Canvas_Editor SHALL display a Context_Menu with options for font size, font color, and font family
2. WHEN the user selects a property change from the Context_Menu, THE Canvas_Editor SHALL apply the change to the selected text element immediately
3. WHEN the user clicks outside the Context_Menu, THE Canvas_Editor SHALL close the Context_Menu

### Requirement 9: Manual Chart Customization Controls

**User Story:** As a user, I want a control panel with manual settings for axis properties, chart elements, and visual styling, so that I can fine-tune chart appearance without using the AI assistant.

#### Acceptance Criteria

1. THE Frontend SHALL provide controls for axis properties including axis labels, axis ranges (min/max), and axis scales (linear, logarithmic)
2. THE Frontend SHALL provide controls for chart elements including legend visibility and position, gridline visibility and style, and annotation text and placement
3. THE Frontend SHALL provide controls for visual styling including color selection for data series, font family and size for text elements, and chart type selection (line, bar, mixed)
4. THE Frontend SHALL provide controls for data table visibility and label formatting
5. WHEN the user changes any manual control value, THE Chart_Renderer SHALL apply the change to the Canvas_Editor immediately

### Requirement 10: AI Assistant Chat Interface

**User Story:** As a user, I want a floating AI assistant icon that opens a chat window, so that I can issue natural language commands to modify charts and ask questions about data.

#### Acceptance Criteria

1. THE Frontend SHALL display a floating AI assistant icon in the bottom-right corner of the application window
2. WHEN the user clicks the AI assistant icon, THE Frontend SHALL open a chat window overlay
3. WHEN the user submits a natural language message in the chat window, THE AI_Assistant SHALL send the message along with the current chart context to the Bedrock model for processing
4. THE AI_Assistant SHALL maintain conversation context per chart session
5. WHEN a new chart is created or loaded, THE AI_Assistant SHALL reset the conversation context

### Requirement 11: AI-Driven Chart Modification

**User Story:** As a user, I want to describe chart changes in natural language and have them applied immediately, so that I can modify charts conversationally.

#### Acceptance Criteria

1. WHEN the user sends a chart modification command (e.g., "change to bar chart", "change legend font size to 12", "create vertical annotation band between 2020-01 and 2020-03"), THE AI_Assistant SHALL interpret the command and generate the corresponding chart configuration changes
2. WHEN the AI_Assistant produces chart configuration changes, THE Chart_Renderer SHALL apply the changes to the Canvas_Editor immediately
3. WHEN a chart modification is applied via the AI_Assistant, THE Frontend SHALL provide an undo option that reverts the chart to the state before the modification
4. THE AI_Assistant SHALL provide intelligent styling recommendations based on the current chart context and data characteristics

### Requirement 12: Executive Summary Generation

**User Story:** As a user, I want an auto-generated executive summary for my chart and data, so that I can quickly understand trends, predictions, and key insights.

#### Acceptance Criteria

1. WHEN a chart is generated or updated with new data, THE Summary_Generator SHALL automatically produce an executive summary by analyzing the dataset and chart context using a Bedrock model
2. THE Summary_Generator SHALL include trend analysis, peak and trough identification, predictions, and an economist-perspective interpretation in the executive summary
3. THE Summary_Generator SHALL use only the provided dataset and Bedrock model knowledge for analysis, without performing real-time web searches, unless the user explicitly requests external source usage
4. THE Frontend SHALL display the executive summary in an editable text area below the chart section
5. WHEN the user edits the summary text, THE Application SHALL persist the edited text as the current summary for the project

### Requirement 13: Data Q&A via AI Assistant

**User Story:** As a user, I want to ask questions about my data through the AI assistant chat, so that I can explore insights conversationally.

#### Acceptance Criteria

1. WHEN the user asks a data-related question in the AI_Assistant chat, THE AI_Assistant SHALL analyze the current dataset and chart context using a Bedrock model and return a text-based answer
2. THE AI_Assistant SHALL distinguish between chart modification commands and data Q&A questions and route them to the appropriate handler
3. THE AI_Assistant SHALL use only the provided dataset and Bedrock model knowledge for answering questions, without performing real-time web searches, unless the user explicitly requests external sources

### Requirement 14: Export as Python Code

**User Story:** As a user, I want to export my chart as standalone Python matplotlib code packaged as a zip, so that I can reproduce the chart independently.

#### Acceptance Criteria

1. WHEN the user triggers a Python export, THE Export_Service SHALL generate a standalone Python script using matplotlib that reproduces the current chart
2. THE Export_Service SHALL embed the dataset as a pandas DataFrame literal within the generated Python script
3. THE Export_Service SHALL package the Python script and a requirements.txt file (listing matplotlib and pandas) into a zip archive
4. THE Export_Service SHALL produce a zip archive that the user can unzip and run with `pip install -r requirements.txt && python chart.py` without additional setup

### Requirement 15: Export as R Code

**User Story:** As a user, I want to export my chart as standalone R ggplot2 code packaged as a zip, so that I can reproduce the chart in an R environment.

#### Acceptance Criteria

1. WHEN the user triggers an R export, THE Export_Service SHALL generate a standalone R script using ggplot2 that reproduces the current chart
2. THE Export_Service SHALL embed the dataset as an inline data frame within the generated R script
3. THE Export_Service SHALL package the R script and a dependency installation script into a zip archive
4. THE Export_Service SHALL produce a zip archive that the user can unzip and run without additional setup beyond installing listed R packages

### Requirement 16: Export as PDF

**User Story:** As a user, I want to export my chart and executive summary as a PDF document, so that I can share a polished report.

#### Acceptance Criteria

1. WHEN the user triggers a PDF export, THE Export_Service SHALL generate a PDF document with the chart image rendered at the top and the executive summary text rendered at the bottom
2. THE Export_Service SHALL render the chart at a resolution suitable for print (minimum 300 DPI)
3. THE Export_Service SHALL apply FRBSF_Branding styling to the PDF layout
