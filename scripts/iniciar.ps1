$RaizUtilityHub = Split-Path -Parent $PSScriptRoot
$PuertoApi = if ($env:UTILITYHUB_PUERTO_API) { $env:UTILITYHUB_PUERTO_API } else { '8000' }
$PuertoWeb = if ($env:UTILITYHUB_PUERTO_WEB) { $env:UTILITYHUB_PUERTO_WEB } else { '5173' }

function Escribir-Paso([string]$texto) {
    Write-Host ''
    Write-Host "==> $texto" -ForegroundColor Cyan
}

function Esperar-Hasta([scriptblock]$condicion, [int]$segundosMaximos, [string]$descripcion) {
    $limite = (Get-Date).AddSeconds($segundosMaximos)
    while ((Get-Date) -lt $limite) {
        if (& $condicion) {
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "Se agotó la espera: $descripcion"
}

function Docker-Responde {
    docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Url-Responde([string]$url) {
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

Escribir-Paso 'Docker'
if (-not (Docker-Responde)) {
    $dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path $dockerDesktop)) {
        throw 'Docker no responde y no se encontró Docker Desktop. Instálalo o ábrelo y vuelve a ejecutar este script.'
    }
    Write-Host 'Abriendo Docker Desktop...'
    Start-Process $dockerDesktop
    Esperar-Hasta { Docker-Responde } 180 'Docker Desktop no terminó de arrancar'
}
Write-Host 'Docker listo.'

Escribir-Paso 'Contenedores (la primera vez tarda unos minutos)'
Push-Location $RaizUtilityHub
try {
    cmd /c "docker compose up -d --build 2>&1"
    if ($LASTEXITCODE -ne 0) {
        throw 'docker compose up falló. Revisa el mensaje de arriba o ejecuta: docker compose logs'
    }
} finally {
    Pop-Location
}

Escribir-Paso 'Esperando a la API y al frontend'
Esperar-Hasta { Url-Responde "http://localhost:$PuertoApi/docs" } 90 'la API no respondió; revisa: docker compose logs api'
Esperar-Hasta { Url-Responde "http://localhost:$PuertoWeb" } 30 'el frontend no respondió; revisa: docker compose logs web'

Start-Process "http://localhost:$PuertoWeb"
Write-Host ''
Write-Host 'UtilityHub está arriba:' -ForegroundColor Green
Write-Host "  Panel web  http://localhost:$PuertoWeb"
Write-Host "  API        http://localhost:$PuertoApi/docs"
Write-Host 'Para procesar CSV: .\scripts\procesar-csv.ps1 <archivo o carpeta>'
Write-Host 'Para apagarlo:     .\scripts\detener.ps1'
