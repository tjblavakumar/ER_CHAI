# FRBSF Chart Builder - Start backend and frontend servers
# Run this from the project root: .\start-servers.ps1

Write-Host "Starting FRBSF Chart Builder..." -ForegroundColor Cyan

# Start backend (FastAPI on port 8080)
Write-Host "Starting backend on http://localhost:8080 ..." -ForegroundColor Green
$backendCmd = "cd '" + $PSScriptRoot + "'; python -m uvicorn backend.main:app --reload --port 8080"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend health endpoint
Write-Host "Waiting for backend..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 10; $i++) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8080/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) {
            $ready = $true
            Write-Host "Backend ready." -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  Waiting... ($i)" -ForegroundColor Gray
    }
}
if (-not $ready) {
    Write-Host "Backend may still be starting. Proceeding..." -ForegroundColor Yellow
}

# Start frontend (Vite dev server on port 5173)
Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
$frontendCmd = "cd '" + $PSScriptRoot + "\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Both servers started." -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8080" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open http://localhost:5173 in your browser." -ForegroundColor White
Write-Host "To stop both servers, run stop-servers.ps1" -ForegroundColor Gray
