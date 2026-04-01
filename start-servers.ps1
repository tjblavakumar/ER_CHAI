# FRBSF Chart Builder - Start backend and frontend servers
# Run this from the project root: .\start-servers.ps1

Write-Host "Starting FRBSF Chart Builder..." -ForegroundColor Cyan

# Start backend (FastAPI on port 8080)
Write-Host "Starting backend on http://localhost:8080 ..." -ForegroundColor Green
$backendCmd = "cd '" + $PSScriptRoot + "'; python -m uvicorn backend.main:app --reload --port 8080"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend to be ready before starting frontend
Write-Host "Waiting for backend to be ready..." -ForegroundColor Yellow
$maxAttempts = 15
$attempt = 0
$backendReady = $false

while ($attempt -lt $maxAttempts -and -not $backendReady) {
    Start-Sleep -Seconds 2
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/api/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            $elapsed = $attempt * 2
            Write-Host "Backend is ready. (took ~${elapsed}s)" -ForegroundColor Green
        }
    } catch {
        Write-Host "  Attempt ${attempt}/${maxAttempts} - backend not ready yet..." -ForegroundColor Gray
    }
}

if (-not $backendReady) {
    Write-Host "Warning: Backend may not be fully started. Starting frontend anyway..." -ForegroundColor Yellow
}

# Start frontend (Vite dev server on port 5173)
Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
$frontendCmd = "cd '" + $PSScriptRoot + "\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "Both servers started." -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8080" -ForegroundColor Yellow
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open http://localhost:5173 in your browser." -ForegroundColor White
Write-Host "To stop both servers, run stop-servers.ps1" -ForegroundColor Gray
