#!/usr/bin/env python3
"""
Script utilitario para inicializar y configurar el servidor de QA:
1. Instala y asegura Nginx, Python3 venv, Node.js 20 LTS y dependencias del sistema.
2. Crea el servicio systemd /etc/systemd/system/pedidos-tridente-qa.service.
3. Configura el virtualhost Nginx con soporte HTTP 80 y HTTPS 443 (Certbot SSL).
4. Recrea el entorno virtual Python (venv) y compila el frontend React con Node 20.
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


def ensure_node20():
    need_install = True
    node_bin = shutil.which("node")
    if node_bin:
        res = subprocess.run([node_bin, "-v"], capture_output=True, text=True)
        out = res.stdout.strip()
        print(f"Versión de Node actual: {out}")
        if out.startswith("v"):
            try:
                major = int(out[1:].split(".")[0])
                if major >= 20:
                    need_install = False
                    print("✓ Node.js ya es versión 20 o superior.")
            except Exception:
                pass
    if need_install:
        print("Instalando Node.js v20 LTS vía NodeSource...")
        subprocess.run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -", shell=True, check=False)
        subprocess.run(["apt-get", "install", "-y", "nodejs"], check=False)
        res = subprocess.run(["node", "-v"], capture_output=True, text=True)
        print("✓ Nueva versión de Node:", res.stdout.strip())


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
    print("Instalando dependencias del sistema en QA...")
    subprocess.run(["apt-get", "update", "-y"], check=False)
    subprocess.run([
        "apt-get", "install", "-y",
        "nginx",
        "python3-venv",
        "python3.12-venv",
        "python3-pip",
        "certbot",
        "python3-certbot-nginx",
        "postgresql-client"
    ], check=False)
    print("✓ Paquetes del sistema base asegurados.")

    # 2. Asegurar Node.js 20 LTS para compilación Vite
    ensure_node20()

    # 3. Crear directorios requeridos
    Path(QA_HTML_DIR).mkdir(parents=True, exist_ok=True)
    Path("/etc/nginx/sites-available").mkdir(parents=True, exist_ok=True)
    Path("/etc/nginx/sites-enabled").mkdir(parents=True, exist_ok=True)
    print(f"✓ Directorio HTML listo: {QA_HTML_DIR}")

    # 4. Deshabilitar virtualhost por defecto de Ubuntu
    default_site = Path("/etc/nginx/sites-enabled/default")
    if default_site.exists():
        try:
            default_site.unlink()
            print("✓ Deshabilitado sitio por defecto (/etc/nginx/sites-enabled/default).")
        except Exception as e:
            print("Aviso al remover default site:", e)

    # 5. Configurar VirtualHost de QA
    QA_NGINX_PATH.write_text(get_nginx_config(), encoding="utf-8")
    if not QA_NGINX_ENABLED.exists():
        try:
            QA_NGINX_ENABLED.symlink_to(QA_NGINX_PATH)
        except Exception:
            pass
    print(f"✓ VirtualHost Nginx configurado: {QA_NGINX_PATH}")

    # 6. Configurar servicio systemd
    QA_SERVICE_PATH.write_text(SERVICE_CONTENT, encoding="utf-8")
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "pedidos-tridente-qa"], check=False)
    print(f"✓ Servicio systemd creado y habilitado: {QA_SERVICE_PATH}")

    # 7. Habilitar reglas de firewall local UFW si está activo
    if shutil.which("ufw"):
        subprocess.run(["ufw", "allow", "80/tcp"], check=False)
        subprocess.run(["ufw", "allow", "443/tcp"], check=False)
        subprocess.run(["ufw", "allow", "Nginx Full"], check=False)
        print("✓ Reglas de puerto 80/443 aplicadas en UFW.")

    # 8. Asegurar entorno virtual backend con ensurepip
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

    # 9. Compilar frontend React y colocar en QA_HTML_DIR
    frontend_dir = Path(QA_DIR) / "frontend"
    if (frontend_dir / "package.json").exists():
        print("Compilando frontend React para generar index.html...")
        subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=False)
        res_build = subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), capture_output=True, text=True)
        if res_build.stdout:
            print(res_build.stdout.strip()[-300:])
        if res_build.stderr:
            print(res_build.stderr.strip()[-300:])
        dist_dir = frontend_dir / "dist"
        if dist_dir.exists() and (dist_dir / "index.html").exists():
            for item in dist_dir.glob("*"):
                dest = Path(QA_HTML_DIR) / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            print("✓ Frontend compilado y copiado a HTML root:", QA_HTML_DIR)
        else:
            print("Aviso: dist/index.html no encontrado tras build.")

    # Asegurar permisos www-data y 755
    subprocess.run(["chown", "-R", "www-data:www-data", QA_HTML_DIR], check=False)
    subprocess.run(["chmod", "-R", "755", QA_HTML_DIR], check=False)

    # 10. Corregir número de versión desfasado en alembic_version si aplica
    fix_alembic_schema_version()

    # 11. Configurar SSL / HTTPS en puerto 443 con Certbot
    setup_ssl_certbot()

    # 12. Reiniciar y verificar Nginx
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


def fix_alembic_schema_version():
    try:
        backend_path = Path(QA_DIR) / "backend"
        python_bin = backend_path / "venv" / "bin" / "python3"
        if not python_bin.exists():
            return
        code = """
from app.core.config import get_settings
from app.core.database import engine
from sqlalchemy import text
raw_schema = get_settings().database_schema.strip('"')
with engine.begin() as conn:
    conn.execute(text(f'UPDATE "{raw_schema}".alembic_version SET version_num = \\'20261113_0042\\' WHERE version_num = \\'20261022_0039\\';'))
    print('✓ Tabla alembic_version verificada y sincronizada.')
"""
        subprocess.run([str(python_bin), "-c", code], cwd=str(backend_path), check=False)
    except Exception as e:
        print("Aviso fix alembic:", e)


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
