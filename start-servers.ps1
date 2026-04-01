# FRBSF Chart Builder — Start backend and frontend servers
# Run this from the project root: .\start-servers.ps1

Write-Host "Starting FRBSF Chart Builder..." -ForegroundColor Cyan

# Start backend (FastAPI on port 8080)
Write-Host "Starting backend on http://localhost:8080 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python -m uvicorn backend.main:app --reload --port 8080"

# Start frontend (Vite dev server on port 5173)
Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "Both servers started." -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8080" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open http://localhost:5173 in your browser." -ForegroundColor White
Write-Host "To stop both servers, run: .\stop-servers.ps1" -ForegroundColor Gray
