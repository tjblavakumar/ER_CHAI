# ER_CHAI Startup Script with Dependency Check
# Starts both backend and frontend servers

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   ER_CHAI Chart Builder - Startup Script  " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python dependencies are installed
Write-Host "[1/4] Checking Python dependencies..." -ForegroundColor Yellow
try {
    python -c "import fastapi, uvicorn, httpx" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Python dependencies missing" -ForegroundColor Red
        Write-Host "  Run: pip install -e .[dev]" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  ✗ Python dependencies missing" -ForegroundColor Red
    Write-Host "  Run: pip install -e .[dev]" -ForegroundColor Yellow
    exit 1
}

# Check if frontend dependencies are installed
Write-Host "[2/4] Checking frontend dependencies..." -ForegroundColor Yellow
if (Test-Path "frontend\node_modules") {
    Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
} else {
    Write-Host "  ✗ Frontend dependencies missing" -ForegroundColor Red
    Write-Host "  Installing frontend dependencies..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Failed to install frontend dependencies" -ForegroundColor Red
        Pop-Location
        exit 1
    }
    Pop-Location
    Write-Host "  ✓ Frontend dependencies installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/4] Starting Backend Server..." -ForegroundColor Yellow
Write-Host "  Backend: http://localhost:8080" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8080/docs" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python -m uvicorn backend.main:app --reload --port 8080"

# Wait a bit for backend to start
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "[4/4] Starting Frontend Server..." -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "   ✓ Both servers started successfully!    " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser to: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "To stop the servers, close the terminal windows or run:" -ForegroundColor Yellow
Write-Host "  .\stop-servers.ps1" -ForegroundColor Yellow
Write-Host ""
