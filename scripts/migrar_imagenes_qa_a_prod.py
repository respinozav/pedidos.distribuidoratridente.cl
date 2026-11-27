#!/usr/bin/env python3
"""
Migrador de Imágenes de Productos: QA -> Producción
===================================================
Distribuidora Tridente

Lee las 424 imágenes estandarizadas y auditadas al 100% en QA
y las replica exactamente en Producción.

Modos de uso:
  1. Generar archivo SQL atómico para ejecutar directo en PostgreSQL:
     python scripts/migrar_imagenes_qa_a_prod.py --generate-sql

  2. Actualizar vía API REST de Producción (con autenticación admin):
     python scripts/migrar_imagenes_qa_a_prod.py --apply-api --password TU_PASSWORD

  3. Modo Simulación (Dry-Run):
     python scripts/migrar_imagenes_qa_a_prod.py --dry-run
"""

import argparse
import io
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("migrar_qa_prod")


def get_admin_token(base_url: str, email: str, password: str) -> str:
    url = f"{base_url.rstrip('/')}/api/login"
    payload = {"correo": email, "password": password}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"No se obtuvo access_token de {base_url}")
        return token


def fetch_catalog(base_url: str) -> list[dict]:
    url = f"{base_url.rstrip('/')}/api/productos?page=1&page_size=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("items", data.get("data", []))


def escape_sql_string(s: str) -> str:
    """Escapa comillas simples para sentencias SQL seguras."""
    return s.replace("'", "''")


def main():
    parser = argparse.ArgumentParser(description="Migración de imágenes de productos de QA a Producción")
    parser.add_argument("--qa-url", default="https://pedidos-qa.distribuidoratridente.cl", help="URL base de QA")
    parser.add_argument("--prod-url", default="https://pedidos.distribuidoratridente.cl", help="URL base de Producción")
    parser.add_argument("--admin-email", default="roderick.espinoza@gmail.com", help="Email del administrador")
    parser.add_argument("--password", default=None, help="Contraseña del administrador para Producción")
    parser.add_argument("--generate-sql", action="store_true", help="Genera script SQL atómico con las sentencias UPDATE")
    parser.add_argument("--sql-output", default="scripts/actualizar_imagenes_produccion.sql", help="Ruta del script SQL")
    parser.add_argument("--apply-api", action="store_true", help="Actualiza Producción vía peticiones PUT a la API")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de productos a procesar")
    parser.add_argument("--codes", default=None, help="Lista de códigos específicos separados por coma (ej: 760,764,526)")
    parser.add_argument("--dry-run", action="store_true", help="Verifica correspondencia sin modificar datos")
    parser.add_argument("--pause", type=float, default=0.05, help="Pausa entre peticiones en segundos")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("MIGRACIÓN DE IMÁGENES ESTANDARIZADAS: QA -> PRODUCCIÓN")
    logger.info("=" * 70)
    logger.info("Origen (QA)         : %s", args.qa_url)
    logger.info("Destino (Producción): %s", args.prod_url)
    logger.info("=" * 70)

    # 1. Obtener catálogo con imágenes limpias de QA
    logger.info("Descargando catálogo con imágenes estandarizadas desde QA...")
    try:
        qa_items = fetch_catalog(args.qa_url)
    except Exception as e:
        logger.error("Error al consultar catálogo de QA: %s", e)
        sys.exit(1)

    qa_images = {}
    for p in qa_items:
        cod = str(p.get("codigo", "")).strip()
        img = p.get("imagen_url", "")
        if cod and img and len(img.strip()) > 100:
            qa_images[cod] = {
                "nombre": p.get("nombre", ""),
                "imagen_url": img.strip(),
                "bytes": len(img.strip())
            }

    if args.codes:
        target_set = set(c.strip() for c in args.codes.split(","))
        qa_images = {k: v for k, v in qa_images.items() if k in target_set}
        logger.info("Filtrado por códigos: %d productos seleccionados.", len(qa_images))

    if args.limit:
        qa_images = dict(list(qa_images.items())[:args.limit])
        logger.info("Filtrado por límite: %d productos seleccionados.", len(qa_images))

    logger.info("✓ %d productos con imágenes estandarizadas a procesar.", len(qa_images))

    # 2. Generación de Script SQL Atómico si fue solicitado
    if args.generate_sql or not args.apply_api:
        sql_path = Path(args.sql_output)
        logger.info("Generando script SQL atómico en %s...", sql_path)
        sql_lines = [
            "-- ==============================================================================\n",
            "-- MIGRACIÓN ATÓMICA DE IMÁGENES DE PRODUCTOS (QA -> PRODUCCIÓN)\n",
            f"-- Generado automáticamente: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"-- Total de productos con imagen: {len(qa_images)}\n",
            "-- ==============================================================================\n\n",
            "BEGIN;\n\n",
            "-- Configurar esquema de Producción\n",
            "SET search_path TO bdtridente, public;\n\n"
        ]

        for cod, data in sorted(qa_images.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99999):
            img_escaped = escape_sql_string(data["imagen_url"])
            sql_lines.append(f"-- [{cod}] {data['nombre']}\n")
            sql_lines.append(f"UPDATE bdtridente.productos SET imagen_url = '{img_escaped}' WHERE codigo = '{cod}';\n\n")

        sql_lines.append("COMMIT;\n")

        sql_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sql_path, "w", encoding="utf-8") as f:
            f.writelines(sql_lines)

        logger.info("✓ Script SQL generado exitosamente: %s (%.1f MB)",
                    sql_path, sql_path.stat().st_size / (1024 * 1024))
        logger.info("  Para ejecutarlo directo en PostgreSQL de Producción:")
        logger.info("  psql -h <AWS_HOST_BD> -U <AWS_USER_BD> -d postgres -f %s", sql_path)

    # 3. Aplicación vía API REST
    if args.apply_api:
        if not args.password:
            logger.error("Debe proporcionar --password para autenticarse en la API de Producción.")
            sys.exit(1)

        logger.info("Autenticando en Producción...")
        try:
            prod_token = get_admin_token(args.prod_url, args.admin_email, args.password)
            logger.info("✓ Autenticado en Producción como Administrador.")
        except Exception as e:
            logger.error("Error al autenticar en Producción: %s", e)
            sys.exit(1)

        logger.info("Consultando catálogo actual de Producción...")
        try:
            prod_items = fetch_catalog(args.prod_url)
        except Exception as e:
            logger.error("Error al obtener catálogo de Producción: %s", e)
            sys.exit(1)

        prod_by_code = {str(p.get("codigo", "")).strip(): p for p in prod_items}
        logger.info("Total productos en Producción: %d", len(prod_by_code))

        exitos = 0
        omitidos = 0
        errores = 0

        for i, (cod, qa_data) in enumerate(sorted(qa_images.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 99999), 1):
            if cod not in prod_by_code:
                logger.warning("[%d/%d] Código %s no existe en Producción. Omitido.", i, len(qa_images), cod)
                omitidos += 1
                continue

            p = prod_by_code[cod]
            p_id = p["id"]
            nombre = p.get("nombre", "")

            if args.dry_run:
                logger.info("[%d/%d] [DRY-RUN] Código %s (%s): Listo para migrar (%.1f KB)",
                            i, len(qa_images), cod, nombre[:22], len(qa_data["imagen_url"]) / 1024)
                exitos += 1
                continue

            put_url = f"{args.prod_url.rstrip('/')}/api/productos/{p_id}"
            put_payload = {
                "categoria_id": p["categoria_id"],
                "codigo": p["codigo"],
                "nombre": p["nombre"],
                "precio": float(p["precio"]),
                "cantidad": p.get("cantidad") or 0,
                "imagen_url": qa_data["imagen_url"],
                "activo": p.get("activo", True),
                "afecto": p.get("afecto", False),
                "tiene_caja": p.get("tiene_caja", False),
                "cantidad_caja": p.get("cantidad_caja"),
                "precio_caja": float(p["precio_caja"]) if p.get("precio_caja") else None,
                "notificar_stock": p.get("notificar_stock", False),
                "stock_notificacion": p.get("stock_notificacion"),
            }

            success = False
            for attempt in range(1, 4):
                try:
                    req_put = urllib.request.Request(
                        put_url,
                        data=json.dumps(put_payload).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {prod_token}",
                            "User-Agent": "Mozilla/5.0"
                        },
                        method="PUT"
                    )
                    with urllib.request.urlopen(req_put, timeout=25) as resp:
                        if resp.status == 200:
                            logger.info("[%d/%d] ✓ Cod %s (%s): Migrado a Prod (HTTP 200)",
                                        i, len(qa_images), cod, nombre[:22])
                            exitos += 1
                            success = True
                            break
                        else:
                            logger.warning("[%d/%d] ✗ Cod %s: HTTP %d (intento %d)", i, len(qa_images), cod, resp.status, attempt)
                except Exception as e:
                    if attempt < 3:
                        logger.warning("[%d/%d] Reintentando cod %s por error transitorio: %s", i, len(qa_images), cod, e)
                        time.sleep(2.0)
                    else:
                        logger.error("[%d/%d] ✗ Error al migrar producto %s tras 3 intentos: %s", i, len(qa_images), cod, e)
            if not success:
                errores += 1

            if args.pause > 0:
                time.sleep(args.pause)

        logger.info("=" * 70)
        logger.info("FINALIZADO: %d Exitosos | %d Omitidos | %d Errores", exitos, errores, omitidos)
        logger.info("=" * 70)


if __name__ == "__main__":
    main()
