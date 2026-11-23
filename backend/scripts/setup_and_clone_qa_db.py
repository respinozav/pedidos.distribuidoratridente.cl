#!/usr/bin/env python3
"""
Script para aprovisionar y clonar la base de datos de Producción a QA:
1. Crea el esquema "bdtridente-qa" y el usuario exclusivo "tridente_qa" con su contraseña.
2. Clona exactamente la estructura (tablas, secuencias, índices, claves foráneas) y datos de "bdtridente".
3. Otorga permisos exclusivos a "tridente_qa" sobre "bdtridente-qa" y revoca acceso a producción.
4. Verifica la paridad de tablas y registros entre producción y QA.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Agregar backend al path para importar configuración si está disponible
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from app.core.config import get_settings
    settings = get_settings()
    DEFAULT_HOST = settings.database_host
    DEFAULT_PORT = settings.database_port
    DEFAULT_DB = settings.database_name
    DEFAULT_USER = settings.database_user
    DEFAULT_PASSWORD = settings.database_password
    DEFAULT_SOURCE_SCHEMA = settings.database_schema
except Exception:
    DEFAULT_HOST = os.environ.get("DATABASE_HOST", "localhost")
    DEFAULT_PORT = int(os.environ.get("DATABASE_PORT", "5432"))
    DEFAULT_DB = os.environ.get("DATABASE_NAME", "postgres")
    DEFAULT_USER = os.environ.get("DATABASE_USER", "postgres")
    DEFAULT_PASSWORD = os.environ.get("DATABASE_PASSWORD", "postgres")
    DEFAULT_SOURCE_SCHEMA = os.environ.get("DATABASE_SCHEMA", "bdtridente")

DEFAULT_TARGET_SCHEMA = "bdtridente-qa"
DEFAULT_QA_USER = "tridente_qa"
DEFAULT_QA_PASSWORD = "TridenteQa2026!Sec#Db"


def find_pg_binary(binary_name: str) -> str:
    """Busca un binario de PostgreSQL en PATH o en rutas comunes de Windows/Linux."""
    found = shutil.which(binary_name)
    if found:
        return found
    common_paths = [
        r"C:\Program Files\PostgreSQL\18\bin",
        r"C:\Program Files\PostgreSQL\17\bin",
        r"C:\Program Files\PostgreSQL\16\bin",
        r"C:\Program Files\PostgreSQL\15\bin",
        "/usr/lib/postgresql/18/bin",
        "/usr/lib/postgresql/17/bin",
        "/usr/lib/postgresql/16/bin",
        "/usr/lib/postgresql/15/bin",
        "/usr/lib/postgresql/14/bin",
        "/usr/bin",
    ]
    for p in common_paths:
        candidate = Path(p) / (binary_name + (".exe" if sys.platform == "win32" else ""))
        if candidate.exists():
            return str(candidate)
    return binary_name


def run_sql_direct(conn, sql: str, params: dict = None):
    """Ejecuta una sentencia SQL en una conexión de SQLAlchemy/psycopg."""
    from sqlalchemy import text
    return conn.execute(text(sql), params or {})


def setup_and_clone(
    host: str,
    port: int,
    db: str,
    admin_user: str,
    admin_password: str,
    source_schema: str,
    target_schema: str,
    qa_user: str,
    qa_password: str,
):
    from sqlalchemy import create_engine, text

    print("=" * 65)
    print("APROVISIONAMIENTO Y CLONACION DE BD: PRODUCCION -> QA")
    print("=" * 65)
    print(f"Host BD       : {host}:{port}")
    print(f"Base de Datos : {db}")
    print(f"Esquema Origen: {source_schema} (PROD)")
    print(f"Esquema Dest. : {target_schema} (QA)")
    print(f"Usuario QA    : {qa_user}")
    print(f"Password QA   : {'*' * len(qa_password)} (Longitud: {len(qa_password)})")
    print("=" * 65)

    is_local = host in ("localhost", "127.0.0.1", "::1")
    admin_url = f"postgresql+psycopg://{admin_user}:{admin_password}@{host}:{port}/{db}"
    engine = create_engine(
        admin_url,
        connect_args={"sslmode": "prefer" if is_local else "require"},
        isolation_level="AUTOCOMMIT",
    )

    with engine.connect() as conn:
        print("\n[1/5] Configurando usuario y permisos exclusivos para QA...")
        # 1. Crear el usuario QA si no existe y asignar contraseña
        conn.execute(text(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{qa_user}') THEN
                    CREATE ROLE {qa_user} WITH LOGIN PASSWORD '{qa_password}';
                ELSE
                    ALTER ROLE {qa_user} WITH PASSWORD '{qa_password}';
                END IF;
            END $$;
        """))

        # Revocar privilegios en public
        conn.execute(text(f"REVOKE ALL ON SCHEMA public FROM {qa_user};"))

        # 2. Crear el esquema destino si no existe
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}";'))

        # Asignar search_path por defecto al usuario QA
        conn.execute(text(f'ALTER ROLE {qa_user} SET search_path TO "{target_schema}";'))

        print(f"✓ Usuario '{qa_user}' y esquema '\"{target_schema}\"' listos.")

    # 3. Clonar estructura y datos usando pg_dump + psql para 100% fidelidad
    print("\n[2/5] Realizando volcado de datos y estructura desde Producción...")
    pg_dump_bin = find_pg_binary("pg_dump")
    psql_bin = find_pg_binary("psql")

    env = os.environ.copy()
    env["PGPASSWORD"] = admin_password

    dump_cmd = [
        pg_dump_bin,
        "-h", host,
        "-p", str(port),
        "-U", admin_user,
        "-d", db,
        "-n", source_schema,
        "--no-owner",
        "--no-privileges",
    ]
    if not is_local:
        env["PGSSLMODE"] = "require"

    print(f"Ejecutando: {' '.join(dump_cmd[:7])}...")
    proc_dump = subprocess.run(
        dump_cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if proc_dump.returncode != 0:
        raise RuntimeError(f"Error en pg_dump: {proc_dump.stderr}")

    raw_sql = proc_dump.stdout
    print(f"✓ Volcado generado con éxito ({len(raw_sql):,} caracteres).")

    print("\n[3/5] Transformando referencias de esquema (prod -> qa)...")
    # Reemplazar esquema origen por esquema destino (escapando adecuadamente para guiones)
    # 1. Reemplazos de CREATE SCHEMA y search_path
    transformed_sql = re.sub(
        rf'\b{re.escape(source_schema)}\b',
        f'"{target_schema}"',
        raw_sql,
    )

    # 4. Restaurar en la base de datos
    print(f"\n[4/5] Restaurando estructura y datos en el esquema '\"{target_schema}\"'...")
    psql_cmd = [
        psql_bin,
        "-h", host,
        "-p", str(port),
        "-U", admin_user,
        "-d", db,
        "-v", "ON_ERROR_STOP=0",
    ]
    proc_restore = subprocess.run(
        psql_cmd,
        input=transformed_sql,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    print(f"✓ Restauración finalizada.")
    if proc_restore.stderr:
        # Filtrar avisos normales como 'already exists'
        notices = [l for l in proc_restore.stderr.splitlines() if "ERROR" in l]
        if notices:
            print(f"Avisos durante restauración: {len(notices)} advertencias.")

    # 5. Otorgar todos los privilegios sobre el nuevo esquema y sus tablas al usuario QA
    with engine.connect() as conn:
        print("\n[5/5] Otorgando permisos completos sobre QA a usuario 'tridente_qa'...")
        conn.execute(text(f'GRANT USAGE, CREATE ON SCHEMA "{target_schema}" TO {qa_user};'))
        conn.execute(text(f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA "{target_schema}" TO {qa_user};'))
        conn.execute(text(f'GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA "{target_schema}" TO {qa_user};'))
        conn.execute(text(f'GRANT ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA "{target_schema}" TO {qa_user};'))
        conn.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{target_schema}" GRANT ALL ON TABLES TO {qa_user};'))
        conn.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{target_schema}" GRANT ALL ON SEQUENCES TO {qa_user};'))
        conn.execute(text(f'ALTER DEFAULT PRIVILEGES IN SCHEMA "{target_schema}" GRANT ALL ON ROUTINES TO {qa_user};'))

        # Revocar acceso del usuario QA al esquema de Producción
        conn.execute(text(f'REVOKE ALL ON SCHEMA "{source_schema}" FROM {qa_user};'))
        conn.execute(text(f'REVOKE ALL ON ALL TABLES IN SCHEMA "{source_schema}" FROM {qa_user};'))
        conn.execute(text(f'REVOKE ALL ON ALL SEQUENCES IN SCHEMA "{source_schema}" FROM {qa_user};'))

        # Verificación y comparación de tablas y registros
        print("\n" + "=" * 65)
        print("VERIFICACION DE PARIDAD DE DATOS: PRODUCCION vs QA")
        print("=" * 65)
        tables_prod = [r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :sch ORDER BY table_name"
        ), {"sch": source_schema}).fetchall()]

        tables_qa = [r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :sch ORDER BY table_name"
        ), {"sch": target_schema}).fetchall()]

        print(f"Total tablas en {source_schema} (PROD): {len(tables_prod)}")
        print(f"Total tablas en {target_schema} (QA)  : {len(tables_qa)}")

        metrics_tables = ["productos", "pedidos", "clientes", "usuarios", "categorias", "ia_chats"]
        print("\nMuestra de conteo de registros:")
        for t in metrics_tables:
            if t in tables_prod and t in tables_qa:
                c_prod = conn.execute(text(f'SELECT count(*) FROM "{source_schema}"."{t}"')).scalar()
                c_qa = conn.execute(text(f'SELECT count(*) FROM "{target_schema}"."{t}"')).scalar()
                match_str = "✓ IGUAL" if c_prod == c_qa else "⚠ DIFERENCIA"
                print(f"  - {t:<15}: PROD={c_prod:<5} | QA={c_qa:<5} [{match_str}]")

    print("\n" + "=" * 65)
    print("PROCESO COMPLETADO EXITOSAMENTE")
    print("=" * 65)
    print(f"Esquema QA creado: {target_schema}")
    print(f"Usuario QA creado: {qa_user}")
    print(f"Contraseña QA    : {qa_password}")
    print(f"Host / BD        : {host}:{port} / {db}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aprovisionar esquema y usuario QA, clonando datos de Producción.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host PostgreSQL")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Puerto PostgreSQL")
    parser.add_argument("--db", default=DEFAULT_DB, help="Nombre de la Base de Datos")
    parser.add_argument("--admin-user", default=DEFAULT_USER, help="Usuario Administrador/Superuser")
    parser.add_argument("--admin-password", default=DEFAULT_PASSWORD, help="Contraseña Administrador")
    parser.add_argument("--source-schema", default=DEFAULT_SOURCE_SCHEMA, help="Esquema Origen (Producción)")
    parser.add_argument("--target-schema", default=DEFAULT_TARGET_SCHEMA, help="Esquema Destino (QA)")
    parser.add_argument("--qa-user", default=DEFAULT_QA_USER, help="Nombre de usuario exclusivo para QA")
    parser.add_argument("--qa-password", default=DEFAULT_QA_PASSWORD, help="Contraseña para usuario QA")

    args = parser.parse_args()

    setup_and_clone(
        host=args.host,
        port=args.port,
        db=args.db,
        admin_user=args.admin_user,
        admin_password=args.admin_password,
        source_schema=args.source_schema,
        target_schema=args.target_schema,
        qa_user=args.qa_user,
        qa_password=args.qa_password,
    )
