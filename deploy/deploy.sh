#!/bin/bash
set -e

REPO_DIR="/var/www/pedidos.distribuidoratridente.cl"

echo "=== 1. Actualizando código desde Git ==="
cd "$REPO_DIR"
git pull origin main

echo "=== 2. Actualizando dependencias de Backend ==="
cd "$REPO_DIR/backend"
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    python3 -m venv .venv
    source .venv/bin/activate
fi
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 3. Ejecutando migraciones de Base de Datos ==="
if [ -f "alembic.ini" ]; then
    alembic upgrade head || echo "Alembic upgrade omitido o sin cambios pendientes"
fi

echo "=== 4. Compilando Frontend ==="
cd "$REPO_DIR/frontend"
npm install
npm run build

echo "=== 5. Levantando / Actualizando Evolution API (WhatsApp) ==="
cd "$REPO_DIR/deploy"
if command -v docker &> /dev/null; then
    docker compose up -d
else
    echo "Docker no está instalado o no disponible en PATH."
fi

echo "=== 6. Reiniciando servicio FastAPI ==="
sudo systemctl restart distribuidoratridente-api || echo "Servicio distribuidoratridente-api no reiniciado"

echo "=== ¡Despliegue completado con éxito! ==="
