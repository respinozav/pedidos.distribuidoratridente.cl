#!/usr/bin/env python3
"""
Genera el script SQL para actualizar las 19 imágenes de Desechables con fondo neutro (#F6F7F1)
directamente en la base de datos PostgreSQL (QA o Producción).
"""

import base64
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "scripts" / "assets_estudio"
REF_BAG_PATH = REPO_ROOT / "scripts" / "referencia_fondo.jpg"
SQL_OUTPUT = REPO_ROOT / "scripts" / "actualizar_desechables_neutro.sql"

BAG_CODES = ["760", "761", "762", "763"]
CURATED_CODES = ["764", "765", "766", "767", "768", "769", "770", "771", "772", "773", "774", "775", "776", "777", "778"]

with open(REF_BAG_PATH, "rb") as f:
    bag_b64 = base64.b64encode(f.read()).decode("utf-8")

lines = [
    "-- ====================================================================",
    "-- ACTUALIZACIÓN ATÓMICA DE IMÁGENES DE DESECHABLES - FONDO NEUTRO (#F6F7F1)",
    "-- Distribuidora Tridente",
    "-- ====================================================================",
    "BEGIN;",
    ""
]

# Bolsas 760-763
for cod in BAG_CODES:
    lines.append(f"-- Producto {cod}")
    lines.append(f"UPDATE productos SET imagen_url = '{bag_b64}' WHERE codigo = '{cod}';")
    lines.append("")

# Desechables curados 764-778
for cod in CURATED_CODES:
    asset_file = ASSETS_DIR / f"{cod}_final.jpg"
    with open(asset_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    lines.append(f"-- Producto {cod}")
    lines.append(f"UPDATE productos SET imagen_url = '{b64}' WHERE codigo = '{cod}';")
    lines.append("")

lines.extend([
    "COMMIT;",
    "-- ====================================================================",
    "-- FIN DE ACTUALIZACIÓN",
    "-- ===================================================================="
])

with open(SQL_OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"✓ Archivo SQL generado exitosamente en {SQL_OUTPUT} ({len(lines)} líneas)")
