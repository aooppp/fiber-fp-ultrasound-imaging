$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath ".\main.py")) {
    throw "main.py was not found. Please run this script from the ultrasound_imaging project folder."
}

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
python -m pip install -r requirements.txt

Write-Host "Building Windows application with PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name "FiberFP_Ultrasound_Imaging" `
    --hidden-import "PyQt5.sip" `
    --hidden-import "matplotlib.backends.backend_qt5agg" `
    --hidden-import "mc600_controller" `
    --hidden-import "art_scope_daq" `
    main.py

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host "Executable folder: $ProjectRoot\dist\FiberFP_Ultrasound_Imaging" -ForegroundColor Green
Write-Host "Run: $ProjectRoot\dist\FiberFP_Ultrasound_Imaging\FiberFP_Ultrasound_Imaging.exe" -ForegroundColor Green
