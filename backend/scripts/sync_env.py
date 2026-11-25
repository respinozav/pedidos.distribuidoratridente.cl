"""
Script utilitario para sincronizar y actualizar variables de entorno en archivos .env
durante despliegues automatizados (CI/CD) para Production y QA.
"""
import os
import sys
from pathlib import Path


def sync_env_file(env_path_str: str) -> bool:
    env_path = Path(env_path_str)
    if not env_path.exists():
        print(f"[sync_env] Archivo no encontrado: {env_path}")
        return False

    deploy_env = os.environ.get("DEPLOY_ENV", "").strip().lower()

    # Mapeo de variables de entorno pasadas por CI/CD
    var_map = {
        "DATABASE_HOST": os.environ.get("AWS_HOST_BD"),
        "DATABASE_USER": os.environ.get("AWS_USER_BD"),
        "DATABASE_PASSWORD": os.environ.get("AWS_PASSWORD_BD"),
        "DATABASE_SCHEMA": os.environ.get("AWS_SCHEME_BD"),
        "POSTGREST_SCHEMA": os.environ.get("AWS_SCHEME_BD"),
        "DEFONTANA_API_BASE_URL": os.environ.get("DEFONTANA_API_BASE_URL"),
        "DEFONTANA_CLIENT_ID": os.environ.get("DEFONTANA_CLIENT_ID"),
        "DEFONTANA_COMPANY_ID": os.environ.get("DEFONTANA_COMPANY_ID"),
        "DEFONTANA_API_USER": os.environ.get("DEFONTANA_API_USER"),
        "DEFONTANA_API_PASSWORD": os.environ.get("DEFONTANA_API_PASSWORD"),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY"),
        "GEMINI_MODEL": os.environ.get("GEMINI_MODEL"),
        "JWT_SECRET_KEY": os.environ.get("JWT_SECRET_KEY"),
        "CORS_ORIGINS": os.environ.get("CORS_ORIGINS"),
    }

    # Fallbacks inteligentes para CORS_ORIGINS si no viene explícita
    if not var_map["CORS_ORIGINS"]:
        if deploy_env == "qa":
            var_map["CORS_ORIGINS"] = "http://pedidos-qa.distribuidoratridente.cl,https://pedidos-qa.distribuidoratridente.cl,http://localhost:5173"
        elif deploy_env == "production":
            var_map["CORS_ORIGINS"] = "https://pedidos.distribuidoratridente.cl,http://pedidos.distribuidoratridente.cl,http://localhost:5173"

    # Filtrar solo aquellas variables que tienen un valor no vacío definido
    active_vars = {k: v for k, v in var_map.items() if v is not None and str(v).strip() != ""}

    with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    updated = set()
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if "=" in line and not stripped.startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in active_vars:
                new_lines.append(f"{key}={active_vars[key]}\n")
                updated.add(key)
                continue
        new_lines.append(line)

    # Si alguna variable configurada no existía previamente en el archivo, agregarla al final
    missing = [k for k in active_vars if k not in updated]
    if missing:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append("\n# Variables sincronizadas por CI/CD\n")
        for k in missing:
            new_lines.append(f"{k}={active_vars[k]}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"[sync_env] Archivo sincronizado exitosamente: {env_path} ({len(updated)} actualizadas, {len(missing)} agregadas)")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python sync_env.py <ruta_al_archivo_env> [ruta2 ...]")
        sys.exit(1)

    for target in sys.argv[1:]:
        sync_env_file(target)
