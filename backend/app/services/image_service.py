"""Servicio centralizado para optimizar y normalizar imágenes de productos.

Funcionalidades:
1. Detección y recorte de franjas/pestañas laterales izquierdas (logos o banners verticales BAT).
2. Detección y recorte de cintas/listones laterales derechos (logos verticales como en tiras de confites).
3. Detección y recorte de etiquetas/insignias superiores flotantes (como 'ALKA MENTOL 12' o 'ALFAJOR PREMIUM 12').
4. Autocrop robusto contra ruido jpeg para centrar el producto real.
5. Normalización a formato cuadrado 1:1 con fondo blanco limpio.
6. Optimización de compresión (JPEG calidad 85%) para máxima velocidad de carga.
"""

from io import BytesIO
import base64
from typing import Tuple, Optional
from PIL import Image, ImageChops

try:
    import numpy as np
except ImportError:
    np = None


def detect_lateral_strip_divider(img: Image.Image) -> Optional[int]:
    """
    Detecta si la imagen contiene una franja o pestaña lateral izquierda
    (típica en catálogos de cigarrillos BAT).
    Retorna la coordenada X donde cortar, o None si no hay franja lateral.
    """
    if np is None:
        return None

    w, h = img.size
    if w < 150 or h < 150:
        return None
    if (w / h) > 1.25:
        return None

    rgb_img = img.convert("RGB")
    arr = np.array(rgb_img)

    cand_min = int(w * 0.15)
    cand_max = int(w * 0.45)

    # 1. Separador por franja blanca
    is_white = np.all(arr > 240, axis=2)
    col_white_frac = np.mean(is_white, axis=0)
    white_cols = [x for x in range(cand_min, cand_max) if col_white_frac[x] > 0.95]
    if len(white_cols) >= 3:
        left_strip_non_white = np.mean(~is_white[:, :white_cols[0]])
        if left_strip_non_white > 0.20:
            return max(white_cols) + 1

    # 2. Separador por línea negra/oscura sólida vertical
    is_black = np.all(arr < 25, axis=2)
    col_black_frac = np.mean(is_black, axis=0)
    black_cols = [x for x in range(cand_min, cand_max) if col_black_frac[x] > 0.85]
    if len(black_cols) >= 2:
        left_has_content = np.mean(arr[:, :black_cols[0]] > 30) > 0.40
        if left_has_content:
            return max(black_cols) + 1

    return None


def detect_top_floating_badge(img: Image.Image) -> Optional[int]:
    """
    Detecta etiquetas o recuadros flotantes en la parte superior
    (ej: 'ALKA MENTOL 12' o 'ALFAJOR PREMIUM 12' separados por un espacio en blanco del producto).
    Retorna la coordenada Y desde donde recortar hacia abajo.
    """
    if np is None:
        return None

    w, h = img.size
    if h < 120:
        return None

    rgb_img = img.convert("RGB")
    arr = np.array(rgb_img)
    is_white = np.all(arr > 240, axis=2)
    row_white = np.mean(is_white, axis=1)

    for y in range(int(h * 0.05), int(h * 0.55)):
        if row_white[y] > 0.95:
            above_active = np.where(row_white[:y] < 0.95)[0]
            if len(above_active) >= 12:
                badge_h = above_active[-1] - above_active[0] + 1
                if badge_h <= h * 0.22:
                    badge_cols = np.where(np.mean(is_white[above_active[0]:above_active[-1]+1], axis=0) < 0.98)[0]
                    if len(badge_cols):
                        badge_w = badge_cols[-1] - badge_cols[0] + 1
                        if badge_w / badge_h >= 2.5: # Insignia horizontal apaisada
                            below_active = np.where(row_white[y:] < 0.95)[0]
                            if len(below_active) >= 30: # Hay producto real debajo
                                return y
    return None


def detect_right_vertical_ribbon(img: Image.Image) -> Optional[int]:
    """
    Detecta tiras/listones verticales flotantes en el lateral derecho
    (ej: tira roja 'ALKA CEREZA 12' al lado derecho del producto agrupado).
    Retorna la coordenada X hasta donde recortar.
    """
    if np is None:
        return None

    w, h = img.size
    if w < 120:
        return None

    rgb_img = img.convert("RGB")
    arr = np.array(rgb_img)
    is_white = np.all(arr > 240, axis=2)
    col_white = np.mean(is_white, axis=0)

    for x in range(int(w * 0.60), int(w * 0.92)):
        if col_white[x] > 0.95:
            right_active = np.where(col_white[x:] < 0.95)[0]
            if len(right_active) >= 12:
                ribbon_w = right_active[-1] - right_active[0] + 1
                if ribbon_w <= w * 0.25:
                    ribbon_rows = np.where(np.mean(is_white[:, x+right_active[0]:x+right_active[-1]+1], axis=1) < 0.98)[0]
                    if len(ribbon_rows):
                        ribbon_h = ribbon_rows[-1] - ribbon_rows[0] + 1
                        if ribbon_h / ribbon_w >= 2.2: # Cinta vertical
                            left_active = np.where(col_white[:x] < 0.95)[0]
                            if len(left_active) >= 30: # Hay producto real a la izquierda
                                return x
    return None


def clean_and_square_image(
    img: Image.Image,
    target_max_dim: int = 800,
    padding_pct: float = 0.04
) -> Image.Image:
    """
    Limpia franjas laterales (izq/der), etiquetas superiores,
    recorta márgenes vacíos y encuadra en formato cuadrado 1:1 con fondo blanco.
    """
    # 1. Quitar franja lateral izquierda si existe
    crop_x_left = detect_lateral_strip_divider(img)
    if crop_x_left and crop_x_left < img.width * 0.5:
        img = img.crop((crop_x_left, 0, img.width, img.height))

    # 2. Quitar insignia superior flotante si existe
    crop_y_top = detect_top_floating_badge(img)
    if crop_y_top and crop_y_top < img.height * 0.6:
        img = img.crop((0, crop_y_top, img.width, img.height))

    # 3. Quitar cinta lateral derecha si existe
    crop_x_right = detect_right_vertical_ribbon(img)
    if crop_x_right and crop_x_right > img.width * 0.5:
        img = img.crop((0, 0, crop_x_right, img.height))

    # Asegurar modo RGB
    if img.mode in ("RGBA", "LA", "P"):
        canvas_bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if "A" in img.mode:
            canvas_bg.paste(img, mask=img.split()[-1])
        else:
            canvas_bg.paste(img)
        img = canvas_bg
    else:
        img = img.convert("RGB")

    # 4. Autocrop robusto (con numpy o fallback con pure Pillow)
    if np is not None:
        arr = np.array(img)
        w, h = img.size
        non_white = np.any(arr < 240, axis=2)
        row_frac = np.mean(non_white, axis=1)
        col_frac = np.mean(non_white, axis=0)
        active_y = np.where(row_frac > 0.01)[0]
        active_x = np.where(col_frac > 0.01)[0]

        if len(active_y) and len(active_x):
            y0, y1 = active_y[0], active_y[-1] + 1
            x0, x1 = active_x[0], active_x[-1] + 1
            pad_y = int((y1 - y0) * padding_pct)
            pad_x = int((x1 - x0) * padding_pct)
            pad = max(pad_x, pad_y)
            crop_box = (
                max(0, x0 - pad),
                max(0, y0 - pad),
                min(w, x1 + pad),
                min(h, y1 + pad),
            )
            img = img.crop(crop_box)
    else:
        bg = Image.new("RGB", img.size, (255, 255, 255))
        diff = ImageChops.difference(img, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)

    # 5. Encuadre cuadrado centrado (1:1)
    max_side = max(img.width, img.height)
    square_canvas = Image.new("RGB", (max_side, max_side), (255, 255, 255))
    offset = ((max_side - img.width) // 2, (max_side - img.height) // 2)
    square_canvas.paste(img, offset)

    # 6. Redimensionar si excede tamaño máximo razonable
    if square_canvas.width > target_max_dim:
        square_canvas = square_canvas.resize(
            (target_max_dim, target_max_dim),
            Image.Resampling.LANCZOS
        )

    return square_canvas


def optimize_product_image_base64(raw_base64: str, quality: int = 85) -> str:
    """
    Recibe un string base64 de imagen, la optimiza y normaliza
    y retorna el base64 limpio.
    """
    if not raw_base64 or not raw_base64.strip():
        return raw_base64

    clean_b64 = raw_base64.strip()
    prefix = ""
    if "," in clean_b64 and "base64" in clean_b64.split(",")[0]:
        prefix, clean_b64 = clean_b64.split(",", 1)
        prefix += ","

    try:
        raw_bytes = base64.b64decode(clean_b64)
        with Image.open(BytesIO(raw_bytes)) as img:
            processed = clean_and_square_image(img)
            buffer = BytesIO()
            processed.save(buffer, format="JPEG", quality=quality, optimize=True)
            result_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"{prefix}{result_b64}" if prefix else result_b64
    except Exception:
        return raw_base64
