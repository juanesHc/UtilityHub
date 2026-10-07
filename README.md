# UtilityHub

Plataforma que recibe archivos CSV con lecturas de medidores de agua y energía de un conjunto residencial, los valida, los consolida en PostgreSQL y marca los consumos anómalos. Proyecto académico de AWS Cloud Foundations.

| Carpeta | Contenido |
| --- | --- |
| `backend/comun` | Modelos, excepciones, configuración y acceso a datos compartidos |
| `backend/procesamiento` | Normalización, validación, cálculo de consumo y detección de anomalías |
| `backend/api` | API FastAPI de consulta, autenticación y administradores |
| `backend/pruebas` | Pruebas automáticas (unitarias y contra PostgreSQL) |
| `frontend` | Panel web en React + Vite |
| `tools/generador-datos` | Generador de CSV de prueba con casos esperados |

Requisitos: Docker, Python 3.12 o superior y Node 20 o superior. Los comandos están en PowerShell.

## 1. Base de datos

```powershell
docker compose up -d
Get-Content backend\esquema.sql | docker exec -i utilityhub-postgres psql -U utilityhub -d utilityhub
```

El esquema se puede volver a ejecutar sin errores. Siembra servicios, torres, apartamentos y el usuario `admin`.

## 2. Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\python -m pip install -r requirements-dev.txt

$env:UTILITYHUB_DB_HOST = "localhost"
$env:UTILITYHUB_DB_USUARIO = "utilityhub"
$env:UTILITYHUB_DB_CLAVE = "localdev"
$env:UTILITYHUB_DB_NOMBRE = "utilityhub"
$env:UTILITYHUB_JWT_CLAVE_FIRMA = "una-clave-de-desarrollo-de-al-menos-32-caracteres"
$env:UTILITYHUB_CORS_ORIGENES = "http://localhost:5173,http://127.0.0.1:5173"
```

| Variable | Uso |
| --- | --- |
| `UTILITYHUB_DB_HOST`, `UTILITYHUB_DB_USUARIO`, `UTILITYHUB_DB_CLAVE`, `UTILITYHUB_DB_NOMBRE` | Conexión a PostgreSQL |
| `UTILITYHUB_DB_PUERTO` | Opcional, 5432 por defecto |
| `UTILITYHUB_JWT_CLAVE_FIRMA` | Firma de los tokens, mínimo 32 caracteres |
| `UTILITYHUB_CORS_ORIGENES` | Orígenes del frontend separados por coma |

Generar y procesar datos de prueba (cada torre en orden de periodo):

```powershell
venv\Scripts\python ..\tools\generador-datos\generateTestCsv.py --salida ..\salida
Get-ChildItem ..\salida\lecturas_*.csv | Sort-Object Name | ForEach-Object { venv\Scripts\python -m procesamiento $_.FullName }
```

API y documentación interactiva en http://localhost:8000/docs:

```powershell
venv\Scripts\python -m uvicorn api.main:aplicacion --reload
```

Pruebas (crean y borran su propia base `utilityhub_pruebas`; sin PostgreSQL solo corren las unitarias):

```powershell
venv\Scripts\python -m pytest
```

Administradores desde el servidor:

```powershell
venv\Scripts\python -m api.administrar_usuarios crear <usuario>
venv\Scripts\python -m api.administrar_usuarios cambiar-clave admin
```

La clave sembrada del usuario `admin` es solo para desarrollo: cámbiala antes de cualquier despliegue.

## 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173 con la API corriendo (sección 2) y entra con un administrador de la base. El frontend toma la dirección de la API de `VITE_API_URL`, que para desarrollo ya está en `frontend\.env.development` (`http://127.0.0.1:8000`). Para apuntar a otra API sin tocar ese archivo, crea `frontend\.env.development.local` con tu propio `VITE_API_URL`; ese archivo no se versiona. Si la variable falta, la aplicación muestra un aviso en lugar de arrancar.

Comprobaciones y build para S3:

```powershell
npx tsc -b
npx oxlint
npm run build
```

El build queda en `frontend\dist`. En producción, la URL de la API va en `frontend\.env.production` y el origen del sitio debe estar en `UTILITYHUB_CORS_ORIGENES`.
