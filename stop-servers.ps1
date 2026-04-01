# FRBSF Chart Builder - Stop backend and frontend servers and close their terminals
# Run this from the project root: .\stop-servers.ps1

Write-Host "Stopping FRBSF Chart Builder servers..." -ForegroundColor Cyan

# Kill anything on port 8080 (backend)
$backendPids = netstat -ano 2>$null | Select-String ":8080\s.*LISTENING" | ForEach-Object {
    ($_ -split '\s+')[-1]
} | Sort-Object -Unique
foreach ($procId in $backendPids) {
    if ($procId -and $procId -ne "0") {
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            try {
                $parentId = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue).ParentProcessId
                if ($parentId) {
                    $parentProc = Get-Process -Id $parentId -ErrorAction SilentlyContinue
                    if ($parentProc -and $parentProc.ProcessName -eq "powershell") {
                        Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
                    }
                }
            } catch {}
            Write-Host "Backend process (PID $procId) on port 8080 stopped." -ForegroundColor Green
        } catch {
            Write-Host "Could not stop PID $procId" -ForegroundColor Yellow
        }
    }
}
if (-not $backendPids) {
    Write-Host "No backend process found on port 8080." -ForegroundColor Yellow
}

# Kill anything on port 5173 (frontend)
$frontendPids = netstat -ano 2>$null | Select-String ":5173\s.*LISTENING" | ForEach-Object {
    ($_ -split '\s+')[-1]
} | Sort-Object -Unique
foreach ($procId in $frontendPids) {
    if ($procId -and $procId -ne "0") {
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            try {
                $parentId = (Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction SilentlyContinue).ParentProcessId
                if ($parentId) {
                    $parentProc = Get-Process -Id $parentId -ErrorAction SilentlyContinue
                    if ($parentProc -and $parentProc.ProcessName -eq "powershell") {
                        Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
                    }
                }
            } catch {}
            Write-Host "Frontend process (PID $procId) on port 5173 stopped." -ForegroundColor Green
        } catch {
            Write-Host "Could not stop PID $procId" -ForegroundColor Yellow
        }
    }
}
if (-not $frontendPids) {
    Write-Host "No frontend process found on port 5173." -ForegroundColor Yellow
}

Write-Host "Done." -ForegroundColor Cyan
