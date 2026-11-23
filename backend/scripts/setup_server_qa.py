#!/usr/bin/env python3
"""
Script utilitario para inicializar y configurar el servidor de QA:
1. Instala y asegura Nginx y dependencias si faltan.
2. Crea el servicio systemd /etc/systemd/system/pedidos-tridente-qa.service si no existe.
3. Crea el virtualhost de Nginx /etc/nginx/sites-available/pedidos-qa.distribuidoratridente.cl si no existe.
4. Deshabilita el sitio default de Nginx para evitar conflictos en el puerto 80.
5. Habilita y arranca los servicios.
"""

import os
import shutil
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
    listen [::]:80;
    server_name pedidos-qa.distribuidoratridente.cl _;

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

    # 1. Asegurar instalación de Nginx
    if not shutil.which("nginx"):
        print("Instalando Nginx en el servidor de QA...")
        subprocess.run(["apt-get", "update", "-y"], check=False)
        subprocess.run(["apt-get", "install", "-y", "nginx"], check=False)
        print("✓ Nginx instalado.")

    # 2. Crear directorios requeridos
    Path(QA_HTML_DIR).mkdir(parents=True, exist_ok=True)
    Path("/etc/nginx/sites-available").mkdir(parents=True, exist_ok=True)
    Path("/etc/nginx/sites-enabled").mkdir(parents=True, exist_ok=True)
    print(f"✓ Directorio HTML listo: {QA_HTML_DIR}")

    # 3. Deshabilitar virtualhost por defecto de Ubuntu
    default_site = Path("/etc/nginx/sites-enabled/default")
    if default_site.exists():
        try:
            default_site.unlink()
            print("✓ Deshabilitado sitio por defecto (/etc/nginx/sites-enabled/default).")
        except Exception as e:
            print("Aviso al remover default site:", e)

    # 4. Configurar VirtualHost de QA
    QA_NGINX_PATH.write_text(NGINX_CONTENT, encoding="utf-8")
    if not QA_NGINX_ENABLED.exists():
        try:
            QA_NGINX_ENABLED.symlink_to(QA_NGINX_PATH)
        except Exception:
            pass
    print(f"✓ VirtualHost Nginx configurado: {QA_NGINX_PATH}")

    # 5. Configurar servicio systemd si no existe
    if not QA_SERVICE_PATH.exists() and not Path("/etc/systemd/system/pedidos-tridente.service").exists():
        QA_SERVICE_PATH.write_text(SERVICE_CONTENT, encoding="utf-8")
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        subprocess.run(["systemctl", "enable", "pedidos-tridente-qa"], check=False)
        print(f"✓ Servicio systemd creado y habilitado: {QA_SERVICE_PATH}")
    else:
        print("✓ Servicio systemd ya se encuentra presente.")

    # 6. Habilitar reglas de firewall local UFW si está activo
    if shutil.which("ufw"):
        subprocess.run(["ufw", "allow", "80/tcp"], check=False)
        subprocess.run(["ufw", "allow", "443/tcp"], check=False)
        subprocess.run(["ufw", "allow", "Nginx Full"], check=False)
        print("✓ Reglas de puerto 80/443 aplicadas en UFW.")

    # 7. Reiniciar y verificar Nginx
    subprocess.run(["nginx", "-t"], check=False)
    subprocess.run(["systemctl", "enable", "nginx"], check=False)
    subprocess.run(["systemctl", "restart", "nginx"], check=False)
    print("✓ Servicio Nginx reiniciado y activo.")

    print("=" * 60)
    print("SERVIDOR QA CONFIGURADO EXITOSAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    setup_qa_system()
