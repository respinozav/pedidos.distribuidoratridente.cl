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

    host = os.environ.get("AWS_HOST_BD")
    user = os.environ.get("AWS_USER_BD")
    pwd = os.environ.get("AWS_PASSWORD_BD")
    sch = os.environ.get("AWS_SCHEME_BD")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

    with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    updated = set()
    new_lines = []

    for l in lines:
        if "=" in l and not l.strip().startswith("#"):
            k = l.split("=", 1)[0].strip()
            if k == "DATABASE_HOST" and host:
                new_lines.append(f"DATABASE_HOST={host}\n")
                updated.add(k)
                continue
            if k == "DATABASE_USER" and user:
                new_lines.append(f"DATABASE_USER={user}\n")
                updated.add(k)
                continue
            if k == "DATABASE_PASSWORD" and pwd:
                new_lines.append(f"DATABASE_PASSWORD={pwd}\n")
                updated.add(k)
                continue
            if k == "DATABASE_SCHEMA" and sch:
                new_lines.append(f"DATABASE_SCHEMA={sch}\n")
                updated.add(k)
                continue
            if k == "POSTGREST_SCHEMA" and sch:
                new_lines.append(f"POSTGREST_SCHEMA={sch}\n")
                updated.add(k)
                continue
            if k == "GEMINI_MODEL" and gemini_model:
                new_lines.append(f"GEMINI_MODEL={gemini_model}\n")
                updated.add(k)
                continue
            if k == "GEMINI_API_KEY" and gemini_key:
                new_lines.append(f"GEMINI_API_KEY={gemini_key}\n")
                updated.add(k)
                continue
        new_lines.append(l)

    # Si alguna variable requerida no existia previamente, agregarla
    if host and "DATABASE_HOST" not in updated:
        new_lines.append(f"DATABASE_HOST={host}\n")
    if user and "DATABASE_USER" not in updated:
        new_lines.append(f"DATABASE_USER={user}\n")
    if pwd and "DATABASE_PASSWORD" not in updated:
        new_lines.append(f"DATABASE_PASSWORD={pwd}\n")
    if sch and "DATABASE_SCHEMA" not in updated:
        new_lines.append(f"DATABASE_SCHEMA={sch}\n")
    if sch and "POSTGREST_SCHEMA" not in updated:
        new_lines.append(f"POSTGREST_SCHEMA={sch}\n")
    if gemini_key and "GEMINI_API_KEY" not in updated:
        new_lines.append(f"GEMINI_API_KEY={gemini_key}\n")
    if gemini_model and "GEMINI_MODEL" not in updated:
        new_lines.append(f"GEMINI_MODEL={gemini_model}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    print(f"[sync_env] Archivo sincronizado exitosamente: {env_path}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python sync_env.py <ruta_al_archivo_env>")
        sys.exit(1)

    for target in sys.argv[1:]:
        sync_env_file(target)
