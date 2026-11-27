#!/usr/bin/env python3
"""
Actualizador de Nombres de Productos: Catálogo Normalizado -> Producción
========================================================================
Distribuidora Tridente

Aplica la normalización de nombres (Title Case con minúsculas en conectores
y unidades de medida, mayúsculas en siglas y corrección de tildes)
al catálogo de Producción.

Modos de uso:
  1. Simulación (Dry-Run):
     python scripts/migrar_nombres_a_prod.py --dry-run

  2. Aplicar vía API de Producción:
     python scripts/migrar_nombres_a_prod.py --apply-api --password TU_PASSWORD

  3. Generar archivo SQL para ejecución directa en PostgreSQL:
     python scripts/migrar_nombres_a_prod.py --generate-sql
"""

import argparse
import json
import logging
import re
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
logger = logging.getLogger("migrar_nombres_prod")

LOWER_WORDS = {'de', 'del', 'con', 'en', 'para', 'por', 'y', 'o', 'a', 'sin', 'al', 'la', 'las', 'el', 'los', 'e'}
UNITS = {'gr', 'grs', 'grs.', 'gr.', 'g', 'kg', 'kg.', 'cc', 'cc.', 'ml', 'ml.', 'lt', 'lts', 'lts.', 'l', 'oz', 'oz.', 'cm', 'cm.', 'mm', 'mm.', 'un', 'un.', 'und', 'und.', 'unid', 'unid.', 'unidades', 'v', 'w', 'mah', 'puffs'}
UPPER_WORDS = {'ocb', 'cbd', 'led', 'xl', 'usb', 'rgb', 'uv', 'hd', 'pvc', 'pet', 'bbq', 'c'}
SPECIAL_BRANDS = {
    'mckay': 'McKay', 'mcdonalds': "McDonald's", 'nestle': 'Nestlé', 'sahne': 'Sahne', 'nuss': 'Nuss',
    'triton': 'Tritón', 'tritón': 'Tritón', 'oxbar': 'Oxbar', 'duracell': 'Duracell', 'amphora': 'Amphora',
    'madison': 'Madison', 'bristol': 'Bristol', 'springfield': 'Springfield', 'lucky': 'Lucky', 'strike': 'Strike',
    'kent': 'Kent', 'pall': 'Pall', 'mall': 'Mall', 'dunhill': 'Dunhill', 'camel': 'Camel', 'marlboro': 'Marlboro',
    'rothmans': 'Rothmans', 'winston': 'Winston',
}
ACCENTS = {
    'arandano': 'arándano', 'arandanos': 'arándanos', 'bateria': 'batería', 'baterias': 'baterías',
    'cafe': 'café', 'limon': 'limón', 'melon': 'melón', 'sandia': 'sandía', 'sandía': 'sandía',
    'maracuya': 'maracuyá', 'platano': 'plátano', 'melocoton': 'melocotón', 'mani': 'maní',
    'diseno': 'diseño', 'plastico': 'plástico', 'sandwich': 'sándwich', 'te': 'té', 'anis': 'anís',
}

def normalize_title(name: str) -> str:
    if not name:
        return name
    name = re.sub(r'\s+', ' ', name.strip())
    words = name.split(' ')
    norm_words = []
    for i, w in enumerate(words):
        m = re.match(r'^([(\[\"-]*)(.*?)([)\]\",.:;-]*)$', w)
        if not m:
            norm_words.append(w)
            continue
        pre, core, post = m.groups()
        if not core:
            norm_words.append(w)
            continue
        core_lower = core.lower()
        if core_lower in ACCENTS:
            core_lower = ACCENTS[core_lower]
        if core_lower in UNITS:
            norm_core = core_lower
        elif core_lower in UPPER_WORDS:
            norm_core = core_lower.upper()
        elif core_lower in SPECIAL_BRANDS:
            norm_core = SPECIAL_BRANDS[core_lower]
        elif core_lower.startswith('mc') and len(core) > 2:
            norm_core = 'Mc' + core[2:].capitalize()
        elif i > 0 and core_lower in LOWER_WORDS and not pre:
            norm_core = core_lower
        else:
            norm_core = core_lower[0].upper() + core_lower[1:]
        norm_words.append(f'{pre}{norm_core}{post}')
    res = ' '.join(norm_words)
    res = re.sub(r'(\w)-(\w)', r'\1 - \2', res)
    return res

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

def main():
    parser = argparse.ArgumentParser(description="Actualizar nombres normalizados en Producción")
    parser.add_argument("--prod-url", default="https://pedidos.distribuidoratridente.cl", help="URL base de Producción")
    parser.add_argument("--admin-email", default="roderick.espinoza@gmail.com", help="Email administrador")
    parser.add_argument("--password", default="12345678", help="Contraseña del administrador")
    parser.add_argument("--generate-sql", action="store_true", help="Generar script SQL atómico")
    parser.add_argument("--sql-output", default="scripts/actualizar_nombres_produccion.sql", help="Ruta archivo SQL")
    parser.add_argument("--apply-api", action="store_true", help="Aplicar directamente vía API REST")
    parser.add_argument("--dry-run", action="store_true", help="Simulación sin modificar datos")
    parser.add_argument("--pause", type=float, default=0.03, help="Pausa entre peticiones en segundos")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("ACTUALIZACIÓN DE NOMBRES EN PRODUCCIÓN: TITLE CASE")
    logger.info("=" * 70)
    logger.info("Destino: %s", args.prod_url)

    logger.info("Descargando catálogo actual de Producción...")
    try:
        prod_items = fetch_catalog(args.prod_url)
    except Exception as e:
        logger.error("Error al obtener catálogo de Producción: %s", e)
        sys.exit(1)

    logger.info("✓ %d productos descargados de Producción.", len(prod_items))

    # Calcular normalizaciones
    plan = []
    for p in prod_items:
        orig = p.get("nombre", "")
        norm = normalize_title(orig)
        if orig != norm:
            plan.append((p, orig, norm))

    logger.info("Productos que serán actualizados: %d de %d (%.1f%%)",
                len(plan), len(prod_items), (len(plan) / len(prod_items) * 100) if prod_items else 0)

    # 1. Generar SQL
    if args.generate_sql or not args.apply_api:
        sql_lines = [
            "-- ==============================================================================\n",
            "-- ACTUALIZACIÓN ATÓMICA DE NOMBRES DE PRODUCTOS (PRODUCCIÓN)\n",
            f"-- Generado: {time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"-- Total cambios: {len(plan)}\n",
            "-- ==============================================================================\n\n",
            "BEGIN;\nSET search_path TO bdtridente, public;\n\n"
        ]
        for p, orig, norm in plan:
            safe_norm = norm.replace("'", "''")
            safe_orig = orig.replace("'", "''")
            sql_lines.append(f"-- [{p['codigo']}] Antes: {safe_orig}\n")
            sql_lines.append(f"UPDATE bdtridente.productos SET nombre = '{safe_norm}' WHERE id = '{p['id']}';\n\n")
        sql_lines.append("COMMIT;\n")

        sql_path = Path(args.sql_output)
        sql_path.parent.mkdir(parents=True, exist_ok=True)
        with open(sql_path, "w", encoding="utf-8") as f:
            f.writelines(sql_lines)
        logger.info("✓ Script SQL generado en: %s", sql_path)

    # 2. Aplicar vía API REST
    if args.apply_api:
        logger.info("Iniciando sesión en Producción como Administrador...")
        token = get_admin_token(args.prod_url, args.admin_email, args.password)
        logger.info("✓ Autenticado exitosamente.")

        exitos = 0
        errores = 0

        for i, (p, orig, norm) in enumerate(plan, 1):
            if args.dry_run:
                logger.info("[%d/%d] [DRY-RUN] [%s] '%s' -> '%s'", i, len(plan), p['codigo'], orig, norm)
                exitos += 1
                continue

            put_url = f"{args.prod_url.rstrip('/')}/api/productos/{p['id']}"
            put_payload = {
                "categoria_id": p.get("categoria_id"),
                "codigo": p.get("codigo"),
                "nombre": norm,
                "precio": float(p.get("precio", 0)),
                "cantidad": p.get("cantidad") or 0,
                "tipo_unidad": p.get("tipo_unidad") or "UNIDAD",
                "imagen_url": p.get("imagen_url"),
                "activo": p.get("activo", True),
                "destacado": p.get("destacado", False),
            }

            req = urllib.request.Request(
                put_url,
                data=json.dumps(put_payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Mozilla/5.0",
                },
                method="PUT",
            )

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    if resp.status in (200, 204):
                        exitos += 1
                        if i % 25 == 0 or i == len(plan):
                            logger.info("[%d/%d] Progreso: %.1f%% completado.", i, len(plan), (i / len(plan) * 100))
                    else:
                        errores += 1
                        logger.error("[%d/%d] Error HTTP %d al actualizar %s", i, len(plan), resp.status, p['codigo'])
            except Exception as e:
                errores += 1
                logger.error("[%d/%d] Excepción al actualizar %s ('%s'): %s", i, len(plan), p['codigo'], orig, e)

            if args.pause > 0:
                time.sleep(args.pause)

        logger.info("=" * 70)
        logger.info("RESUMEN DE ACTUALIZACIÓN EN PRODUCCIÓN")
        logger.info("=" * 70)
        logger.info("Total a procesar : %d", len(plan))
        logger.info("Actualizados OK  : %d", exitos)
        logger.info("Errores          : %d", errores)
        logger.info("=" * 70)

if __name__ == "__main__":
    main()
