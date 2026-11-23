#!/usr/bin/env python3
"""
Script utilitario para inicializar y configurar el servidor de QA:
1. Crea el servicio systemd /etc/systemd/system/pedidos-tridente-qa.service si no existe.
2. Crea el virtualhost de Nginx /etc/nginx/sites-available/pedidos-qa.distribuidoratridente.cl si no existe.
3. Habilita y recarga los servicios.
"""

import os
import subprocess
import sys
from pathlib import Path

QA_DIR = "/var/www/pedidos-qa.distribuidoratridente.cl"
QA_HTML_DIR = "/var/www/html/pedidos-qa.distribuidoratridente.cl"
QA_SERVICE_PATH = Path("/etc/systemd/system/pedidos-tridente-qa.service")
QA_NGINX_PATH = Path("/etc/nginx/sites-available/pedidos-qa.distribuidoratridente.cl")
QA_NGINX_ENABLED = Path("/etc/nginx/sites-enabled/pedidos-qa.distribuidoratridente.cl")

SERVICE_CONTENT = f"""[Unit]
Description=API Pedidos Distribuidora Tridente QA
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory={QA_DIR}/backend
Environment="PATH={QA_DIR}/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile={QA_DIR}/backend/.env
ExecStart={QA_DIR}/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

NGINX_CONTENT = f"""server {{
    listen 80;
    server_name pedidos-qa.distribuidoratridente.cl;

    root {QA_HTML_DIR};
    index index.html;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location /api {{
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""


def setup_qa_system():
    print("=" * 60)
    print("CONFIGURACION AUTOMATICA DEL SERVIDOR QA")
    print("=" * 60)

    # 1. Crear directorio HTML si no existe
    Path(QA_HTML_DIR).mkdir(parents=True, exist_ok=True)
    print(f"✓ Directorio HTML listo: {QA_HTML_DIR}")

    # 2. Configurar servicio systemd si no existe
    if not QA_SERVICE_PATH.exists() and not Path("/etc/systemd/system/pedidos-tridente.service").exists():
        QA_SERVICE_PATH.write_text(SERVICE_CONTENT, encoding="utf-8")
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", "pedidos-tridente-qa"], check=False)
        print(f"✓ Servicio systemd creado y habilitado: {QA_SERVICE_PATH}")
    else:
        print("✓ Servicio systemd ya se encuentra configurado.")

    # 3. Configurar Nginx si no existe
    if not QA_NGINX_PATH.exists():
        QA_NGINX_PATH.write_text(NGINX_CONTENT, encoding="utf-8")
        if not QA_NGINX_ENABLED.exists():
            try:
                QA_NGINX_ENABLED.symlink_to(QA_NGINX_PATH)
            except Exception:
                pass
        subprocess.run(["nginx", "-t"], check=False)
        subprocess.run(["systemctl", "reload", "nginx"], check=False)
        print(f"✓ Configuración Nginx creada y recargada: {QA_NGINX_PATH}")
    else:
        print("✓ Configuración Nginx ya se encuentra presente.")

    print("=" * 60)
    print("SERVIDOR QA CONFIGURADO EXITOSAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    setup_qa_system()
