# CHAI : Chart AI Assistant v3.1

An AI-powered web application for creating, customizing, and exporting publication-quality economic charts. Built with FastAPI (Python) backend and React + Konva.js frontend, powered by AWS Bedrock (Claude Sonnet 4.5) for AI-driven chart editing, Vision AI image analysis, and executive summary generation.

## Features

### 1. Data Ingestion
- **FRED API**: Paste a FRED URL to automatically download economic data and generate a chart, with optional reference image to mimic styling via Vision AI
- **File Upload**: Upload CSV or Excel files with optional reference chart image
- **Chart Preview Overlay**: On data upload, AI generates multiple chart style options (line, area, bar, stacked bar, stacked bar + line) displayed in a carousel overlay. User picks one to start customizing — only applicable chart types are shown for each dataset
- **Reference Image Analysis**: OpenCV + AWS Bedrock Vision (20-field comprehensive prompt) extracts colors, chart type, annotations, horizontal lines, vertical bands, axis formatting, gridlines, title, and layout from reference images
- **Smart Y-Axis Range**: Vision AI y-axis values are sanity-checked against actual data to prevent scale mismatches
- **Visual Distinction**: FRED URL input (blue) and CSV/Excel upload (green) are color-coded for easy identification
- **Smart Long-Format Detection**: Automatically pivots long-format data (date, key, value) to wide format with intelligent column selection — prefers columns named "date", "variable", "value" over ambiguous alternatives
- **Categorical Data Detection**: Automatically detects categorical grouped data (e.g., Energy/Food × periods) and renders appropriate bar chart variants
- **Date range filtering**: X-axis supports date-based min/max filtering

### 2. Interactive Chart Editor
- **Konva.js Canvas**: All chart elements rendered as draggable objects
- **Configurable Canvas Size**: Width (800-2400) and height (400-1600) adjustable via Controls panel, default 1400×800
- **Zoomable Canvas**: Zoom in/out/fit buttons + mouse wheel zoom
- **Drag & Drop**: Move title, legend entries, annotations, data table anywhere on the canvas
- **Right-click Context Menu**: Change font size, color, family; rename legend labels; delete annotations; hide/delete data table
- **Chart Types**: Line, bar, area, stacked bar, stacked bar + line, mixed, and categorical grouped bar charts
- **Bar Stacking**: Grouped (side by side) or stacked rendering, controllable via Controls panel or AI
- **Bar Grouping**: By series (default) or by category for categorical data
- **Manual Controls**: Axis properties (labels, ranges, scales, line width, tick/label font sizes, Y-axis format), series colors/styles, gridlines, legend, data table
- **Resizable Panels**: VS Code-style draggable dividers between all sections (left sidebar, canvas, controls, summary) with minimum size constraints

### 3. Annotations
- **Horizontal Lines**: Dotted/dashed/solid reference lines at specific Y values (e.g., inflation target)
- **Vertical Lines**: Lines at specific dates (e.g., financial crisis, COVID)
- **Vertical Bands**: Shaded regions between date ranges (e.g., recession periods) with optional labels
- **Text Annotations**: Floating text labels anywhere on the chart
- **Full Label Customization**: All annotation types support editable label text, font size, and font color
- **Add/Delete**: Manual buttons (+ H-Line, + V-Line, + Text, + V-Band), ✕ delete per annotation, and "Delete All Annotations" button
- **AI-driven**: Create, customize, and remove annotations via natural language
- **Right-click Context Menu**: Right-click any annotation on the canvas for quick actions

### 4. AI Assistant (Claude Sonnet 4.5)
- **Advisory Mode**: For styling changes (colors, fonts, themes), AI suggests 2-3 professional options as clickable buttons instead of blindly applying. User picks the best option
- **Direct Actions**: Structural changes (delete, add, toggle, change chart type) apply immediately without suggestions
- **Natural Language Commands**: "Change to area chart", "Add % to y-axis", "Make it a stacked bar chart", "Group bars by category"
- **Data Q&A**: Ask questions about your data — trends, peaks, comparisons
- **Summary Updates**: "Append this information to the executive summary"
- **Custom Data Tables**: AI can create fully custom tables with arbitrary headers and rows
- **Display Transforms**: Non-destructive value transformations — "convert to millions", "show as percentage" — original data stays intact
- **Annotation Management**: Add, customize, and remove annotations by name
- **Floating Chat Window**: Bottom-right icon opens the AI chat with undo support
- **Per-chart Context**: Conversation resets when you create a new chart
- **Bedrock Status**: Green/red indicator in the header shows connection status

### 5. Y-Axis Formatting
- **Auto**: Smart formatting based on value range
- **Integer**: Whole numbers
- **Percent**: Values with % symbol
- **Decimal**: 1 or 2 decimal places
- Configurable via Controls Panel or AI assistant

### 6. Legend
- **Individually Draggable**: Each legend entry is a separate floating element
- **Right-click Rename**: Change legend label text via context menu
- **Per-Entry Font Controls**: Font size, color, and family editable per legend entry in Controls panel
- **Color Sync**: Changing series color automatically updates legend

### 7. Data Table
- **Transposed Layout**: Rows = data series, Columns = sampled dates
- **Custom Table Mode**: AI can create arbitrary tables with custom headers and rows
- **Drag-to-Resize**: Resize handles appear on hover — right edge, bottom edge, corner — all proportional scaling
- **Right-click Hide/Delete**: Right-click the data table for quick hide or delete options
- **Series-colored Text**: Row labels and values use the corresponding data series color
- **Computed Columns**: Vision analysis detects derived columns from reference images
- **Customizable**: Select columns, max date columns, font size, column width, row height
- **Legend-synced**: Row labels use legend entry names
- **Draggable**: Float the data table anywhere on the canvas

### 8. Executive Summary
- **Auto-generated**: Trend analysis, peaks/troughs, predictions, economist perspective
- **Resizable Panel**: Drag the divider to expand the summary section
- **Editable**: Full-height text area that fills the panel with vertical scrollbar
- **AI Append**: Ask the AI to add analysis to the summary
- **Powered by Bedrock**: Uses Claude Sonnet 4.5

### 9. Export
- **Python**: Standalone matplotlib script with embedded data, date-aware x-axis, area charts, annotations (zip with requirements.txt)
- **R**: Standalone ggplot2 script with embedded data (zip with install_packages.R)
- **PDF**: Chart image (300 DPI) with proper dates, area fills, horizontal lines, vertical bands, y-axis formatting + executive summary with FRBSF branding

### 10. Project Management
- **Save/Load**: Persist charts to SQLite, resume work across sessions
- **Dataset Reload**: Loading a saved project reloads the CSV data for rendering
- **Project List**: Sidebar with saved projects, click to load

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Konva.js, Zustand |
| Database | SQLite (via aiosqlite) |
| LLM | AWS Bedrock — Claude Sonnet 4.5 (cross-region) |
| Image Analysis | OpenCV + Bedrock Vision API |
| Data API | FRED API |
| PDF Export | ReportLab + matplotlib |
| Build Tool | Vite |

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access (Claude Sonnet 4.5 enabled, cross-region inference)
- FRED API key ([get one here](https://fred.stlouisfed.org/docs/api/api_key.html))

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/tjblavakumar/ER_CHAI.git
cd ER_CHAI
```

### 2. Install Python dependencies

```bash
pip install -e ".[dev]"
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Configure API keys

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
fred_api_key: "your-fred-api-key"
aws_region: "us-east-1"
aws_access_key_id: "ASIA..."
aws_secret_access_key: "your-secret-key"
aws_session_token: "your-session-token"  # required for SSO/STS credentials
bedrock_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
bedrock_vision_model_id: "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

Note: If using AWS SSO, session tokens expire periodically. Refresh with:
```bash
aws sso login
aws configure export-credentials --format env
```

## Running

### Quick Start (PowerShell)

```powershell
.\start-servers.ps1
```

Starts backend (port 8080) and frontend (port 5173). Open http://localhost:5173.

```powershell
.\stop-servers.ps1
```

### Manual Start

```bash
python -m uvicorn backend.main:app --reload --port 8080
cd frontend && npm run dev
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
ER_CHAI/
├── backend/
│   ├── api/                     # FastAPI routes, middleware, Bedrock status
│   ├── models/schemas.py        # Pydantic models (30+ classes)
│   ├── services/
│   │   ├── ai_assistant.py      # AI chat with advisory mode + direct actions
│   │   ├── config.py            # YAML config loader
│   │   ├── export_service.py    # Python/R/PDF export with date-aware rendering
│   │   ├── fred_client.py       # FRED API client with retry
│   │   ├── image_analyzer.py    # OpenCV + Vision (20-field comprehensive analysis)
│   │   ├── ingestion.py         # Data pipeline (URL, file, long-format pivot, categorical detection)
│   │   ├── project_store.py     # SQLite CRUD
│   │   └── summary_generator.py # Executive summary generation
│   └── main.py                  # FastAPI app with Bedrock health check
├── frontend/src/
│   ├── api/client.ts            # Axios API client (15+ endpoints)
│   ├── components/
│   │   ├── chart/               # 7 Konva.js chart element components
│   │   ├── AIChatWindow.tsx     # Floating AI chat with advisory mode, undo, suggestions
│   │   ├── CanvasEditor.tsx     # Zoomable canvas with configurable size
│   │   ├── ChartPreviewOverlay.tsx  # Chart style selection carousel
│   │   ├── ControlsPanel.tsx    # Full controls sidebar with all chart options
│   │   ├── ContextMenu.tsx      # Right-click menu with rename, delete, hide
│   │   ├── ExportToolbar.tsx    # Python/R/PDF download buttons
│   │   ├── ProjectList.tsx      # Save/load/delete with dataset reload
│   │   └── SummaryEditor.tsx    # Editable summary with AI generation
│   ├── store/appStore.ts        # Zustand state with undo history + preview overlay
│   ├── utils/
│   │   ├── chartVariants.ts     # Chart style variant generator for preview overlay
│   │   └── uuid.ts              # UUID generator
│   └── types/index.ts           # TypeScript interfaces
├── tests/                       # 255 tests (unit + property-based)
├── config.yaml.example
├── start-servers.ps1
└── stop-servers.ps1
```

## License

Internal use only.
