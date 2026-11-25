# Guía de Configuración de Variables y Secretos por Ambiente en GitHub

Esta guía detalla paso a paso cómo configurar los entornos **`production`** y **`qa`** en GitHub Actions para el repositorio `pedidos.distribuidoratridente.cl`, garantizando la segregación de credenciales entre ramas y entornos de ejecución.

---

## 1. Funcionamiento del Pipeline Multientorno

El workflow `.github/workflows/deploy.yml` evalúa dinámicamente el entorno de GitHub según la rama que detona el despliegue:

- **Rama `main`** $\longrightarrow$ Activa el environment **`production`**.
- **Rama `qa`** (o `develop`) $\longrightarrow$ Activa el environment **`qa`**.
- **Despliegue Manual (`workflow_dispatch`)** $\longrightarrow$ Permite seleccionar explícitamente `production` o `qa` desde la interfaz de GitHub Actions.

Al declarar `environment: <nombre>` en el job de despliegue, GitHub Actions inyecta automáticamente los secretos y variables específicos de ese entorno en los contextos `${{ secrets.* }}` y `${{ vars.* }}`.

---

## 2. Creación de los Entornos en GitHub

1. Ingresa a tu repositorio en GitHub: `https://github.com/respinozav/pedidos.distribuidoratridente.cl`
2. Ve a la pestaña **Settings** (Configuración del repositorio).
3. En el menú lateral izquierdo, haz clic en **Environments** (dentro de la sección *Code and automation*).
4. Haz clic en **New environment**:
   - Crea el entorno llamado exactamente: `production`
   - Vuelve a hacer clic en **New environment** y crea: `qa`

### Reglas de Despliegue Recomendadas (Deployment branches):
- Para **`production`**: En *Deployment branches*, selecciona *Selected branches* y añade la regla `main`.
- Para **`qa`**: En *Deployment branches*, selecciona *Selected branches* y añade la regla `qa`.

---

## 3. Matriz de Variables y Secretos Requeridos

Dentro de cada entorno creado (**Settings -> Environments -> [production | qa]**), encontrarás dos secciones:
1. **Environment variables** (para datos públicos o de configuración).
2. **Environment secrets** (para contraseñas, llaves SSH y tokens cifrados).

### A. Environment Variables (`vars`)

| Variable | Tipo | Descripción | Ejemplo Producción (`main`) | Ejemplo QA (`qa`) |
| :--- | :---: | :--- | :--- | :--- |
| `AWS_HOST` | `var` | IP pública o DNS del servidor AWS | `pedidos.distribuidoratridente.cl` | `pedidos-qa.distribuidoratridente.cl` |
| `AWS_USERNAME` | `var` | Usuario SSH para la conexión | `ubuntu` | `ubuntu` |
| `AWS_HOST_BD` | `var` | Host de conexión PostgreSQL | `localhost` (o DNS RDS Prod) | `pedidos-qa.distribuidoratridente.cl` |
| `AWS_SCHEME_BD` | `var` | Esquema de base de datos PostgreSQL | `bdtridente` | `bdtridente-qa` |
| `AWS_USER_BD` | `var` | Usuario de base de datos PostgreSQL | `postgres` | `tridente_qa` |
| `DEFONTANA_API_BASE_URL` | `var` | URL base del API de Defontana | `https://replapi.defontana.com` | `https://replapi.defontana.com` |
| `DEFONTANA_CLIENT_ID` | `var` | Client ID de integración Defontana | `20250217200717633001` | `20250217200717633001` |
| `DEFONTANA_COMPANY_ID` | `var` | Company ID de integración Defontana | `20250217200717633001` | `20250217200717633001` |
| `DEFONTANA_API_USER` | `var` | Usuario de API Defontana | `INTEGRACION` | `INTEGRACION` |
| `GEMINI_MODEL` | `var` | Modelo de IA de Google Gemini | `gemini-3.5-flash-lite` | `gemini-3.5-flash-lite` |
| `CORS_ORIGINS` | `var` | Orígenes web autorizados para API | `https://pedidos.distribuidoratridente.cl` | `https://pedidos-qa.distribuidoratridente.cl,http://localhost:5173` |

---

### B. Environment Secrets (`secrets`)

| Secreto | Tipo | Descripción | Configuración en Producción | Configuración en QA |
| :--- | :---: | :--- | :--- | :--- |
| `AWS_PRIVATE_KEY` | `secret` | Llave privada SSH (contenido del archivo `.pem`) | Llave privada AWS Prod | Llave privada AWS QA |
| `AWS_PASSWORD_BD` | `secret` | Contraseña del usuario PostgreSQL | Contraseña BD Prod | Contraseña BD QA |
| `DEFONTANA_API_PASSWORD` | `secret` | Contraseña o token del API Defontana | Password API Defontana Prod | Password API Defontana QA |
| `GEMINI_API_KEY` | `secret` | API Key de Google AI Studio | Clave Gemini Prod | Clave Gemini QA |
| `JWT_SECRET_KEY` | `secret` | Clave secreta para firmar tokens JWT | Secreto aleatorio robusto Prod | Secreto aleatorio robusto QA |

> [!IMPORTANT]
> **Generación de JWT_SECRET_KEY:**
> Puedes generar una clave aleatoria segura ejecutando en la terminal:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```
> Asegúrate de colocar un valor diferente en `production` y en `qa`.

---

## 4. Flujo de Sincronización en el Servidor

Durante la ejecución del workflow de GitHub Actions:

1. **SSH Connection:** GitHub Actions se conecta al servidor especificado en `AWS_HOST` usando `AWS_USERNAME` y `AWS_PRIVATE_KEY`.
2. **Systemd Environment:** Las variables globales de entorno del sistema operativo (`GEMINI_API_KEY`, `GEMINI_MODEL`, `JWT_SECRET_KEY`, `DATABASE_*`, `DEFONTANA_*`) son inyectadas en systemd mediante `systemctl set-environment`.
3. **Sincronización en Archivos `.env`:** El script `backend/scripts/sync_env.py` actualiza atómicamente todos los archivos `.env` del proyecto con los valores exactos del ambiente.
4. **Reinicio de Servicios:** Se recarga `systemd`, se reinician los servicios de backend correspondientes (`pedidos-tridente` en producción o `pedidos-tridente-qa` en QA) y se recarga `nginx`.
5. **Diagnóstico y Reporte:** Se ejecuta una prueba de salud (`/api/health`), test de conexión a Gemini y se genera el archivo de diagnóstico `/status_diag.txt`.
