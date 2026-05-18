param(
    [int]$backendPort = 8000,
    [int]$frontendPort = 3000
)

function Test-Port {
    param([int]$port)
    $tcpClient = New-Object System.Net.Sockets.TCPClient
    try {
        $tcpClient.Connect("localhost", $port)
        return $true
    } catch {
        return $false
    } finally {
        $tcpClient.Close()
    }
}

function Stop-ProcessOnPort {
    param([int]$port)
    $processIdList = (Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue).OwningProcess | Select-Object -Unique
    if ($processIdList) {
        foreach ($procId in $processIdList) {
            try {
                $process = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "Port $port is occupied by process $($process.Name) (PID: $procId), stopping..." -ForegroundColor Yellow
                    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
                    Write-Host "Process $($process.Name) (PID: $procId) stopped" -ForegroundColor Green
                }
            } catch {
                Write-Host ("Error stopping process " + $procId + ": " + $_) -ForegroundColor Red
            }
        }
        Start-Sleep -Seconds 1
    }
}

function Wait-ForPort {
    param([int]$port, [int]$timeout = 30)
    $count = 0
    while (-not (Test-Port -port $port)) {
        Start-Sleep -Seconds 1
        $count++
        if ($count -ge $timeout) {
            Write-Host "Timeout waiting for port $port to start" -ForegroundColor Red
            return $false
        }
    }
    return $true
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Start Backend and Frontend Services" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking port $backendPort (Backend)..." -ForegroundColor White
if (Test-Port -port $backendPort) {
    Stop-ProcessOnPort -port $backendPort
}

Write-Host "Checking port $frontendPort (Frontend)..." -ForegroundColor White
if (Test-Port -port $frontendPort) {
    Stop-ProcessOnPort -port $frontendPort
}

Write-Host ""
Write-Host "Starting Backend Service (Port $backendPort)..." -ForegroundColor Green
$env:PYTHONPATH = $env:PYTHONPATH + ";."
$backendProcess = Start-Process -FilePath "python" -ArgumentList "-m", "backend.app.run" -WorkingDirectory "." -PassThru -NoNewWindow

Write-Host "Waiting for Backend Service to start..." -ForegroundColor White
if (Wait-ForPort -port $backendPort) {
    Write-Host "Backend Service started, listening on port $backendPort" -ForegroundColor Green
} else {
    Write-Host "Failed to start Backend Service" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting Frontend Service (Port $frontendPort)..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm", "run", "dev" -WorkingDirectory "frontend" -PassThru -NoNewWindow

Write-Host "Waiting for Frontend Service to start..." -ForegroundColor White
if (Wait-ForPort -port $frontendPort) {
    Write-Host "Frontend Service started, listening on port $frontendPort" -ForegroundColor Green
} else {
    Write-Host "Failed to start Frontend Service" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    Services Started Successfully" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Backend Service: http://localhost:$backendPort" -ForegroundColor White
Write-Host "Frontend Service: http://localhost:$frontendPort" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop services" -ForegroundColor Yellow

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    if ($backendProcess -and !$backendProcess.HasExited) {
        $backendProcess.Kill()
        Write-Host "Backend Service stopped" -ForegroundColor Green
    }
    if ($frontendProcess -and !$frontendProcess.HasExited) {
        $frontendProcess.Kill()
        Write-Host "Frontend Service stopped" -ForegroundColor Green
    }
    Write-Host "All services stopped" -ForegroundColor Cyan
}