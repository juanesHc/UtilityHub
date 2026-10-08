param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Rutas
)

$RaizUtilityHub = Split-Path -Parent $PSScriptRoot

$archivos = foreach ($ruta in $Rutas) {
    $resuelta = Resolve-Path $ruta -ErrorAction SilentlyContinue
    if (-not $resuelta) {
        Write-Host "No existe: $ruta" -ForegroundColor Red
        continue
    }
    $elemento = Get-Item $resuelta
    if ($elemento.PSIsContainer) {
        Get-ChildItem -Path $elemento.FullName -Filter 'lecturas_*.csv' -File
    } else {
        $elemento
    }
}
$archivos = @($archivos | Sort-Object Name -Unique)
if ($archivos.Count -eq 0) {
    Write-Host 'No hay archivos que procesar. Los nombres deben seguir el formato lecturas_T<torre>_<AAAA-MM>.csv' -ForegroundColor Yellow
    exit 1
}

Push-Location $RaizUtilityHub
try {
    $serviciosActivos = @(docker compose ps --status running --services 2>$null)
    if ($serviciosActivos -notcontains 'postgres') {
        Write-Host 'La base de datos no está corriendo. Ejecuta primero .\scripts\iniciar.ps1' -ForegroundColor Red
        exit 1
    }

    $conError = 0
    foreach ($archivo in $archivos) {
        Write-Host ''
        Write-Host "==> $($archivo.Name)" -ForegroundColor Cyan
        docker compose run --rm --no-deps -v "$($archivo.DirectoryName):/entrada:ro" api python -m procesamiento "/entrada/$($archivo.Name)"
        if ($LASTEXITCODE -ne 0) {
            $conError += 1
        }
    }
} finally {
    Pop-Location
}

Write-Host ''
$color = if ($conError -eq 0) { 'Green' } else { 'Yellow' }
Write-Host "Procesados: $($archivos.Count) · con error: $conError" -ForegroundColor $color
