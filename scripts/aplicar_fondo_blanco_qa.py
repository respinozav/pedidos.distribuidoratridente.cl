#!/usr/bin/env python3
"""
Estandarización de Fondo Blanco en QA (Excepto DESECHABLES)
============================================================
Distribuidora Tridente - Entorno QA

1. Para la categoría DESECHABLES:
   - Preserva al 100% sus fondos de estudio actuales intactos (cero modificaciones).
2. Para todas las demás categorías (CONFITES, ABARROTES, TABAQUERIA, VAPORIZADORES,
   TABACOS, ATLAS, LATINOS, MARLBORO, BAT):
   - Obtiene la imagen de producto de máxima fidelidad (respaldo original o QA).
   - Aplica canvas 1:1 (900x900 px) con fondo 100% blanco puro (#FFFFFF).
   - Preserva al 100% letras, logos, envoltorios y áreas blancas internas del producto.
   - Comprime iterativamente en JPEG <= 72.000 bytes (< 100 KB Base64).
   - Actualiza directamente en la base de datos de QA vía API autenticada (PUT /api/productos/{id}).
"""

import argparse
import base64
import io
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from scipy import ndimage

# Asegurar backend en sys.path para importar servicios
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend"))

from app.services.image_service import (
    clean_and_square_image,
    clean_background_to_white,
    CATEGORY_CONFIG,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fondo_blanco_qa")

MAX_BINARY_BYTES = 72_000
TARGET_DIM = 900


def get_admin_token(base_url: str) -> str:
    """Inicia sesión como administrador en la API de QA para obtener el token JWT."""
    url = f"{base_url.rstrip('/')}/api/login"
    payload = {"correo": "roderick.espinoza@gmail.com", "password": "replace-with-qa-password"}
    payload["password"] = "12345678"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        token = data.get("access_token")
        if not token:
            raise RuntimeError("No se obtuvo access_token de la respuesta de login.")
        return token


def compress_to_limit(img: Image.Image, max_bytes: int = MAX_BINARY_BYTES) -> tuple[bytes, int]:
    """Comprime iterativamente en JPEG hasta asegurar tamaño <= max_bytes."""
    for quality in range(88, 35, -4):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= max_bytes:
            return raw, quality

    # Si aún supera el límite, reducir escala gradualmente
    current_img = img
    scale = 0.90
    while current_img.width > 500:
        current_img = current_img.resize(
            (int(current_img.width * scale), int(current_img.height * scale)),
            Image.Resampling.LANCZOS
        )
        for quality in range(80, 25, -5):
            buf = io.BytesIO()
            current_img.save(buf, format="JPEG", quality=quality, optimize=True)
            raw = buf.getvalue()
            if len(raw) <= max_bytes:
                return raw, quality
        scale *= 0.90
    return raw, 30


def segment_cyan_to_white(img_rgb: Image.Image) -> Image.Image:
    """
    Para imágenes que ya tenían el fondo de estudio celeste degradado:
    segmenta el producto preservando áreas internas y lo transfiere a fondo blanco puro.
    """
    arr = np.array(img_rgb)
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)

    # Condición de fondo de estudio celeste: b > r + 25, g > r + 20, b > 125
    is_cyan_bg = (b > r + 22) & (g > r + 18) & (b > 120)
    prod_mask = ~is_cyan_bg

    structure = ndimage.generate_binary_structure(2, 2)
    labeled, num = ndimage.label(prod_mask, structure=structure)
    if num > 0:
        sizes = ndimage.sum(prod_mask, labeled, range(1, num + 1))
        max_idx = np.argmax(sizes) + 1
        prod_mask = (labeled == max_idx)
        prod_mask = ndimage.binary_fill_holes(prod_mask)

    white_arr = np.ones_like(arr) * 255
    white_arr[prod_mask] = arr[prod_mask]
    return Image.fromarray(white_arr)


def process_to_white_background(
    raw_bytes: bytes,
    category_name: str,
    target_dim: int = TARGET_DIM,
) -> tuple[bytes, int]:
    """
    Procesa la imagen para garantizar fondo blanco puro 1:1, centrado
    y optimizado para catálogo B2B.
    """
    with Image.open(io.BytesIO(raw_bytes)) as im:
        rgb = im.convert("RGB")

    # Si tiene esquinas celestes, extraer producto primero
    w_c, h_c = rgb.size
    corners = [
        rgb.getpixel((0, 0)),
        rgb.getpixel((w_c - 1, 0)),
        rgb.getpixel((0, h_c - 1)),
        rgb.getpixel((w_c - 1, h_c - 1)),
    ]
    has_cyan_corner = any(
        (c[2] > c[0] + 20) and (c[1] > c[0] + 15) and (c[2] > 120)
        for c in corners
    )

    if has_cyan_corner:
        rgb = segment_cyan_to_white(rgb)

    # Limpiar franjas, recortar, blanquear y centrar en cuadrado 900x900
    processed = clean_and_square_image(
        rgb,
        target_max_dim=target_dim,
        category_name=category_name,
    )

    return compress_to_limit(processed, MAX_BINARY_BYTES)


def main():
    parser = argparse.ArgumentParser(description="Aplica fondo blanco a productos en QA (excepto DESECHABLES)")
    parser.add_argument("--base-url", default="https://pedidos-qa.distribuidoratridente.cl", help="URL base de QA")
    parser.add_argument("--codes", default=None, help="Lista de códigos específicos separados por coma (ej: 526,711)")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de productos a procesar")
    parser.add_argument("--dry-run", action="store_true", help="Procesa sin actualizar en la base de datos")
    parser.add_argument("--pause", type=float, default=0.02, help="Pausa entre actualizaciones en segundos")
    args = parser.parse_args()

    backup_path = repo_root / "backend" / "backup" / "backup_imagenes_productos_20261008_122835.json"
    backup_by_cod = {}
    if backup_path.exists():
        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)
            for item in backup_data:
                c = str(item.get("codigo", "")).strip()
                if c and item.get("imagen_url"):
                    backup_by_cod[c] = item["imagen_url"]
        logger.info("✓ Respaldo original cargado: %d imágenes disponibles", len(backup_by_cod))
    else:
        logger.warning("No se encontró el archivo de respaldo en %s", backup_path)

    logger.info("=" * 70)
    logger.info("ESTANDARIZADOR DE FONDO BLANCO EN QA (EXCEPTO DESECHABLES)")
    logger.info("=" * 70)
    logger.info("Entorno QA   : %s", args.base_url)
    logger.info("Modo Dry-Run : %s", "SI (Sin cambios en BD)" if args.dry_run else "NO (Actualizará BD)")
    logger.info("=" * 70)

    # 1. Autenticación en QA
    token = None
    if not args.dry_run:
        try:
            token = get_admin_token(args.base_url)
            logger.info("✓ Autenticado como Administrador en QA.")
        except Exception as e:
            logger.error("Error al autenticar en QA: %s", e)
            sys.exit(1)

    # 2. Obtener productos de QA
    logger.info("Consultando catálogo de productos en QA...")
    url_prods = f"{args.base_url.rstrip('/')}/api/productos?page=1&page_size=1000"
    req_prods = urllib.request.Request(url_prods, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_prods, timeout=30) as resp:
        catalog = json.loads(resp.read().decode("utf-8"))

    items = catalog.get("items", catalog.get("data", []))
    logger.info("Total productos encontrados en QA: %d", len(items))

    target_codes = set([c.strip() for c in args.codes.split(",")]) if args.codes else None

    to_process = []
    desechables_omitidos = 0
    sin_imagen_omitidos = 0

    for p in items:
        cod = str(p.get("codigo", "")).strip()
        cname = p.get("categoria", {}).get("nombre", "") if isinstance(p.get("categoria"), dict) else ""
        img_url = p.get("imagen_url") or ""

        if target_codes is not None and cod not in target_codes:
            continue

        # Regla mandataria: OMITIR categoría DESECHABLES
        if cname.upper().strip() == "DESECHABLES":
            desechables_omitidos += 1
            continue

        # Si no tiene imagen ni en QA ni en backup, omitir
        if not img_url.strip() and cod not in backup_by_cod:
            sin_imagen_omitidos += 1
            continue

        to_process.append((p, cname))

    if args.limit:
        to_process = to_process[:args.limit]

    logger.info("Productos DESECHABLES preservados intactos: %d", desechables_omitidos)
    logger.info("Productos sin imagen omitidos              : %d", sin_imagen_omitidos)
    logger.info("Productos a cambiar fondo blanco en QA     : %d", len(to_process))
    logger.info("=" * 70)

    exitos = 0
    errores = 0

    for i, (prod, cname) in enumerate(to_process, 1):
        cod = str(prod.get("codigo", "S/C")).strip()
        nombre = prod.get("nombre", "Sin nombre")
        p_id = prod["id"]
        old_img = prod.get("imagen_url") or ""

        try:
            # Obtener fuente de imagen: respaldo limpio original o QA actual
            source_img = backup_by_cod.get(cod) or old_img
            clean_b64 = source_img.strip()
            if "," in clean_b64 and "base64" in clean_b64.split(",")[0]:
                clean_b64 = clean_b64.split(",", 1)[1]
            orig_raw = base64.b64decode(clean_b64)

            # Procesar imagen a fondo blanco puro
            final_bytes, q = process_to_white_background(orig_raw, category_name=cname, target_dim=TARGET_DIM)
            final_b64 = base64.b64encode(final_bytes).decode("utf-8")
            final_kb = len(final_bytes) / 1024.0

            if not args.dry_run and token:
                put_url = f"{args.base_url.rstrip('/')}/api/productos/{p_id}"
                put_payload = {
                    "categoria_id": prod["categoria_id"],
                    "codigo": prod["codigo"],
                    "nombre": prod["nombre"],
                    "precio": float(prod["precio"]),
                    "cantidad": prod.get("cantidad") or 0,
                    "imagen_url": final_b64,
                    "activo": prod.get("activo", True),
                    "afecto": prod.get("afecto", False),
                    "tiene_caja": prod.get("tiene_caja", False),
                    "cantidad_caja": prod.get("cantidad_caja"),
                    "precio_caja": float(prod["precio_caja"]) if prod.get("precio_caja") else None,
                    "notificar_stock": prod.get("notificar_stock", False),
                    "stock_notificacion": prod.get("stock_notificacion"),
                }
                success = False
                for attempt in range(1, 4):
                    try:
                        req_put = urllib.request.Request(
                            put_url,
                            data=json.dumps(put_payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {token}",
                                "User-Agent": "Mozilla/5.0"
                            },
                            method="PUT"
                        )
                        with urllib.request.urlopen(req_put, timeout=25) as resp:
                            if resp.status == 200:
                                logger.info("[%d/%d] ✓ Cod %s (%s - %s) -> Blanco %.1f KB (q=%d)",
                                            i, len(to_process), cod, cname, nombre[:20], final_kb, q)
                                exitos += 1
                                success = True
                                break
                            else:
                                logger.warning("[%d/%d] ✗ Cod %s: HTTP %d (intento %d)", i, len(to_process), cod, resp.status, attempt)
                    except Exception as req_err:
                        if attempt < 3:
                            logger.warning("[%d/%d] Reintentando cod %s por: %s", i, len(to_process), cod, req_err)
                            time.sleep(1.5)
                        else:
                            raise req_err
                if not success:
                    errores += 1
            else:
                logger.info("[%d/%d] ✓ [DRY-RUN] Cod %s (%s - %s) -> Blanco %.1f KB (q=%d)",
                            i, len(to_process), cod, cname, nombre[:20], final_kb, q)
                exitos += 1

            if args.pause > 0:
                time.sleep(args.pause)

        except Exception as e:
            logger.error("[%d/%d] ✗ Error al procesar producto %s: %s", i, len(to_process), cod, e)
            errores += 1

    logger.info("=" * 70)
    logger.info("FINALIZADO: %d Exitosos | %d Errores de %d productos procesados", exitos, errores, len(to_process))
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
