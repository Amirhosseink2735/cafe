$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "Building CafeManagement with PyInstaller..."
& $Python -m PyInstaller --noconfirm --clean cafe.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

New-Item -ItemType Directory -Force -Path (Join-Path $Root "dist\installer") | Out-Null

$Iscc = @(
    "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    Write-Warning "Inno Setup compiler (ISCC.exe) was not found. Installer was not built."
    Write-Host "PyInstaller output: dist\CafeManagement\CafeManagement.exe"
    exit 0
}

Write-Host "Compiling Inno Setup installer..."
& $Iscc (Join-Path $Root "installer\installer_script.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Write-Host "Installer: dist\installer\CafeManagement_Setup.exe"
