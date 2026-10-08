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

## Arranque con Docker

El único requisito es Docker Desktop. Desde la raíz del repositorio:

```powershell
.\scripts\iniciar.ps1                     # construye y levanta todo, y abre el navegador
.\scripts\generar-csv.ps1                 # crea CSV de prueba en .\salida
.\scripts\procesar-csv.ps1 .\salida       # carga una carpeta, uno o varios CSV
.\scripts\detener.ps1                     # apaga todo sin borrar los datos
```

| Contenedor | Contenido | Dirección |
| --- | --- | --- |
| `postgres` | PostgreSQL 16 con los datos en el volumen `utilityhub-datos-postgres` | `localhost:5432` |
| `esquema` | Aplica `backend\esquema.sql` en cada arranque y termina | |
| `api` | FastAPI servida con uvicorn | http://localhost:8000/docs |
| `web` | Build de producción del frontend servido con nginx | http://localhost:5173 |

Sin los scripts: `docker compose up -d --build` y `docker compose down`. Tras cambiar código, `iniciar.ps1` reconstruye las imágenes. Para empezar con la base vacía: `docker compose down -v`.

Los valores de desarrollo están como predeterminados en `docker-compose.yml` y se pueden cambiar con variables de entorno o un archivo `.env` en la raíz (no se versiona): `UTILITYHUB_DB_USUARIO`, `UTILITYHUB_DB_CLAVE`, `UTILITYHUB_DB_NOMBRE`, `UTILITYHUB_JWT_CLAVE_FIRMA` y los puertos `UTILITYHUB_PUERTO_DB`, `UTILITYHUB_PUERTO_API`, `UTILITYHUB_PUERTO_WEB`. Si Windows bloquea los scripts, ejecútalos con `powershell -ExecutionPolicy Bypass -File .\scripts\iniciar.ps1`.

### Cómo entran los CSV

Cada archivo trae las lecturas de una torre en un mes y se llama `lecturas_T<torre>_<AAAA-MM>.csv`. `procesar-csv.ps1` ejecuta `python -m procesamiento` dentro de la imagen de la API, que valida las filas, guarda la carga, sus lecturas y sus rechazos, y marca las anomalías; el resultado aparece en la página Cargas. De cada torre solo se admite el periodo más reciente o uno posterior, así que los archivos se cargan en orden. También se puede subir desde la página Cargas con el botón **Elegir archivo CSV**, que sigue el patrón de URL prefirmada de S3:

1. El navegador pide permiso con `POST /api/subidas`. La API revisa el nombre, la torre y el periodo, registra la subida como `pendiente` en la tabla `subida` y devuelve una URL firmada válida por 5 minutos.
2. El navegador envía el archivo con `PUT` a esa URL. El CSV no pasa a la base de datos: queda como objeto en el almacén.
3. La llegada del objeto dispara el procesamiento (`procesamiento/receptor_archivos.py`), que crea la carga y marca la subida como `procesada` o `fallida`. El navegador consulta `GET /api/subidas/{id}` hasta ver el resultado.

Mientras no hay AWS, la propia API hace de S3: guarda los objetos en la carpeta de `UTILITYHUB_ALMACEN_LOCAL_CARPETA` y los procesa en segundo plano, como haría la Lambda. Sin esa variable, la subida web responde 503 y el resto funciona igual.

El Detalle de carga muestra el CSV original línea por línea, con las filas rechazadas marcadas, y permite descargarlo. Lo pide con `GET /api/cargas/{id}/archivo`, que devuelve una URL firmada de lectura (el equivalente a una URL prefirmada `GET` de S3). Las firmas incluyen el método HTTP, así que una URL de subida no sirve para leer ni una de lectura para escribir. Las cargas procesadas con `procesar-csv.ps1` no tienen archivo en el almacén y muestran un aviso.

## Desarrollo sin Docker

Para editar código con recarga automática, Python 3.12 o superior y Node 20 o superior. Primero apaga los contenedores `api` y `web` para liberar los puertos y deja solo la base:

### 1. Base de datos

```powershell
docker compose up -d postgres esquema
docker compose stop api web
```

El esquema se puede volver a ejecutar sin errores. Siembra servicios, torres, apartamentos y el usuario `admin`.

### 2. Backend

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
$env:UTILITYHUB_ALMACEN_LOCAL_CARPETA = "..\almacen-local"
```

| Variable | Uso |
| --- | --- |
| `UTILITYHUB_DB_HOST`, `UTILITYHUB_DB_USUARIO`, `UTILITYHUB_DB_CLAVE`, `UTILITYHUB_DB_NOMBRE` | Conexión a PostgreSQL |
| `UTILITYHUB_DB_PUERTO` | Opcional, 5432 por defecto |
| `UTILITYHUB_JWT_CLAVE_FIRMA` | Firma de los tokens, mínimo 32 caracteres |
| `UTILITYHUB_CORS_ORIGENES` | Orígenes del frontend separados por coma |
| `UTILITYHUB_ALMACEN_LOCAL_CARPETA` | Opcional. Carpeta que simula el bucket de S3 para la subida web |

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

### 3. Frontend

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
