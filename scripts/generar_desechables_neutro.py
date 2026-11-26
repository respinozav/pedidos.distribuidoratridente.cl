#!/usr/bin/env python3
"""
Generación de Imágenes con Fondo de Estudio Neutro para Desechables
==================================================================
Distribuidora Tridente

Aplica el fondo neutro cálido (#F6F7F1, RGB 246, 247, 241) según la imagen
de referencia adjunta por el usuario (referencia_fondo_neutro.png), eliminando
completamente el fondo celeste previo y preservando sombras naturales de contacto
y la máxima nitidez del producto.
"""

import io
import os
from pathlib import Path
from PIL import Image
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
REF_NEUTRO_PATH = REPO_ROOT / "scripts" / "referencia_fondo_neutro.png"
ASSETS_DIR = REPO_ROOT / "scripts" / "assets_estudio"
REF_BAG_PATH = REPO_ROOT / "scripts" / "referencia_fondo.jpg"

MAX_BINARY_BYTES = 72_000

if not REF_NEUTRO_PATH.exists():
    raise FileNotFoundError(f"No se encontró la referencia neutra en {REF_NEUTRO_PATH}")

ref_im = Image.open(REF_NEUTRO_PATH).convert("RGB")


def get_neutral_bg(w: int = 900, h: int = 900) -> Image.Image:
    return ref_im.resize((w, h), Image.Resampling.LANCZOS)


def compress_to_limit(img: Image.Image, max_bytes: int = MAX_BINARY_BYTES) -> tuple[bytes, int]:
    for q in range(88, 35, -2):
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= max_bytes:
            return raw, q
    return raw, 35


def process_cyan_to_neutral(img: Image.Image, codigo: str = "", target_dim: int = 900) -> Image.Image:
    if img.size != (target_dim, target_dim):
        img = img.resize((target_dim, target_dim), Image.Resampling.LANCZOS)

    arr = np.array(img.convert("RGB"), dtype=np.float32)
    h, w, _ = arr.shape

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # Cyan metric: en fondo celeste b > g > r
    cyan_metric = (b - r) * 0.6 + (g - r) * 0.4

    # Perfil del fondo celeste en margen izquierdo (cols 5 a 25)
    bg_cyan_col = np.mean(arr[:, 5:25, :], axis=1)
    bg_r = bg_cyan_col[:, 0]
    bg_g = bg_cyan_col[:, 1]
    bg_b = bg_cyan_col[:, 2]
    bg_brightness = (bg_r + bg_g + bg_b) / 3.0

    brightness = (r + g + b) / 3.0

    # Ratio de sombra relativa al fondo limpio
    shadow_ratio = np.clip(brightness / (bg_brightness[:, np.newaxis] + 1e-5), 0.55, 1.0)

    # Canvas neutro de destino
    neutral_bg = get_neutral_bg(w, h)
    neutral_bg_arr = np.array(neutral_bg, dtype=np.float32)

    # Umbrales según material del producto
    if codigo in ["774", "775", "776", "777", "778"]:
        # Plumavit: blanco sólido/gris claro
        t_low = 8.0
        t_high = 24.0
    elif codigo in ["770", "771", "772", "773"]:
        # Bambú/madera: tono cálido marrón/amarillo
        t_low = 6.0
        t_high = 22.0
    elif codigo in ["765", "766"]:
        # Vasos transparentes
        t_low = 14.0
        t_high = 32.0
    else:
        # Bolsas, vasos de papel (760-764, 767-769)
        t_low = 10.0
        t_high = 26.0

    # Alfa de producto
    alpha = np.clip((t_high - cyan_metric) / (t_high - t_low), 0.0, 1.0)

    # De-spill de rebote celeste en bordes del producto
    b_despill = np.minimum(b, np.maximum(r, g) + 3.0)
    if codigo in ["774", "775", "776", "777", "778", "767", "761"]:
        g_despill = np.minimum(g, r + 5.0)
    else:
        g_despill = g

    prod_clean = np.stack([r, g_despill, b_despill], axis=2)

    # Piso neutro con sombra de contacto preservada
    floor_factor = np.clip((np.arange(h)[:, np.newaxis] - h * 0.55) / (h * 0.25), 0.0, 1.0)
    effective_shadow = 1.0 - floor_factor * (1.0 - shadow_ratio) * 0.85
    bg_shadowed = neutral_bg_arr * effective_shadow[:, :, np.newaxis]

    # Mezcla compuesta
    alpha_3d = alpha[:, :, np.newaxis]
    out_arr = prod_clean * alpha_3d + bg_shadowed * (1.0 - alpha_3d)
    out_arr = np.clip(out_arr, 0, 255).astype(np.uint8)

    return Image.fromarray(out_arr)


def main():
    print("=" * 70)
    print("GENERADOR DE IMÁGENES DE DESECHABLES CON FONDO NEUTRO (#F6F7F1)")
    print("=" * 70)

    # 1. Procesar Referencia de Fondo (Bolsas 760, 761, 762, 763)
    print("\n1. Procesando imagen de referencia de bolsas (760, 761, 762, 763)...")
    with Image.open(REF_BAG_PATH) as bag_im:
        bag_neutro = process_cyan_to_neutral(bag_im, "762", target_dim=900)
        raw_bag, q_bag = compress_to_limit(bag_neutro, MAX_BINARY_BYTES)
        with open(REF_BAG_PATH, "wb") as f:
            f.write(raw_bag)
        print(f"  ✓ referencia_fondo.jpg actualizado: {len(raw_bag)} bytes ({len(raw_bag)/1024:.1f} KB, q={q_bag})")

    # 2. Procesar Assets Curados 764 a 778
    curated_codes = ["764", "765", "766", "767", "768", "769", "770", "771", "772", "773", "774", "775", "776", "777", "778"]
    print(f"\n2. Procesando {len(curated_codes)} productos desechables en assets_estudio/...")
    
    for cod in curated_codes:
        asset_file = ASSETS_DIR / f"{cod}_final.jpg"
        if not asset_file.exists():
            print(f"  ⚠ No se encontró {asset_file}")
            continue

        with Image.open(asset_file) as im:
            res_neutro = process_cyan_to_neutral(im, cod, target_dim=900)
            raw_bytes, q = compress_to_limit(res_neutro, MAX_BINARY_BYTES)
            with open(asset_file, "wb") as f:
                f.write(raw_bytes)
                
            arr = np.array(res_neutro)
            tl = arr[5, 5].tolist()
            br = arr[-6, -6].tolist()
            print(f"  ✓ [{cod}] {len(raw_bytes):5d} B ({len(raw_bytes)/1024:4.1f} KB, q={q:2d}) | TL={tl} BR={br}")

    print("\n" + "=" * 70)
    print("✓ Todos los desechables convertidos exitosamente al estándar de fondo neutro.")
    print("=" * 70)


if __name__ == "__main__":
    main()
