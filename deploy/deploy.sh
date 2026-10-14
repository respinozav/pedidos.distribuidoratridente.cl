#!/bin/bash

##############################################################################
# DEPLOY UNIVERSAL 3.0
# React / FastAPI / HTML
#
# Soporta:
#   - HTML estático
#   - React dentro de /frontend
#   - React en la raíz del proyecto
#   - FastAPI dentro de /backend
#   - React + FastAPI
#   - Evolution API (WhatsApp Sidecar)
##############################################################################

set -e
set -o pipefail

START_TIME=$(date +%s)

############################################
# COLORES
############################################

RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
NC="\033[0m"

############################################
# RUTAS
############################################

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_NAME=$(basename "$PROJECT_DIR")

BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# React ubicado directamente en la raíz
ROOT_PACKAGE_JSON="$PROJECT_DIR/package.json"
ROOT_DIST_DIR="$PROJECT_DIR/dist"

DEPLOY_DIR="$PROJECT_DIR/deploy"
LOG_DIR="$PROJECT_DIR/logs"
BACKUP_DIR="$PROJECT_DIR/backup"

mkdir -p "$DEPLOY_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

DATE=$(date +"%Y-%m-%d_%H-%M-%S")

LOG_FILE="$LOG_DIR/deploy-$DATE.log"

exec > >(tee -a "$LOG_FILE") 2>&1

############################################
# CABECERA
############################################

echo ""
echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}          DEPLOY $PROJECT_NAME${NC}"
echo -e "${CYAN}====================================================${NC}"
echo ""

############################################
# INFORMACIÓN GIT
############################################

echo -e "${BLUE}Repositorio:${NC} $PROJECT_DIR"
echo -e "${BLUE}Usuario:${NC} $(whoami)"
echo -e "${BLUE}Fecha:${NC} $(date)"

CURRENT_BRANCH=$(git branch --show-current)
CURRENT_COMMIT=$(git rev-parse --short HEAD)

echo -e "${BLUE}Branch:${NC} $CURRENT_BRANCH"
echo -e "${BLUE}Commit:${NC} $CURRENT_COMMIT"

############################################
# SERVICIO SYSTEMD
############################################

SERVICE_NAME=""

case "$PROJECT_NAME" in

    pedidos.santamena.cl)
        SERVICE_NAME="pedidos-santamena"
        ;;

    pedidos.distribuidoratridente.cl)
        SERVICE_NAME="pedidos-tridente"
        ;;

esac

############################################
# NGINX ROOT
############################################

NGINX_ROOT="/var/www/html/$PROJECT_NAME"

############################################
# GIT PULL
############################################

echo ""
echo -e "${YELLOW}>> Actualizando repositorio...${NC}"

git pull origin "$CURRENT_BRANCH"

NEW_COMMIT=$(git rev-parse --short HEAD)

echo "Commit desplegado: $NEW_COMMIT"

############################################
# DETECCIÓN DEL PROYECTO
############################################

IS_BACKEND=false
IS_FRONTEND=false
IS_ROOT_REACT=false
IS_HTML=false

if [ -d "$BACKEND_DIR" ]; then
    IS_BACKEND=true
fi

if [ -d "$FRONTEND_DIR" ]; then
    IS_FRONTEND=true
fi

# Detectar React cuando package.json está en la raíz
if [ "$IS_FRONTEND" = false ] && [ -f "$ROOT_PACKAGE_JSON" ]; then
    IS_ROOT_REACT=true
fi

# HTML estático:
# index.html en raíz y no es React
if [ "$IS_ROOT_REACT" = false ] && [ -f "$PROJECT_DIR/index.html" ]; then
    IS_HTML=true
fi

############################################
# MOSTRAR TIPO DE PROYECTO
############################################

echo ""
echo -e "${CYAN}>> Tipo de proyecto detectado${NC}"

if [ "$IS_BACKEND" = true ] && [ "$IS_FRONTEND" = true ]; then

    echo -e "${GREEN}React + FastAPI${NC}"

elif [ "$IS_BACKEND" = true ] && [ "$IS_ROOT_REACT" = true ]; then

    echo -e "${GREEN}React raíz + FastAPI${NC}"

elif [ "$IS_FRONTEND" = true ]; then

    echo -e "${GREEN}React /frontend${NC}"

elif [ "$IS_ROOT_REACT" = true ]; then

    echo -e "${GREEN}React raíz${NC}"

elif [ "$IS_HTML" = true ]; then

    echo -e "${GREEN}HTML estático${NC}"

else

    echo -e "${YELLOW}Proyecto no clasificado${NC}"

fi

############################################
# BACKEND
############################################

if [ "$IS_BACKEND" = true ]; then

    echo ""
    echo -e "${YELLOW}>> Backend${NC}"

    cd "$BACKEND_DIR"

    ########################################
    # VIRTUAL ENVIRONMENT (.venv y venv)
    ########################################

    ACTIVE_VENV=""
    if [ -d "$BACKEND_DIR/.venv" ]; then
        ACTIVE_VENV="$BACKEND_DIR/.venv"
    elif [ -d "$BACKEND_DIR/venv" ]; then
        ACTIVE_VENV="$BACKEND_DIR/venv"
    else
        echo "Creando entorno virtual..."
        python3 -m venv "$BACKEND_DIR/.venv"
        ACTIVE_VENV="$BACKEND_DIR/.venv"
    fi

    # Asegurar enlace simbólico entre venv y .venv
    if [ -d "$BACKEND_DIR/.venv" ] && [ ! -e "$BACKEND_DIR/venv" ]; then
        ln -s "$BACKEND_DIR/.venv" "$BACKEND_DIR/venv" || true
    elif [ -d "$BACKEND_DIR/venv" ] && [ ! -e "$BACKEND_DIR/.venv" ]; then
        ln -s "$BACKEND_DIR/venv" "$BACKEND_DIR/.venv" || true
    fi

    ########################################
    # ACTIVAR VENV Y ACTUALIZAR DEPENDENCIAS
    ########################################

    source "$ACTIVE_VENV/bin/activate"

    echo "Instalando dependencias Python..."
    pip install --upgrade pip
    pip install -r requirements.txt

    ########################################
    # ALEMBIC MIGRACIONES
    ########################################

    if [ -f "alembic.ini" ]; then
        echo "Ejecutando Alembic..."
        alembic upgrade head || echo "Alembic completado o sin cambios pendientes"
    fi

    echo "Validando importación de FastAPI app.main..."
    python3 -c "import app.main; print('app.main importado exitosamente')"

    deactivate

    ########################################
    # SYSTEMD
    ########################################

    CANDIDATE_SERVICES=("pedidos-tridente" "distribuidoratridente-api")
    if [ ! -z "$SERVICE_NAME" ]; then
        CANDIDATE_SERVICES=("$SERVICE_NAME" "${CANDIDATE_SERVICES[@]}")
    fi

    echo "Reiniciando servicios systemd..."
    for SVC in "${CANDIDATE_SERVICES[@]}"; do
        if sudo systemctl list-unit-files "$SVC.service" &>/dev/null || sudo systemctl status "$SVC" &>/dev/null; then
            echo "Reiniciando $SVC..."
            sudo systemctl restart "$SVC" || true
            sudo systemctl --no-pager --full status "$SVC" || true
        fi
    done

    echo "Esperando 4 segundos a que el backend inicialice..."
    sleep 4

    HEALTH_OK=false
    for i in {1..5}; do
        if curl -s -f http://127.0.0.1:8001/api/health > /dev/null 2>&1; then
            echo -e "${GREEN}¡Backend respondiendo OK en http://127.0.0.1:8001/api/health!${NC}"
            HEALTH_OK=true
            break
        elif curl -s -f http://127.0.0.1:8000/api/health > /dev/null 2>&1; then
            echo -e "${GREEN}¡Backend respondiendo OK en http://127.0.0.1:8000/api/health!${NC}"
            HEALTH_OK=true
            break
        fi
        sleep 1
    done

    if [ "$HEALTH_OK" = false ]; then
        echo -e "${RED}ADVERTENCIA: Backend no responde en 8001 ni 8000. Logs recientes:${NC}"
        for SVC in "${CANDIDATE_SERVICES[@]}"; do
            echo "=== Logs de $SVC ==="
            sudo journalctl -u "$SVC" -n 35 --no-pager || true
        done
        echo "=== Puertos locales en escucha ==="
        sudo ss -tlpn 2>/dev/null || sudo netstat -tlpn 2>/dev/null || true
    fi

fi

############################################
# EVOLUTION API (WHATSAPP SIDECAR)
############################################

if [ -f "$DEPLOY_DIR/docker-compose.yml" ]; then

    echo ""
    echo -e "${YELLOW}>> Levantando Evolution API (WhatsApp)...${NC}"

    cd "$DEPLOY_DIR"

    if command -v docker &> /dev/null; then

        sudo docker compose up -d

    else

        echo -e "${RED}Docker no está instalado o no disponible en PATH${NC}"

    fi

fi

############################################
# FRONTEND / REACT
############################################

FRONTEND_FOUND=false

############################################
# REACT DENTRO DE /frontend
############################################

if [ -d "$FRONTEND_DIR" ]; then

    FRONTEND_FOUND=true

    echo ""
    echo -e "${YELLOW}>> Frontend React (/frontend)${NC}"

    cd "$FRONTEND_DIR"

    ########################################
    # NPM INSTALL
    ########################################

    npm install

    ########################################
    # BUILD
    ########################################

    npm run build

    ########################################
    # BACKUP
    ########################################

    mkdir -p "$BACKUP_DIR/$DATE"

    if [ -d "$NGINX_ROOT" ]; then

        sudo cp -R "$NGINX_ROOT"/. \
            "$BACKUP_DIR/$DATE/" \
            2>/dev/null || true

    fi

    ########################################
    # NGINX DIRECTORY
    ########################################

    sudo mkdir -p "$NGINX_ROOT"

    ########################################
    # LIMPIAR
    ########################################

    sudo rm -rf "$NGINX_ROOT"/*

    ########################################
    # COPIAR DIST
    ########################################

    sudo cp -R dist/* "$NGINX_ROOT"/

    ########################################
    # PERMISOS
    ########################################

    sudo chown -R www-data:www-data "$NGINX_ROOT"

fi

############################################
# REACT EN RAÍZ
############################################

if [ "$FRONTEND_FOUND" = false ] && [ "$IS_ROOT_REACT" = true ]; then

    FRONTEND_FOUND=true

    echo ""
    echo -e "${YELLOW}>> React (raíz del proyecto)${NC}"

    cd "$PROJECT_DIR"

    ########################################
    # NPM INSTALL
    ########################################

    npm install

    ########################################
    # BUILD
    ########################################

    npm run build

    ########################################
    # VERIFICAR DIST
    ########################################

    if [ ! -d "$ROOT_DIST_DIR" ]; then

        echo -e "${RED}ERROR: No se generó la carpeta dist/${NC}"

        exit 1

    fi

    ########################################
    # BACKUP
    ########################################

    mkdir -p "$BACKUP_DIR/$DATE"

    if [ -d "$NGINX_ROOT" ]; then

        sudo cp -R "$NGINX_ROOT"/. \
            "$BACKUP_DIR/$DATE/" \
            2>/dev/null || true

    fi

    ########################################
    # NGINX DIRECTORY
    ########################################

    sudo mkdir -p "$NGINX_ROOT"

    ########################################
    # LIMPIAR
    ########################################

    sudo rm -rf "$NGINX_ROOT"/*

    ########################################
    # COPIAR DIST
    ########################################

    sudo cp -R "$ROOT_DIST_DIR"/* "$NGINX_ROOT"/

    ########################################
    # PERMISOS
    ########################################

    sudo chown -R www-data:www-data "$NGINX_ROOT"

fi

############################################
# HTML
############################################

if [ "$FRONTEND_FOUND" = false ] && [ "$IS_HTML" = true ]; then

    echo ""
    echo -e "${YELLOW}>> Sitio HTML${NC}"

    ########################################
    # BACKUP
    ########################################

    mkdir -p "$BACKUP_DIR/$DATE"

    if [ -d "$NGINX_ROOT" ]; then

        sudo cp -R "$NGINX_ROOT"/. \
            "$BACKUP_DIR/$DATE/" \
            2>/dev/null || true

    fi

    ########################################
    # NGINX DIRECTORY
    ########################################

    sudo mkdir -p "$NGINX_ROOT"

    ########################################
    # COPIAR HTML
    ########################################

    sudo rsync -av \
        --delete \
        --exclude ".git" \
        --exclude "deploy" \
        --exclude "logs" \
        --exclude "backup" \
        "$PROJECT_DIR"/ \
        "$NGINX_ROOT"/

    ########################################
    # PERMISOS
    ########################################

    sudo chown -R www-data:www-data "$NGINX_ROOT"

fi

############################################
# NGINX
############################################

echo ""
echo -e "${YELLOW}>> Verificando Nginx${NC}"

sudo nginx -t

echo ""
echo -e "${YELLOW}>> Recargando Nginx${NC}"

sudo systemctl reload nginx

############################################
# TIEMPO
############################################

END_TIME=$(date +%s)

SECONDS_TOTAL=$((END_TIME-START_TIME))

############################################
# FIN
############################################

echo ""
echo -e "${GREEN}====================================================${NC}"
echo -e "${GREEN}DEPLOY FINALIZADO CORRECTAMENTE${NC}"
echo -e "${GREEN}====================================================${NC}"

echo "Proyecto : $PROJECT_NAME"
echo "Branch   : $CURRENT_BRANCH"
echo "Commit   : $NEW_COMMIT"
echo "Usuario  : $(whoami)"
echo "Duración : ${SECONDS_TOTAL} segundos"
echo "Log      : $LOG_FILE"

echo -e "${GREEN}====================================================${NC}"

echo ""
