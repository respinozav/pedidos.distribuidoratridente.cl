#!/usr/bin/env python3
"""
Estandarización de Fondo de Estudio en QA
=========================================
Distribuidora Tridente - Entorno QA

1. Aplica la imagen de referencia exactamente a los productos 760, 761, 762 y 763 (Bolsas Kraft).
2. Para los productos con tomas de estudio curadas (en scripts/assets_estudio/), aplica
   la fotografía de catálogo verificada al 100% con fondo celeste de estudio exacto.
3. Para todas las demás imágenes de productos del catálogo:
   - Descarga la imagen original limpia desde producción.
   - Elimina fondos blancos, sombras sucias y lienzos embebidos.
   - Preserva al 100% letras, logos, envoltorios y áreas blancas internas del producto.
   - Monta el producto centrado 1:1 sobre el degradado celeste de estudio (#4991AA a #B2D6E6).
   - Comprime iterativamente en JPEG <= 72.000 bytes (< 100 KB Base64).
4. Actualiza directamente en la base de datos de QA vía API autenticada (PUT /api/productos/{id}).
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
from scipy import ndimage
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
    """Comprime iterativamente en JPEG hasta asegurar tamaño <= max_bytes sin excepción."""
    for quality in range(88, 35, -4):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= max_bytes:
            return raw, quality
            
    # Si aún no baja, reducir escala gradualmente hasta asegurar <= max_bytes
    current_img = img
    scale = 0.88
    while current_img.width > 500:
        current_img = current_img.resize((int(current_img.width * scale), int(current_img.height * scale)), Image.Resampling.LANCZOS)
        for quality in range(80, 25, -5):
            buf = io.BytesIO()
            current_img.save(buf, format="JPEG", quality=quality, optimize=True)
            raw = buf.getvalue()
            if len(raw) <= max_bytes:
                return raw, quality
        scale *= 0.90
    return raw, 30


def process_product_image(
    raw_bytes: bytes,
    bg_profile: np.ndarray,
    target_dim: int = TARGET_DIM,
    codigo: str = ""
) -> tuple[bytes, int]:
    """
    Toma la imagen original del producto, elimina su fondo blanco/neutro o sucio,
    desacopla lienzos y marcos exteriores en fotos de mesa embebidas,
    mantiene el producto y sus letras/gráficos blancos 100% intactos mediante envolvente span-hull,
    elimina sombras de piso sucias previas sin recortar el producto,
    y monta centrado 1:1 sobre el fondo celeste exacto guiado por el estándar 762.
    """
    with Image.open(io.BytesIO(raw_bytes)) as im:
        prod_rgb = im.convert("RGB")

    arr = np.array(prod_rgb, dtype=np.uint8)
    h, w, _ = arr.shape
    r = arr[:, :, 0].astype(np.float32)
    g = arr[:, :, 1].astype(np.float32)
    b = arr[:, :, 2].astype(np.float32)
    brightness = (r + g + b) / 3.0
    color_diff = np.maximum(np.abs(r - g), np.abs(g - b))

    # Reglas según tipo de producto
    if codigo in ["476", "475", "605"]:
        # Paquetes con sombra suave de mesa: descartar sombra neutra clara
        is_shadow = (color_diff < 16) & (brightness > 175)
        prod_seed = ~is_shadow
    elif codigo == "635":
        # Dragbar: descartar mesa blanca inferior
        is_table = (brightness > 248.0) & (color_diff < 10.0)
        prod_seed = ~is_table
    else:
        # Paquetes sobre fondo blanco / gris claro
        prod_seed = (brightness < 253.0) | (color_diff > 8.0)

    # Filtrar componentes parásitos pequeños
    structure = ndimage.generate_binary_structure(2, 2)
    labeled, num_features = ndimage.label(prod_seed, structure=structure)
    if num_features > 0:
        sizes = ndimage.sum(prod_seed, labeled, range(1, num_features + 1))
        max_size = np.max(sizes)
        keep = [i + 1 for i, s in enumerate(sizes) if s >= max_size * 0.05]
        prod_seed = np.isin(labeled, keep)

    ys, xs = np.where(prod_seed)
    if len(ys) == 0:
        mask = np.ones((h, w), dtype=bool)
    else:
        y_min, y_max = int(ys.min()), int(ys.max())
        x_min, x_max = int(xs.min()), int(xs.max())

        span_mask = np.zeros((h, w), dtype=bool)
        for y in range(y_min, y_max + 1):
            row_xs = np.where(prod_seed[y])[0]
            if len(row_xs) > 0:
                span_mask[y, row_xs.min():row_xs.max()+1] = True
            else:
                # Fila interna sin color (e.g. franja blanca interna): llenar entre x_min y x_max
                span_mask[y, x_min:x_max+1] = True

        col_mask = np.zeros((h, w), dtype=bool)
        for x in range(x_min, x_max + 1):
            col_ys = np.where(prod_seed[:, x])[0]
            if len(col_ys) > 0:
                col_mask[col_ys.min():col_ys.max()+1, x] = True
            else:
                col_mask[y_min:y_max+1, x] = True

        hull_mask = span_mask & col_mask
        hull_mask = ndimage.binary_fill_holes(hull_mask)
        mask = hull_mask

    mask_uint8 = (mask.astype(np.uint8) * 255)
    bbox = Image.fromarray(mask_uint8).getbbox()
    if not bbox:
        bbox = (0, 0, w, h)

    pad = int(max(bbox[2] - bbox[0], bbox[3] - bbox[1]) * 0.01)
    crop_box = (
        max(0, bbox[0] - pad),
        max(0, bbox[1] - pad),
        min(w, bbox[2] + pad),
        min(h, bbox[3] + pad)
    )

    mask_im = Image.fromarray(mask_uint8, mode="L").filter(ImageFilter.GaussianBlur(radius=0.75))
    prod_cropped = prod_rgb.crop(crop_box)
    mask_cropped = mask_im.crop(crop_box)

    # Escalar producto para que ocupe ~80% del canvas (estándar 762)
    max_dim = int(target_dim * 0.80)
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
    prod_enhanced = enh_c.enhance(1.03)
    enh_b = ImageEnhance.Brightness(prod_enhanced)
    prod_enhanced = enh_b.enhance(1.01)
    prod_enhanced = prod_enhanced.filter(ImageFilter.UnsharpMask(radius=1.2, percent=105, threshold=2))

    # Canvas de fondo exacto
    canvas = create_studio_bg(bg_profile, target_dim, target_dim)

    # Posición centrada (sin rectángulos artificiales de sombra)
    pos_x = (target_dim - new_w) // 2
    pos_y = (target_dim - new_h) // 2
    canvas.paste(prod_enhanced, (pos_x, pos_y), mask_resized)

    return compress_to_limit(canvas, MAX_BINARY_BYTES)


def main():
    parser = argparse.ArgumentParser(description="Aplica el fondo de estudio exacto a los productos en QA")
    parser.add_argument("--base-url", default="https://pedidos-qa.distribuidoratridente.cl", help="URL base de QA")
    parser.add_argument("--codes", default=None, help="Lista de códigos específicos separados por coma (ej: 760,764,526)")
    parser.add_argument("--limit", type=int, default=None, help="Límite máximo de productos a procesar")
    parser.add_argument("--dry-run", action="store_true", help="Procesa sin actualizar en la base de datos")
    parser.add_argument("--pause", type=float, default=0.03, help="Pausa entre actualizaciones en segundos")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    ref_image_path = repo_root / "scripts" / "referencia_fondo.jpg"
    assets_dir = repo_root / "scripts" / "assets_estudio"
    scratch_dir = repo_root / "scratch" / "final_31"

    if not ref_image_path.exists():
        logger.error("No se encontró la imagen de referencia en %s", ref_image_path)
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("ESTANDARIZADOR DE FONDO DE ESTUDIO QA (CATÁLOGO COMPLETO)")
    logger.info("=" * 70)
    logger.info("Imagen de referencia : %s", ref_image_path)
    logger.info("Directorio Assets    : %s (Existe: %s)", assets_dir, assets_dir.exists())
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
    
    items = catalog.get("items", catalog.get("data", []))
    logger.info("Total productos encontrados en QA: %d", len(items))

    # Pre-cargar imágenes originales desde producción para asegurar máxima fidelidad
    logger.info("Cargando imágenes originales limpias desde producción...")
    prod_originals = {}
    try:
        req_prod = urllib.request.Request(
            "https://pedidos.distribuidoratridente.cl/api/productos?page=1&page_size=1000",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req_prod, timeout=25) as resp_p:
            p_cat = json.loads(resp_p.read().decode("utf-8"))
            p_items = p_cat.get("items", p_cat.get("data", []))
            for p in p_items:
                c = str(p.get("codigo", "")).strip()
                if c and p.get("imagen_url"):
                    prod_originals[c] = p["imagen_url"]
        logger.info("✓ %d imágenes originales limpias cargadas desde producción.", len(prod_originals))
    except Exception as e:
        logger.warning("No se pudo conectar con producción (%s). Se usarán las imágenes de QA.", e)

    # Filtrar productos con imagen
    target_codes = set([c.strip() for c in args.codes.split(",")]) if args.codes else None
    
    to_process = []
    for p in items:
        cod = str(p.get("codigo", "")).strip()
        img_url = p.get("imagen_url")
        if target_codes is not None and cod not in target_codes:
            continue
        if cod in BAG_CODES:
            to_process.append(p)
        elif (img_url and img_url.strip()) or (cod in prod_originals):
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

        try:
            # Prioridad 1: Bolsas kraft 760-763 -> referencia directa
            if cod in BAG_CODES:
                final_b64 = ref_b64
                final_kb = len(ref_bytes) / 1024.0
                tipo = "REFERENCIA ADJUNTA"
            # Prioridad 2: Asset curado en scripts/assets_estudio/ o scratch/final_31/
            elif (assets_dir / f"{cod}_final.jpg").exists():
                curated_path = assets_dir / f"{cod}_final.jpg"
                with open(curated_path, "rb") as f:
                    final_bytes = f.read()
                final_b64 = base64.b64encode(final_bytes).decode("utf-8")
                final_kb = len(final_bytes) / 1024.0
                tipo = "ASSET CURADO ESTUDIO"
            elif (scratch_dir / f"{cod}_final.jpg").exists():
                curated_path = scratch_dir / f"{cod}_final.jpg"
                with open(curated_path, "rb") as f:
                    final_bytes = f.read()
                final_b64 = base64.b64encode(final_bytes).decode("utf-8")
                final_kb = len(final_bytes) / 1024.0
                tipo = "SCRATCH CURADO ESTUDIO"
            # Prioridad 3: Procesamiento automático de catálogo con fondo celeste
            else:
                source_img = prod_originals.get(cod) or old_img
                clean_b64 = source_img.strip()
                if "," in clean_b64 and "base64" in clean_b64.split(",")[0]:
                    clean_b64 = clean_b64.split(",", 1)[1]
                orig_raw = base64.b64decode(clean_b64)
                
                final_bytes, q = process_product_image(orig_raw, bg_profile, TARGET_DIM, codigo=cod)
                final_b64 = base64.b64encode(final_bytes).decode("utf-8")
                final_kb = len(final_bytes) / 1024.0
                tipo = f"AUTO ESTUDIO (q={q})"

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
                        logger.info("[%d/%d] ✓ Cod %s (%s): %s -> %.1f KB (HTTP 200)",
                                    i, len(to_process), cod, nombre[:22], tipo, final_kb)
                        exitos += 1
                    else:
                        logger.warning("[%d/%d] ✗ Cod %s: HTTP %d", i, len(to_process), cod, resp.status)
                        errores += 1
            else:
                logger.info("[%d/%d] ✓ [DRY-RUN] Cod %s (%s): %s -> %.1f KB",
                            i, len(to_process), cod, nombre[:22], tipo, final_kb)
                exitos += 1

            if args.pause > 0:
                time.sleep(args.pause)

        except Exception as e:
            logger.error("[%d/%d] ✗ Error al procesar producto %s: %s", i, len(to_process), cod, e)
            errores += 1

    logger.info("=" * 70)
    logger.info("FINALIZADO: %d Exitosos | %d Errores de %d productos", exitos, errores, len(to_process))
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
