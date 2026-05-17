$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$backendPath = Join-Path $root "backend"
$frontendPath = Join-Path $root "frontend"

$pythonPath = Join-Path $backendPath "venv\Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    $pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"
}

if (-not (Test-Path $pythonPath)) {
    Write-Host "Python virtual environment was not found." -ForegroundColor Red
    Write-Host "Expected one of these paths:" -ForegroundColor Yellow
    Write-Host "$backendPath\venv\Scripts\python.exe"
    Write-Host "$backendPath\.venv\Scripts\python.exe"
    exit 1
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$backendPath'; & '$pythonPath' -m uvicorn app.app:app --reload --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$backendPath'; npx @modelcontextprotocol/inspector '$pythonPath' -m app.mcp.ticket_server"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location -LiteralPath '$frontendPath'; npm run dev "
)