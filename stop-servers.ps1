# FRBSF Chart Builder — Stop backend and frontend servers
# Run this from the project root: .\stop-servers.ps1

Write-Host "Stopping FRBSF Chart Builder servers..." -ForegroundColor Cyan

# Stop uvicorn (backend)
$uvicornProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    try { $_.CommandLine -match "uvicorn" } catch { $false }
}
if ($uvicornProcs) {
    $uvicornProcs | Stop-Process -Force
    Write-Host "Backend (uvicorn) stopped." -ForegroundColor Green
} else {
    # Fallback: kill anything on port 8080
    $portPid = (netstat -ano | Select-String ":8080\s.*LISTENING" | ForEach-Object {
        ($_ -split '\s+')[-1]
    } | Select-Object -First 1)
    if ($portPid) {
        Stop-Process -Id $portPid -Force -ErrorAction SilentlyContinue
        Write-Host "Backend process (PID $portPid) on port 8080 stopped." -ForegroundColor Green
    } else {
        Write-Host "No backend process found on port 8080." -ForegroundColor Yellow
    }
}

# Stop Vite dev server (frontend) — node process on port 5173
$frontendPid = (netstat -ano | Select-String ":5173\s.*LISTENING" | ForEach-Object {
    ($_ -split '\s+')[-1]
} | Select-Object -First 1)
if ($frontendPid) {
    Stop-Process -Id $frontendPid -Force -ErrorAction SilentlyContinue
    Write-Host "Frontend (Vite) process (PID $frontendPid) on port 5173 stopped." -ForegroundColor Green
} else {
    Write-Host "No frontend process found on port 5173." -ForegroundColor Yellow
}

Write-Host "Done." -ForegroundColor Cyan
