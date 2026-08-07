# Despliegue en Ubuntu

Esta copia usa el puerto interno `8001` para la API. No se debe abrir ese puerto en AWS: Nginx atiende HTTP/HTTPS para `pedidos.distribuidoratridente.cl`, entrega el frontend estático y reenvía `/api` a `127.0.0.1:8001`.

Las rutas de las plantillas asumen que el proyecto se instala en `/var/www/distribuidoratridente.cl`. Ajústalas si se usa otra ubicación.

## Configuración del servidor

1. Cree `/var/www/distribuidoratridente.cl/.env` desde `.env.example` y complete sus secretos.
2. Configure un `DATABASE_NAME` y `DATABASE_SCHEMA` exclusivos para Distribuidora Tridente.
3. Configure `CORS_ORIGINS=https://pedidos.distribuidoratridente.cl`.
4. Cree el entorno virtual dentro de `backend/.venv`, instale `backend/requirements.txt` y ejecute `alembic upgrade head` desde `backend`.
5. Ejecute `npm ci` y `npm run build` desde `frontend`.

## Servicios

1. Copie `distribuidoratridente-api.service.example` a `/etc/systemd/system/distribuidoratridente-api.service`.
2. Verifique que el usuario `www-data` pueda leer el proyecto, el entorno virtual y el archivo `.env`.
3. Ejecute `sudo systemctl daemon-reload` y `sudo systemctl enable --now distribuidoratridente-api`.
4. Copie `nginx-distribuidoratridente.cl.conf.example` a `/etc/nginx/sites-available/distribuidoratridente.cl` y cree su enlace en `sites-enabled`.
5. Valide Nginx con `sudo nginx -t`, recárguelo y emita el certificado HTTPS con Certbot.

El frontend compilado usa `/api` en producción. No defina `VITE_API_URL` para este despliegue salvo que se quiera enviar las peticiones a otra URL.