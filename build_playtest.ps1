$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $projectRoot "EcoSim.spec"
$readmePath = Join-Path $projectRoot "packaging\README.txt"
$distributionPath = Join-Path $projectRoot "dist\EcoSim"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Project Python was not found at: $pythonPath"
}

if (-not (Test-Path -LiteralPath $specPath)) {
    throw "PyInstaller spec was not found at: $specPath"
}

if (-not (Test-Path -LiteralPath $readmePath)) {
    throw "Playtest README was not found at: $readmePath"
}

Push-Location $projectRoot
try {
    & $pythonPath -m PyInstaller --clean --noconfirm $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }

    Copy-Item `
        -LiteralPath $readmePath `
        -Destination (Join-Path $distributionPath "README.txt") `
        -Force
}
finally {
    Pop-Location
}

$archivePath = Join-Path `
    $projectRoot `
    "dist\EcoSim-playtest-a.1-windows-x64.zip"

Compress-Archive `
    -LiteralPath $distributionPath `
    -DestinationPath $archivePath `
    -Force

Write-Host "Playtest build created at: $distributionPath"
Write-Host "Playtest archive created at: $archivePath"