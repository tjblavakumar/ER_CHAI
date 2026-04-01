# FRBSF Chart Builder

A local web application for creating, customizing, and exporting FRBSF-branded economic charts. Built with FastAPI (Python) backend and React + Konva.js frontend, powered by AWS Bedrock for AI-driven chart editing and executive summary generation.

## Features

### 1. Data Ingestion
- **FRED API**: Paste a FRED URL to automatically download economic data and generate a chart
- **File Upload**: Upload CSV or Excel files with optional reference chart image
- **Reference Image Analysis**: OpenCV + AWS Bedrock Vision extracts colors, chart type, annotations, formatting from reference images
- **Long-format detection**: Automatically pivots long-format data (date, key, value) to wide format

### 2. Interactive Chart Editor
- **Konva.js Canvas**: All chart elements rendered as draggable objects
- **Drag & Drop**: Move title, legend entries, annotations, data table anywhere on the canvas
- **Right-click Context Menu**: Change font size, color, family, and rename legend labels
- **Chart Types**: Line, bar, area, and mixed charts
- **Manual Controls**: Axis properties, series colors, gridlines, annotations, data table configuration

### 3. AI Assistant
- **Natural Language Commands**: "Change to area chart", "Add % to y-axis", "Create vertical band between 2020-01 and 2020-06"
- **Data Q&A**: Ask questions about your data — trends, peaks, comparisons
- **Floating Chat Window**: Bottom-right icon opens the AI chat with undo support
- **Per-chart Context**: Conversation resets when you create a new chart

### 4. Executive Summary
- **Auto-generated**: Trend analysis, peaks/troughs, predictions, economist perspective
- **Editable**: Modify the AI-generated summary as needed
- **Powered by Bedrock**: Uses Claude models for analysis

### 5. Export
- **Python**: Standalone matplotlib script with embedded data (zip with requirements.txt)
- **R**: Standalone ggplot2 script with embedded data (zip with install_packages.R)
- **PDF**: Chart image (300 DPI) + executive summary with FRBSF branding

### 6. Project Management
- **Save/Load**: Persist charts to SQLite, resume work across sessions
- **Project List**: Sidebar with saved projects, click to load

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI, uvicorn |
| Frontend | React, TypeScript, Konva.js, Zustand |
| Database | SQLite (via aiosqlite) |
| LLM | AWS Bedrock (Claude) |
| Image Analysis | OpenCV + Bedrock Vision API |
| Data API | FRED API |
| PDF Export | ReportLab + matplotlib |
| Build Tool | Vite |

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS account with Bedrock access (Claude models enabled)
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

Copy the example config and fill in your keys:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml`:

```yaml
fred_api_key: "your-fred-api-key"
aws_region: "us-east-1"
aws_access_key_id: "AKIA..."
aws_secret_access_key: "your-secret-key"
aws_session_token: "your-session-token"  # required for SSO/STS credentials
bedrock_model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
bedrock_vision_model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
```

## Running

### Quick Start (PowerShell)

```powershell
.\start-servers.ps1
```

This starts the backend on port 8080 and frontend on port 5173. Open http://localhost:5173 in your browser.

To stop:

```powershell
.\stop-servers.ps1
```

### Manual Start

Backend:

```bash
python -m uvicorn backend.main:app --reload --port 8080
```

Frontend:

```bash
cd frontend
npm run dev
```

## Running Tests

```bash
python -m pytest tests/ -v
```

211 unit tests covering all backend services.

## Project Structure

```
ER_CHAI/
├── backend/
│   ├── api/              # FastAPI routes and middleware
│   ├── models/           # Pydantic data models
│   ├── services/         # Business logic
│   │   ├── ai_assistant.py      # AI chat handler (Bedrock)
│   │   ├── config.py            # YAML config loader
│   │   ├── export_service.py    # Python/R/PDF export
│   │   ├── fred_client.py       # FRED API client
│   │   ├── image_analyzer.py    # OpenCV + Vision analysis
│   │   ├── ingestion.py         # Data ingestion pipeline
│   │   ├── project_store.py     # SQLite project persistence
│   │   └── summary_generator.py # Executive summary (Bedrock)
│   └── main.py           # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── api/           # Axios API client
│       ├── components/    # React components
│       │   ├── chart/     # Konva.js chart elements
│       │   ├── AIChatWindow.tsx
│       │   ├── CanvasEditor.tsx
│       │   ├── ControlsPanel.tsx
│       │   ├── ContextMenu.tsx
│       │   ├── ExportToolbar.tsx
│       │   ├── ProjectList.tsx
│       │   └── SummaryEditor.tsx
│       ├── store/         # Zustand state management
│       └── types/         # TypeScript interfaces
├── tests/                 # pytest test suite
├── config.yaml.example    # Config template
├── start-servers.ps1      # Start both servers
└── stop-servers.ps1       # Stop both servers
```

## License

Internal use only.
