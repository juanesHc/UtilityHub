$RaizUtilityHub = Split-Path -Parent $PSScriptRoot

Push-Location $RaizUtilityHub
try {
    cmd /c "docker compose down 2>&1"
} finally {
    Pop-Location
}
Write-Host ''
Write-Host 'UtilityHub apagado. Los datos siguen en el volumen de Docker.' -ForegroundColor Green
