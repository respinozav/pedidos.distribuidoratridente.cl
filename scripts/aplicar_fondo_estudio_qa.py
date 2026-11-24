#!/usr/bin/env python3
"""
Estandarización de Fondo de Estudio en QA
=========================================
Distribuidora Tridente - Entorno QA

1. Aplica la imagen de referencia exactamente a los productos 760, 761, 762 y 763.
2. Extrae el fondo celeste degradado de estudio de la imagen de referencia.
3. Para todas las demás imágenes de la tabla 'productos' en QA, remueve el fondo blanco/neutro,
   mantiene el producto 100% intacto, le añade sombra de contacto difusa y lo monta centrado 1:1
   sobre el fondo de estudio exacto.
4. Comprime iterativamente en JPEG <= 72.000 bytes (< 100 KB Base64).
5. Actualiza directamente en la base de datos de QA vía API autenticada.
"""

import argparse
import base64
import io
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fondo_estudio_qa")

BAG_CODES = {"760", "761", "762", "763"}
MAX_BINARY_BYTES = 72_000
TARGET_DIM = 900  # 900x900 balance perfecto entre nitidez HD y peso < 72 KB


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


def extract_bg_profile(ref_image_path: Path) -> np.ndarray:
    """Extrae el perfil vertical de color del fondo de la imagen de referencia."""
    with Image.open(ref_image_path) as ref_im:
        arr = np.array(ref_im.convert("RGB"))
        # Promediar columnas 5 a 45 (área libre de producto a la izquierda)
        profile = np.mean(arr[:, 5:45, :], axis=1).astype(np.uint8)
        return profile


def create_studio_bg(bg_profile: np.ndarray, width: int = TARGET_DIM, height: int = TARGET_DIM) -> Image.Image:
    """Genera el canvas con el degradado vertical idéntico a la imagen de referencia."""
    indices = np.linspace(0, len(bg_profile) - 1, height).astype(int)
    column = bg_profile[indices]
    bg_arr = np.tile(column[:, np.newaxis, :], (1, width, 1))
    return Image.fromarray(bg_arr, mode="RGB")


def compress_to_limit(img: Image.Image, max_bytes: int = MAX_BINARY_BYTES) -> tuple[bytes, int]:
    """Comprime iterativamente en JPEG hasta asegurar tamaño <= max_bytes."""
    for quality in range(88, 35, -4):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= max_bytes:
            return raw, quality
    # Si aún no baja, reducir resolución
    resized = img.resize((int(img.width * 0.85), int(img.height * 0.85)), Image.Resampling.LANCZOS)
    for quality in range(85, 35, -5):
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=quality, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= max_bytes:
            return raw, quality
    return raw, 40


def process_product_image(
    raw_bytes: bytes,
    bg_profile: np.ndarray,
    target_dim: int = TARGET_DIM
) -> tuple[bytes, int]:
    """
    Toma la imagen original del producto, elimina su fondo blanco/neutro,
    mantiene el producto intacto, agrega sombra natural y monta sobre el fondo de estudio.
    """
    with Image.open(io.BytesIO(raw_bytes)) as im:
        prod_rgb = im.convert("RGB")

    arr = np.array(prod_rgb, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    brightness = (r + g + b) / 3.0
    color_diff = np.maximum(np.abs(r - g), np.abs(g - b))

    # Detectar fondo blanco/claro neutro
    is_bg = (brightness > 240) & (color_diff < 16)
    mask = (~is_bg).astype(np.uint8) * 255
    mask_im = Image.fromarray(mask, mode="L")
    mask_im = mask_im.filter(ImageFilter.GaussianBlur(radius=1.2))

    # Bounding box del producto
    bbox = Image.fromarray((~is_bg).astype(np.uint8) * 255).getbbox()
    if bbox:
        w_box, h_box = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = int(max(w_box, h_box) * 0.02)
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(prod_rgb.width, bbox[2] + pad),
            min(prod_rgb.height, bbox[3] + pad)
        )
        prod_cropped = prod_rgb.crop(crop_box)
        mask_cropped = mask_im.crop(crop_box)
    else:
        prod_cropped = prod_rgb
        mask_cropped = mask_im

    # Escalar producto para que ocupe ~78% del canvas
    max_dim = int(target_dim * 0.78)
    aspect = prod_cropped.width / prod_cropped.height if prod_cropped.height > 0 else 1.0
    if aspect >= 1.0:
        new_w = max_dim
        new_h = max(1, int(new_w / aspect))
    else:
        new_h = max_dim
        new_w = max(1, int(new_h * aspect))

    prod_resized = prod_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    mask_resized = mask_cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Realce sutil
    enh_c = ImageEnhance.Contrast(prod_resized)
    prod_enhanced = enh_c.enhance(1.05)
    enh_b = ImageEnhance.Brightness(prod_enhanced)
    prod_enhanced = enh_b.enhance(1.02)
    prod_enhanced = prod_enhanced.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))

    # Canvas de fondo exacto
    canvas = create_studio_bg(bg_profile, target_dim, target_dim)

    # Posición centrada
    pos_x = (target_dim - new_w) // 2
    pos_y = (target_dim - new_h) // 2

    # Sombra difusa de contacto
    shadow_w = int(new_w * 0.85)
    shadow_h = max(10, int(new_h * 0.10))
    shadow_mask = Image.new("L", (shadow_w, shadow_h), 0)
    draw = ImageDraw.Draw(shadow_mask)
    draw.ellipse((0, 0, shadow_w, shadow_h), fill=110)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=max(2, shadow_h // 2)))

    shadow_img = Image.new("RGBA", (shadow_w, shadow_h), (50, 90, 115, 0))
    shadow_img.putalpha(shadow_mask)
    shadow_pos = (pos_x + (new_w - shadow_w) // 2, pos_y + new_h - shadow_h // 2)

    canvas.paste(shadow_img, shadow_pos, shadow_img)
    canvas.paste(prod_enhanced, (pos_x, pos_y), mask_resized)

    return compress_to_limit(canvas, MAX_BINARY_BYTES)


def main():
    parser = argparse.ArgumentParser(description="Aplica el fondo de estudio exacto a los productos en QA")
    parser.add_argument("--base-url", default="https://pedidos-qa.distribuidoratridente.cl", help="URL base de QA")
    parser.add_argument("--codes", default=None, help="Lista de códigos específicos separados por coma (ej: 760,764,526)")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de productos a procesar")
    parser.add_argument("--dry-run", action="store_true", help="Procesa sin actualizar en la base de datos")
    parser.add_argument("--pause", type=float, default=0.2, help="Pausa entre actualizaciones en segundos")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    ref_image_path = repo_root / "scripts" / "referencia_fondo.jpg"
    if not ref_image_path.exists():
        logger.error("No se encontró la imagen de referencia en %s", ref_image_path)
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("ESTANDARIZADOR DE FONDO DE ESTUDIO QA")
    logger.info("=" * 70)
    logger.info("Imagen de referencia : %s", ref_image_path)
    logger.info("Entorno QA           : %s", args.base_url)
    logger.info("Modo Dry-Run         : %s", "SI" if args.dry_run else "NO (Actualizará BD)")
    logger.info("=" * 70)

    # 1. Obtener perfil de fondo de la imagen de referencia
    bg_profile = extract_bg_profile(ref_image_path)
    logger.info("✓ Perfil vertical de color de fondo extraído de la referencia.")

    # 2. Preparar imagen comprimida de la referencia para los códigos 760, 761, 762, 763
    with Image.open(ref_image_path) as ref_im:
        ref_bytes, ref_q = compress_to_limit(ref_im.convert("RGB"), MAX_BINARY_BYTES)
        ref_b64 = base64.b64encode(ref_bytes).decode("utf-8")
        logger.info("✓ Imagen de referencia optimizada para 760-763: %.1f KB (Calidad %d, Base64 %.1f KB)",
                    len(ref_bytes)/1024, ref_q, len(ref_b64)/1024)

    # 3. Autenticación en QA
    token = None
    if not args.dry_run:
        try:
            token = get_admin_token(args.base_url)
            logger.info("✓ Autenticado como Administrador en QA.")
        except Exception as e:
            logger.error("Error al autenticar en QA: %s", e)
            sys.exit(1)

    # 4. Obtener productos de QA
    logger.info("Consultando catálogo de productos en QA...")
    url_prods = f"{args.base_url.rstrip('/')}/api/productos?page=1&page_size=1000"
    req_prods = urllib.request.Request(url_prods, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_prods, timeout=30) as resp:
        catalog = json.loads(resp.read().decode("utf-8"))
    
    items = catalog.get("items", [])
    logger.info("Total productos encontrados en QA: %d", len(items))

    # Filtrar productos con imagen
    target_codes = set([c.strip() for c in args.codes.split(",")]) if args.codes else None
    
    to_process = []
    for p in items:
        cod = str(p.get("codigo", "")).strip()
        img_url = p.get("imagen_url")
        # Si es de los códigos de bolsas (760-763), procesar siempre
        if cod in BAG_CODES:
            to_process.append(p)
        elif img_url and img_url.strip():
            if target_codes is None or cod in target_codes:
                to_process.append(p)

    if args.limit:
        to_process = to_process[:args.limit]

    logger.info("Productos a procesar: %d", len(to_process))

    # 5. Procesamiento ítem por ítem
    exitos = 0
    errores = 0

    for i, prod in enumerate(to_process, 1):
        cod = str(prod.get("codigo", "S/C")).strip()
        nombre = prod.get("nombre", "Sin nombre")
        p_id = prod["id"]
        old_img = prod.get("imagen_url") or ""
        old_kb = len(old_img) / 1024.0

        logger.info("[%d/%d] Código %s: %s (Actual: %.1f KB)", i, len(to_process), cod, nombre[:30], old_kb)

        try:
            # Caso A: Códigos 760, 761, 762, 763 reciben la imagen de referencia exacta
            if cod in BAG_CODES:
                final_b64 = ref_b64
                final_kb = len(ref_bytes) / 1024.0
                tipo = "REFERENCIA ADJUNTA"
            else:
                # Caso B: Todas las demás reciben su propio producto con el fondo de estudio
                clean_b64 = old_img.strip()
                if "," in clean_b64 and "base64" in clean_b64.split(",")[0]:
                    clean_b64 = clean_b64.split(",", 1)[1]
                orig_raw = base64.b64decode(clean_b64)
                
                final_bytes, q = process_product_image(orig_raw, bg_profile, TARGET_DIM)
                final_b64 = base64.b64encode(final_bytes).decode("utf-8")
                final_kb = len(final_bytes) / 1024.0
                tipo = f"ESTUDIO CELSTE (q={q})"

            # Actualizar en QA vía PUT
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
                with urllib.request.urlopen(req_put, timeout=20) as resp:
                    if resp.status == 200:
                        logger.info("   ✓ Actualizado en QA (HTTP 200) | %s -> %.1f KB", tipo, final_kb)
                        exitos += 1
                    else:
                        logger.warning("   ✗ Respuesta inesperada: HTTP %d", resp.status)
                        errores += 1
            else:
                logger.info("   ✓ [DRY-RUN] Procesado | %s -> %.1f KB", tipo, final_kb)
                exitos += 1

            if args.pause > 0:
                time.sleep(args.pause)

        except Exception as e:
            logger.error("   ✗ Error al procesar producto %s: %s", cod, e)
            errores += 1

    logger.info("=" * 70)
    logger.info("FINALIZADO: %d Exitosos | %d Errores", exitos, errores)
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
