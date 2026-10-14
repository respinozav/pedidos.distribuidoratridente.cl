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
from PIL import Image, ImageChops, ImageFilter, ImageEnhance, ImageOps

try:
    import numpy as np
except ImportError:
    np = None


# Reglas de estandarización visual por categoría
CATEGORY_CONFIG = {
    "BAT": {"fill_pct": 0.88, "fit_mode": "height"},
    "MARLBORO": {"fill_pct": 0.88, "fit_mode": "height"},
    "LATINOS": {"fill_pct": 0.88, "fit_mode": "height"},
    "ATLAS": {"fill_pct": 0.88, "fit_mode": "height"},
    "VAPORIZADORES": {"fill_pct": 0.88, "fit_mode": "height"},
    "TABACOS": {"fill_pct": 0.86, "fit_mode": "max_side"},
    "CONFITES": {"fill_pct": 0.86, "fit_mode": "max_side"},
    "ABARROTES": {"fill_pct": 0.85, "fit_mode": "max_side"},
    "TABAQUERIA": {"fill_pct": 0.85, "fit_mode": "max_side"},
}


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


def clean_background_to_white(img: Image.Image) -> Image.Image:
    """
    Limpia sombras suaves, fondos grisáceos y ruidos de compresión
    convirtiéndolos en blanco puro (#FFFFFF) para un acabado de estudio profesional.
    """
    rgb = img.convert("RGB")
    if np is not None:
        arr = np.array(rgb)
        max_c = np.max(arr, axis=2)
        min_c = np.min(arr, axis=2)
        # Píxeles casi blancos con baja saturación (sombras/ruido JPG alrededor del producto)
        is_near_white = (min_c > 220) & ((max_c - min_c) < 25)
        cleaned_arr = arr.copy()
        cleaned_arr[is_near_white] = [255, 255, 255]
        return Image.fromarray(cleaned_arr)
    else:
        # Fallback puro Pillow con autocontrast
        return ImageOps.autocontrast(rgb, cutoff=2)


def enhance_sharpness_and_clarity(img: Image.Image) -> Image.Image:
    """
    Aplica realce profesional de nitidez de alta definición sin crear halos ni ruido:
    - Radio fino (1.0) para definir tipografías de empaques con máxima legibilidad.
    - Threshold=3 para proteger gradientes y superficies lisas de motas o grano.
    """
    sharp = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=150, threshold=3))
    sharp = ImageEnhance.Sharpness(sharp).enhance(1.20)
    sharp = ImageEnhance.Color(sharp).enhance(1.08)
    return sharp


def stylize_cartoon_product_image(img: Image.Image) -> Image.Image:
    """
    Capa de visualización artística estilo ilustración digital / dibujo limpio y nítido:
    - Convierte texturas fotográficas en planos lisos y limpios estilo vector / animación.
    - Colores luminosos y vibrantes sin oscurecer ni quemar sombras.
    - Máxima nitidez en textos, sellos y logos sin motas negras ni exceso de contraste.
    - Fondo 100% blanco puro (#FFFFFF).
    """
    rgb = img.convert("RGB")
    if np is not None:
        arr = np.array(rgb)
        is_bg = np.all(arr > 240, axis=2)

        # 1. Suavizado de superficie para eliminar grano JPG y dar aspecto de ilustración vectorial
        smooth = rgb.filter(ImageFilter.MedianFilter(size=3))

        # 2. Colores alegres, luminosos y vibrantes (sin oscurecer ni quemar sombras)
        bright = ImageEnhance.Brightness(smooth).enhance(1.05)
        color = ImageEnhance.Color(bright).enhance(1.25)

        # 3. Posterizado sutil (7 bits) para escalonado de ilustración vectorial sin saltos bruscos
        poster = ImageOps.posterize(color, bits=7)

        # 4. Ultra-nitidez de precisión en letras, bordes y logos (threshold=3 mantiene superficies limpias)
        sharp = poster.filter(ImageFilter.UnsharpMask(radius=1.0, percent=190, threshold=3))
        sharp = ImageEnhance.Sharpness(sharp).enhance(1.25)

        # 5. Fondo 100% blanco puro garantizado
        final_arr = np.array(sharp)
        final_arr[is_bg] = [255, 255, 255]
        return Image.fromarray(final_arr)
    else:
        # Fallback Pillow sin numpy
        smooth = rgb.filter(ImageFilter.MedianFilter(size=3))
        bright = ImageEnhance.Brightness(smooth).enhance(1.05)
        color = ImageEnhance.Color(bright).enhance(1.25)
        poster = ImageOps.posterize(color, bits=7)
        sharp = poster.filter(ImageFilter.UnsharpMask(radius=1.0, percent=190, threshold=3))
        return ImageEnhance.Sharpness(sharp).enhance(1.25)



def clean_and_square_image(
    img: Image.Image,
    target_max_dim: int = 800,
    padding_pct: float = 0.02,
    category_name: Optional[str] = None,
    cartoon_mode: bool = False
) -> Image.Image:
    """
    Limpia franjas laterales (izq/der), etiquetas superiores,
    blanquea el fondo a estudio blanco puro, recorta márgenes vacíos,
    escala de forma estandarizada por categoría y mejora radicalmente la nitidez.
    Si cartoon_mode es True, aplica la capa artística tipo dibujo animado.
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

    # 4. Limpieza de fondo a blanco puro
    img = clean_background_to_white(img)

    # 5. Autocrop ajustado al producto real
    if np is not None:
        arr = np.array(img)
        w, h = img.size
        non_white = np.any(arr < 240, axis=2)
        row_frac = np.mean(non_white, axis=1)
        col_frac = np.mean(non_white, axis=0)
        active_y = np.where(row_frac > 0.005)[0]
        active_x = np.where(col_frac > 0.005)[0]

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

    # 6. Estandarización visual por categoría
    cat_key = (category_name or "").upper().strip()
    cfg = CATEGORY_CONFIG.get(cat_key, {"fill_pct": 0.86, "fit_mode": "max_side"})
    fill_pct = cfg["fill_pct"]
    fit_mode = cfg["fit_mode"]

    prod_w, prod_h = img.size
    aspect = prod_w / prod_h if prod_h > 0 else 1.0

    if fit_mode == "height" and aspect < 1.1:
        # Productos verticales (cajetillas, vapes) con altura estandarizada idéntica
        new_h = int(target_max_dim * fill_pct)
        new_w = max(1, int(new_h * aspect))
        if new_w > target_max_dim * 0.92:
            new_w = int(target_max_dim * 0.92)
            new_h = int(new_w / aspect)
    else:
        # Productos generales (confites, bolsas, abarrotes) ajustados al lado mayor
        max_dim = int(target_max_dim * fill_pct)
        if prod_w >= prod_h:
            new_w = max_dim
            new_h = max(1, int(new_w / aspect))
        else:
            new_h = max_dim
            new_w = max(1, int(new_h * aspect))

    resized_prod = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 7. Realce de nitidez o capa artística tipo dibujo animado
    if cartoon_mode:
        sharp_prod = stylize_cartoon_product_image(resized_prod)
    else:
        sharp_prod = enhance_sharpness_and_clarity(resized_prod)

    # 8. Montar sobre canvas cuadrado (1:1) con fondo blanco de estudio
    square_canvas = Image.new("RGB", (target_max_dim, target_max_dim), (255, 255, 255))
    offset = ((target_max_dim - new_w) // 2, (target_max_dim - new_h) // 2)
    square_canvas.paste(sharp_prod, offset)

    return square_canvas


def optimize_product_image_base64(
    raw_base64: str,
    quality: int = 90,
    category_name: Optional[str] = None,
    cartoon_mode: bool = False
) -> str:
    """
    Recibe un string base64 de imagen, la optimiza, normaliza por categoría,
    mejora la nitidez y retorna el base64 limpio.
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
            processed = clean_and_square_image(img, category_name=category_name, cartoon_mode=cartoon_mode)
            buffer = BytesIO()
            processed.save(buffer, format="JPEG", quality=quality, optimize=True)
            result_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"{prefix}{result_b64}" if prefix else result_b64
    except Exception:
        return raw_base64


