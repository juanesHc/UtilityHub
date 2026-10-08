param(
    [string]$Salida = 'salida',
    [int]$Semilla = 42
)

$RaizUtilityHub = Split-Path -Parent $PSScriptRoot
$CarpetaGenerador = Join-Path $RaizUtilityHub 'tools\generador-datos'
$CarpetaSalida = if ([System.IO.Path]::IsPathRooted($Salida)) { $Salida } else { Join-Path $RaizUtilityHub $Salida }
New-Item -ItemType Directory -Force $CarpetaSalida | Out-Null

Push-Location $RaizUtilityHub
try {
    docker compose run --rm --no-deps -v "${CarpetaGenerador}:/herramientas:ro" -v "${CarpetaSalida}:/salida" --user root api python /herramientas/generateTestCsv.py --salida /salida --semilla $Semilla
    if ($LASTEXITCODE -ne 0) {
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host ''
Write-Host "CSV generados en $CarpetaSalida" -ForegroundColor Green
Write-Host "Para cargarlos: .\scripts\procesar-csv.ps1 $Salida"
