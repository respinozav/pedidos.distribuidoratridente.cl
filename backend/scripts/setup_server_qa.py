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

    # 0. Desactivar Apache2 si existe para liberar el puerto 80
    if shutil.which("apache2") or Path("/etc/apache2").exists():
        print("Desactivando Apache2 para liberar el puerto 80 para Nginx...")
        subprocess.run(["systemctl", "stop", "apache2"], check=False)
        subprocess.run(["systemctl", "disable", "apache2"], check=False)

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
    print("Verificando configuración de Nginx...")
    t = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if t.stdout:
        print(t.stdout.strip())
    if t.stderr:
        print(t.stderr.strip())

    subprocess.run(["systemctl", "enable", "nginx"], check=False)
    r = subprocess.run(["systemctl", "restart", "nginx"], capture_output=True, text=True)
    if r.returncode != 0:
        print("ERROR al reiniciar Nginx:", r.stderr.strip())
        subprocess.run(["journalctl", "-u", "nginx", "-n", "20", "--no-pager"], check=False)
    else:
        print("✓ Servicio Nginx reiniciado y activo.")

    # 8. Configurar SSL / HTTPS en puerto 443 con Certbot
    setup_ssl_certbot()

    print("=" * 60)
    print("SERVIDOR QA CONFIGURADO EXITOSAMENTE")
    print("=" * 60)


def setup_ssl_certbot():
    print("\n--- VERIFICANDO CONFIGURACION SSL / HTTPS (PUERTO 443) ---")
    cert_dir = Path("/etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl")
    if cert_dir.exists():
        print("✓ Certificado SSL activo en /etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl")
        return

    # Instalar certbot si es necesario
    if not shutil.which("certbot"):
        print("Instalando Certbot y python3-certbot-nginx...")
        subprocess.run(["apt-get", "update", "-y"], check=False)
        subprocess.run(["apt-get", "install", "-y", "certbot", "python3-certbot-nginx"], check=False)

    if shutil.which("certbot"):
        print("Solicitando certificado SSL para pedidos-qa.distribuidoratridente.cl...")
        res = subprocess.run([
            "certbot", "--nginx",
            "-d", "pedidos-qa.distribuidoratridente.cl",
            "--non-interactive",
            "--agree-tos",
            "-m", "admin@correodistribuidoratridente.cl",
            "--redirect"
        ], capture_output=True, text=True)
        if res.returncode == 0:
            print("✓ Certificado SSL (HTTPS 443) emitido y configurado exitosamente con redirección automática!")
            subprocess.run(["systemctl", "reload", "nginx"], check=False)
        else:
            print("Aviso Certbot: No se pudo emitir el certificado automáticamente en este intento.")
            print("Verifica que los puertos 80 y 443 estén abiertos en el Security Group de AWS.")
            if res.stderr or res.stdout:
                output = (res.stderr or res.stdout).strip()
                print("Detalle:", output[-300:])


if __name__ == "__main__":
    setup_qa_system()
