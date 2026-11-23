#!/usr/bin/env python3
"""
Script utilitario para inicializar y configurar el servidor de QA:
1. Instala y asegura Nginx, Python3 venv, Node.js y dependencias del sistema.
2. Crea el servicio systemd /etc/systemd/system/pedidos-tridente-qa.service.
3. Configura el virtualhost Nginx con soporte HTTP 80 y HTTPS 443 (Certbot SSL).
4. Recrea el entorno virtual Python (venv) y compila el frontend.
5. Habilita y arranca todos los servicios.
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


def get_nginx_config() -> str:
    cert_file = Path("/etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl/fullchain.pem")
    key_file = Path("/etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl/privkey.pem")

    if cert_file.exists() and key_file.exists():
        return f"""server {{
    listen 80;
    listen [::]:80;
    server_name pedidos-qa.distribuidoratridente.cl;
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name pedidos-qa.distribuidoratridente.cl;

    ssl_certificate /etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl/privkey.pem;

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
    else:
        return f"""server {{
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

    # 1. Asegurar instalación de paquetes del sistema operativo
    print("Instalando dependencias del sistema en QA (Nginx, Python3-venv, Pip, Certbot, Node)...")
    subprocess.run(["apt-get", "update", "-y"], check=False)
    subprocess.run([
        "apt-get", "install", "-y",
        "nginx",
        "python3-venv",
        "python3.12-venv",
        "python3-pip",
        "nodejs",
        "npm",
        "certbot",
        "python3-certbot-nginx",
        "postgresql-client"
    ], check=False)
    print("✓ Paquetes del sistema asegurados.")

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
    QA_NGINX_PATH.write_text(get_nginx_config(), encoding="utf-8")
    if not QA_NGINX_ENABLED.exists():
        try:
            QA_NGINX_ENABLED.symlink_to(QA_NGINX_PATH)
        except Exception:
            pass
    print(f"✓ VirtualHost Nginx configurado: {QA_NGINX_PATH}")

    # 5. Configurar servicio systemd
    QA_SERVICE_PATH.write_text(SERVICE_CONTENT, encoding="utf-8")
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "pedidos-tridente-qa"], check=False)
    print(f"✓ Servicio systemd creado y habilitado: {QA_SERVICE_PATH}")

    # 6. Habilitar reglas de firewall local UFW si está activo
    if shutil.which("ufw"):
        subprocess.run(["ufw", "allow", "80/tcp"], check=False)
        subprocess.run(["ufw", "allow", "443/tcp"], check=False)
        subprocess.run(["ufw", "allow", "Nginx Full"], check=False)
        print("✓ Reglas de puerto 80/443 aplicadas en UFW.")

    # 7. Asegurar entorno virtual backend con ensurepip
    venv_dir = Path(f"{QA_DIR}/backend/venv")
    pip_bin = venv_dir / "bin" / "pip"
    if not pip_bin.exists():
        print(f"Creando entorno virtual Python funcional en {venv_dir}...")
        if venv_dir.exists():
            shutil.rmtree(venv_dir, ignore_errors=True)
        subprocess.run(["python3", "-m", "venv", str(venv_dir)], check=False)
        if pip_bin.exists():
            print("✓ Entorno virtual venv creado exitosamente.")
            subprocess.run([str(pip_bin), "install", "--upgrade", "pip"], check=False)
        else:
            print("Aviso: pip no se encontró tras venv.")

    # 8. Asegurar index.html en frontend
    html_index = Path(QA_HTML_DIR) / "index.html"
    frontend_dir = Path(QA_DIR) / "frontend"
    if not html_index.exists() and (frontend_dir / "package.json").exists():
        print("Compilando frontend React para generar index.html...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=False)
        subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=False)
        dist_dir = frontend_dir / "dist"
        if dist_dir.exists():
            for item in dist_dir.glob("*"):
                dest = Path(QA_HTML_DIR) / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            print("✓ Frontend compilado y copiado a HTML root.")

    # Asegurar permisos www-data
    subprocess.run(["chown", "-R", "www-data:www-data", QA_HTML_DIR], check=False)

    # 9. Configurar SSL / HTTPS en puerto 443 con Certbot
    setup_ssl_certbot()

    # 10. Reiniciar y verificar Nginx
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

    print("=" * 60)
    print("SERVIDOR QA CONFIGURADO EXITOSAMENTE")
    print("=" * 60)


def setup_ssl_certbot():
    print("\n--- VERIFICANDO CONFIGURACION SSL / HTTPS (PUERTO 443) ---")
    cert_file = Path("/etc/letsencrypt/live/pedidos-qa.distribuidoratridente.cl/fullchain.pem")
    if not cert_file.exists():
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
                print("✓ Certificado SSL emitido con éxito vía certbot!")
            else:
                print("Aviso Certbot:", (res.stderr or res.stdout).strip()[-200:])

    # Re-escribir virtualhost para garantizar bloque 443 si los certificados existen
    QA_NGINX_PATH.write_text(get_nginx_config(), encoding="utf-8")
    subprocess.run(["nginx", "-t"], check=False)
    subprocess.run(["systemctl", "reload", "nginx"], check=False)
    print("✓ Virtualhost Nginx actualizado con directivas SSL 443.")


if __name__ == "__main__":
    setup_qa_system()
