param()

$backendDir = Join-Path $PSScriptRoot "backend"
$venvPython = Join-Path $backendDir "venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "venv not found. Run setup first:" -ForegroundColor Red
    Write-Host "  cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  SenseLense -- Starting Backend" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  http://localhost:5050" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

Set-Location $backendDir
& $venvPython -m flask run --port 5050
