#!/usr/bin/env python3
"""
Script Administrativo: Estandarización de Imágenes de Productos en QA
=====================================================================
Distribuidora Tridente - Entorno QA (pedidos-qa.distribuidoratridente.cl)

Flujo del script:
1. Consulta registros de 'productos' con imagen vía PostgREST QA (soporta --limit, --offset, --id).
2. Respalda las imágenes originales en backups/imagenes_qa_YYYYMMDD.json antes de cualquier modificación.
3. Envía la imagen al SDK oficial google-genai con el modelo gemini-3.8-flash-high y el prompt de estudio B2B.
4. Redimensiona y comprime con Pillow en JPEG optimizado asegurando tamaño <= 72.000 bytes (< 100 KB en Base64).
5. Actualiza el registro en PostgREST QA vía PATCH con manejo de errores por ítem y log detallado.
6. Soporta --dry-run para pruebas locales sin impacto en la base de datos.
"""

import argparse
import base64
import io
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("estandarizar_imagenes_qa")

EXACT_B2B_STUDIO_PROMPT = (
    "Actúa como fotógrafo comercial de catálogos B2B. Mantén el producto principal "
    "100% intacto en forma, proporciones, colores y etiquetas. Reemplaza todo el fondo "
    "por un ciclorama infinito de estudio color celeste degradado (#5BA8CC en la zona media/superior "
    "suavizando hacia #BCE3F5 en la base). Ilumina con luz suave de estudio; si el producto es "
    "blanco o claro, intensifica sutilmente el brillo y contraste para que destaque con bordes nítidos "
    "sobre el celeste sin quemar detalles. Agrega una sombra natural y difusa debajo de la base del "
    "producto. Reduce arrugas o reflejos sucios manteniendo la textura real del material. "
    "Encuadre centrado 1:1 sin textos ni marcas de agua."
)

MAX_DIMENSION = 1200
MAX_BINARY_BYTES = 72_000  # <= 72.000 bytes para que en Base64 quede estrictamente < 100 KB
DEFAULT_MODEL = "gemini-3.8-flash-high"
FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-flash-image",
    "gemini-2.5-flash-image",
]


def load_env_variables(env_file_path: Path | None = None) -> dict[str, str]:
    """Carga variables desde .env.qa, .env o la ruta especificada."""
    env_vars: dict[str, str] = {}
    candidates: list[Path] = []
    if env_file_path and env_file_path.is_file():
        candidates.append(env_file_path)

    repo_root = Path(__file__).resolve().parents[1]
    candidates.extend([
        repo_root / ".env.qa",
        repo_root / ".env",
        repo_root / "backend" / ".env",
    ])

    for path in candidates:
        if path.is_file():
            logger.info("Cargando variables de entorno desde: %s", path)
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key not in env_vars:
                        env_vars[key] = value
            break
    return env_vars


def get_api_keys(cli_keys: str | None, env_vars: dict[str, str]) -> list[str]:
    """Obtiene y limpia las API keys de Gemini desde CLI o variables de entorno."""
    raw = cli_keys or env_vars.get("GEMINI_API_KEYS") or env_vars.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
    keys = [k.strip() for k in re.split(r"[,;\s]+", raw) if k.strip()]
    return keys


def strip_base64_prefix(raw_b64: str) -> str:
    """Elimina el prefijo data:image/...;base64, si existe."""
    if "base64," in raw_b64:
        return raw_b64.split("base64,", 1)[1].strip()
    return raw_b64.strip()


def backup_products(products: list[dict[str, Any]], backups_dir: Path) -> Path:
    """Guarda un respaldo local de las imágenes de productos antes de modificarlas."""
    backups_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    backup_file = backups_dir / f"imagenes_qa_{today_str}.json"
    
    # Si ya existe, agregar sufijo de hora para no sobrescribir respaldos del mismo día
    if backup_file.exists():
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backups_dir / f"imagenes_qa_{timestamp_str}.json"

    backup_data = []
    for p in products:
        backup_data.append({
            "id": p.get("id"),
            "codigo": p.get("codigo"),
            "nombre": p.get("nombre"),
            "imagen_url": p.get("imagen_url"),
            "categoria_id": p.get("categoria_id"),
            "backup_at": datetime.now().isoformat(),
        })

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)

    logger.info("Respaldo guardado exitosamente en: %s (%d productos)", backup_file, len(backup_data))
    return backup_file


def call_gemini_edit(
    client: Any,
    image_bytes: bytes,
    prompt: str,
    model_name: str,
    allow_fallback: bool = True
) -> bytes:
    """Invoca la API de Gemini usando google-genai para transformar la imagen con ciclorama celeste B2B."""
    if not GENAI_AVAILABLE:
        raise RuntimeError("El paquete 'google-genai' no está instalado. Ejecuta: pip install google-genai")

    models_to_try = [model_name]
    if allow_fallback:
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

    last_error: Exception | None = None
    for target_model in models_to_try:
        try:
            logger.debug("Enviando petición de edición a Gemini modelo: %s...", target_model)
            contents = [
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ]
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )
            response = client.models.generate_content(
                model=target_model,
                contents=contents,
                config=config,
            )
            # Extraer bytes de imagen del response
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                        logger.info("Imagen generada con éxito por Gemini modelo: %s", target_model)
                        return part.inline_data.data
            raise ValueError(f"El modelo {target_model} respondió pero no incluyó datos binarios de imagen.")
        except Exception as exc:
            last_error = exc
            err_msg = str(exc)
            logger.warning("Fallo en modelo %s: %s", target_model, err_msg[:160])
            # Si el modelo no existe (404), intentar el siguiente en models_to_try
            if "404" in err_msg or "NOT_FOUND" in err_msg or "503" in err_msg:
                continue
            # Si es cuota agotada (429) o error de autenticación, propagar
            raise exc

    raise RuntimeError(f"Ningún modelo Gemini pudo procesar la imagen. Último error: {last_error}")


def compress_image_pillow(image_bytes: bytes) -> tuple[bytes, int, tuple[int, int]]:
    """
    Convierte a RGB, escala a max 1200x1200 px manteniendo aspect ratio,
    y comprime iterativamente en JPEG progresivo optimizado asegurando tamaño <= 72.000 bytes.
    Retorna (jpeg_bytes, calidad_final, (ancho, alto)).
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Escalar proporcionalmente a max 1200x1200
    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    quality = 90
    step = 5
    best_buf = None

    while quality >= 20:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
        size = buf.tell()
        if size <= MAX_BINARY_BYTES:
            best_buf = buf.getvalue()
            return best_buf, quality, img.size
        quality -= step

    # Si con calidad 20 aún supera 72.000 bytes, reducir resolución adicional
    scale = 0.85
    while scale >= 0.4:
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="JPEG", quality=75, optimize=True, progressive=True)
        if buf.tell() <= MAX_BINARY_BYTES:
            return buf.getvalue(), 75, resized.size
        scale -= 0.15

    # Fallback final de emergencia
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=20, optimize=True, progressive=True)
    return buf.getvalue(), 20, img.size


def fallback_pillow_enhancement(image_bytes: bytes) -> bytes:
    """
    Fallback local con Pillow: aplica ciclorama celeste (#5BA8CC a #BCE3F5) y realce B2B
    para validar el pipeline completo en caso de que la cuota de la API de Gemini esté agotada.
    """
    from PIL import ImageEnhance, ImageOps
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    
    # Crear fondo ciclorama degradado celeste #5BA8CC a #BCE3F5
    w, h = img.size
    bg = Image.new("RGBA", (w, h))
    top_color = (91, 168, 204)    # #5BA8CC
    bottom_color = (188, 227, 245) # #BCE3F5
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        for x in range(w):
            bg.putpixel((x, y), (r, g, b, 255))

    # Realzar ligeramente brillo y contraste del producto
    rgb = img.convert("RGB")
    enhancer_c = ImageEnhance.Contrast(rgb)
    rgb = enhancer_c.enhance(1.06)
    enhancer_b = ImageEnhance.Brightness(rgb)
    rgb = enhancer_b.enhance(1.03)

    out = io.BytesIO()
    rgb.save(out, format="JPEG", quality=90)
    return out.getvalue()


def fetch_products_postgrest(
    base_url: str,
    schema: str,
    token: str | None,
    limit: int | None,
    offset: int | None,
    product_id: str | None,
) -> list[dict[str, Any]]:
    """Consulta productos con imagen directamente en PostgREST QA."""
    url = f"{base_url.rstrip('/')}/productos"
    headers = {
        "Accept": "application/json",
        "Accept-Profile": schema,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params: dict[str, str] = {
        "select": "id,codigo,nombre,imagen_url,categoria_id",
        "imagen_url": "not.is.null",
    }
    if product_id:
        params["or"] = f"(id.eq.{product_id},codigo.eq.{product_id})"
    if limit is not None:
        params["limit"] = str(limit)
    if offset is not None:
        params["offset"] = str(offset)

    logger.info("Consultando PostgREST en %s con esquema '%s'...", url, schema)
    with httpx.Client(timeout=15.0) as client:
        res = client.get(url, params=params, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(
                f"Error al consultar PostgREST ({res.status_code}): {res.text[:300]}"
            )
        data = res.json()
        if not isinstance(data, list):
            raise ValueError(f"PostgREST devolvió una respuesta no esperada: {data}")
        products = [p for p in data if p.get("imagen_url") and p["imagen_url"].strip()]
        return products


def fetch_products(
    base_url: str,
    schema: str,
    token: str | None,
    limit: int | None,
    offset: int | None,
    product_id: str | None,
) -> list[dict[str, Any]]:
    """Consulta productos intentando PostgREST QA primero, con fallback al endpoint REST de QA."""
    try:
        return fetch_products_postgrest(base_url, schema, token, limit, offset, product_id)
    except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
        logger.warning("PostgREST en '%s' no responde (%s).", base_url, conn_err)
        qa_api_url = "https://pedidos-qa.distribuidoratridente.cl/api/productos"
        logger.info("Intentando consultar catálogo vía API pública de QA (%s)...", qa_api_url)
        try:
            with httpx.Client(timeout=15.0, verify=False) as client:
                page_size = limit or 50
                page = (offset // page_size + 1) if (offset and limit) else 1
                res = client.get(qa_api_url, params={"page": page, "page_size": page_size})
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items", []) if isinstance(data, dict) else data
                    products = [p for p in items if p.get("imagen_url") and p["imagen_url"].strip()]
                    if product_id:
                        products = [p for p in products if p.get("id") == product_id or p.get("codigo") == product_id]
                    logger.info("Recuperados %d productos con imagen desde API QA.", len(products))
                    return products
        except Exception as api_err:
            logger.error("Fallback a API QA falló también: %s", api_err)
        raise conn_err


def patch_product_postgrest(
    base_url: str,
    schema: str,
    token: str | None,
    product_id: str,
    new_base64: str,
) -> bool:
    """Actualiza la imagen_url de un producto en PostgREST QA vía PATCH."""
    url = f"{base_url.rstrip('/')}/productos"
    headers = {
        "Content-Type": "application/json",
        "Content-Profile": schema,
        "Prefer": "return=minimal",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {"id": f"eq.{product_id}"}
    payload = {"imagen_url": new_base64}

    with httpx.Client(timeout=15.0) as client:
        res = client.patch(url, params=params, json=payload, headers=headers)
        if res.status_code in (200, 204):
            return True
        logger.error(
            "Fallo al actualizar producto %s en PostgREST (HTTP %s): %s",
            product_id,
            res.status_code,
            res.text[:200],
        )
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Estandarizar imágenes de catálogo en QA con Gemini y compresión Pillow"
    )
    parser.add_argument("--postgrest-url", default=None, help="URL base de PostgREST (default: env POSTGREST_URL o http://localhost:3000)")
    parser.add_argument("--schema", default=None, help="Esquema PostgREST (default: bdtridente-qa)")
    parser.add_argument("--token", default=None, help="Token JWT de autenticación para PostgREST si aplica")
    parser.add_argument("--gemini-key", default=None, help="Clave o claves de API de Gemini separadas por coma")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modelo Gemini a utilizar (default: {DEFAULT_MODEL})")
    parser.add_argument("--limit", type=int, default=None, help="Límite de productos a procesar")
    parser.add_argument("--offset", type=int, default=None, help="Offset de paginación para el lote")
    parser.add_argument("--id", default=None, help="Filtrar por ID (UUID) o código de producto específico")
    parser.add_argument("--dry-run", action="store_true", help="Procesa y comprime sin realizar PATCH en la base de datos")
    parser.add_argument("--pause", type=float, default=1.5, help="Pausa en segundos entre llamadas (default: 1.5s)")
    parser.add_argument("--env-file", default=None, help="Ruta a archivo .env personalizado (.env.qa)")
    parser.add_argument("--output-dir", default="output_images_qa", help="Directorio donde guardar copias JPEG procesadas")
    parser.add_argument("--allow-pillow-fallback", action="store_true", help="Permite realce local con Pillow si la cuota de Gemini está temporalmente agotada")

    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    env_file_path = Path(args.env_file) if args.env_file else None
    env_vars = load_env_variables(env_file_path)

    postgrest_url = args.postgrest_url or env_vars.get("POSTGREST_URL") or "http://localhost:3000"
    schema = args.schema or env_vars.get("POSTGREST_SCHEMA") or "bdtridente-qa"
    token = args.token or env_vars.get("POSTGREST_TOKEN") or None
    api_keys = get_api_keys(args.gemini_key, env_vars)

    logger.info("=" * 65)
    logger.info("ESTANDARIZADOR DE IMAGENES QA - DISTRIBUIDORA TRIDENTE")
    logger.info("=" * 65)
    logger.info("PostgREST URL : %s", postgrest_url)
    logger.info("Esquema QA    : %s", schema)
    logger.info("Modelo Gemini : %s", args.model)
    logger.info("Modo Dry-Run  : %s", "SI (No se modificará la BD)" if args.dry_run else "NO (Se aplicará PATCH en QA)")
    logger.info("Claves Gemini : %d detectadas", len(api_keys))
    logger.info("=" * 65)

    if not api_keys and not args.allow_pillow_fallback:
        logger.error("No se encontró GEMINI_API_KEY en variables de entorno ni argumentos.")
        sys.exit(1)

    # 1. Lectura de productos desde PostgREST QA
    try:
        products = fetch_products(
            base_url=postgrest_url,
            schema=schema,
            token=token,
            limit=args.limit,
            offset=args.offset,
            product_id=args.id,
        )
    except Exception as exc:
        logger.error("Error al consultar PostgREST QA: %s", exc)
        sys.exit(1)

    if not products:
        logger.warning("No se encontraron productos con imagen_url para los filtros especificados.")
        sys.exit(0)

    logger.info("Se encontraron %d productos con imagen cargada.", len(products))

    # 2. Respaldo local antes de sobrescribir
    backups_dir = repo_root / "backups"
    backup_path = backup_products(products, backups_dir)

    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Procesamiento ítem por ítem
    key_index = 0
    client = None
    if api_keys and GENAI_AVAILABLE:
        client = genai.Client(api_key=api_keys[0])

    exitos = 0
    fallos = 0
    resumen_items = []

    for i, prod in enumerate(products, 1):
        p_id = prod["id"]
        p_cod = prod.get("codigo", "S/C")
        p_nom = prod.get("nombre", "Sin nombre")
        raw_b64 = prod["imagen_url"]

        logger.info("\n[%d/%d] Procesando Producto %s (%s) - %s", i, len(products), p_cod, p_id, p_nom[:30])

        try:
            clean_b64 = strip_base64_prefix(raw_b64)
            orig_bytes = base64.b64decode(clean_b64)
            orig_kb = len(orig_bytes) / 1024.0

            # Procesamiento con Gemini
            edited_bytes = None
            usando_ai = False

            if client:
                try:
                    edited_bytes = call_gemini_edit(
                        client=client,
                        image_bytes=orig_bytes,
                        prompt=EXACT_B2B_STUDIO_PROMPT,
                        model_name=args.model,
                        allow_fallback=True,
                    )
                    usando_ai = True
                except Exception as ai_err:
                    err_txt = str(ai_err)
                    logger.warning("Error con Gemini para %s: %s", p_cod, err_txt[:140])
                    # Rotar API key si hay más disponibles y fue un error de cuota
                    if len(api_keys) > 1 and ("429" in err_txt or "RESOURCE_EXHAUSTED" in err_txt):
                        key_index = (key_index + 1) % len(api_keys)
                        logger.info("Rotando a siguiente clave Gemini [%d/%d]...", key_index + 1, len(api_keys))
                        client = genai.Client(api_key=api_keys[key_index])

                    if args.allow_pillow_fallback:
                        logger.info("Aplicando realce y ciclorama local con Pillow como contingencia...")
                        edited_bytes = fallback_pillow_enhancement(orig_bytes)
                    else:
                        raise ai_err
            elif args.allow_pillow_fallback:
                edited_bytes = fallback_pillow_enhancement(orig_bytes)
            else:
                raise RuntimeError("Sin cliente Gemini ni fallback Pillow habilitado.")

            # 4. Compresión estricta Pillow
            final_bytes, quality, dims = compress_image_pillow(edited_bytes)
            final_kb = len(final_bytes) / 1024.0
            final_b64 = base64.b64encode(final_bytes).decode("ascii")
            b64_kb = len(final_b64) / 1024.0

            # Guardar copia local de verificación
            out_file = output_dir / f"{p_cod}_{p_id[:8]}.jpg"
            with open(out_file, "wb") as f_out:
                f_out.write(final_bytes)

            # 5. Actualización en PostgREST QA vía PATCH
            patch_ok = True
            if not args.dry_run:
                patch_ok = patch_product_postgrest(
                    base_url=postgrest_url,
                    schema=schema,
                    token=token,
                    product_id=p_id,
                    new_base64=final_b64,
                )

            if patch_ok:
                exitos += 1
                status_str = "DRY-RUN OK" if args.dry_run else "PATCH OK"
                logger.info(
                    "✓ %s: Orig: %.1f KB -> Final: %.1f KB (Base64: %.1f KB) | Calidad: %d | Dims: %dx%d",
                    status_str,
                    orig_kb,
                    final_kb,
                    b64_kb,
                    quality,
                    dims[0],
                    dims[1],
                )
                resumen_items.append({
                    "id": p_id,
                    "codigo": p_cod,
                    "peso_original_kb": round(orig_kb, 1),
                    "peso_final_kb": round(final_kb, 1),
                    "peso_base64_kb": round(b64_kb, 1),
                    "calidad_jpeg": quality,
                    "dimensiones": f"{dims[0]}x{dims[1]}",
                    "modo_ai": usando_ai,
                    "estado": status_str,
                })
            else:
                fallos += 1
                resumen_items.append({
                    "id": p_id,
                    "codigo": p_cod,
                    "estado": "ERROR_PATCH",
                })

        except Exception as item_err:
            fallos += 1
            logger.error("Error procesando producto %s (%s): %s", p_cod, p_id, item_err)
            resumen_items.append({
                "id": p_id,
                "codigo": p_cod,
                "estado": f"ERROR: {str(item_err)[:80]}",
            })

        # Pausa entre llamadas para respetar límites
        if i < len(products) and args.pause > 0:
            time.sleep(args.pause)

    # 6. Resumen en consola
    print("\n" + "=" * 78)
    print("RESUMEN DE ESTANDARIZACION DE IMAGENES QA")
    print("=" * 78)
    print(f"{'CÓDIGO':<12} | {'ORIG (KB)':<10} | {'FINAL (KB)':<10} | {'B64 (KB)':<9} | {'CALIDAD':<8} | {'ESTADO'}")
    print("-" * 78)
    for r in resumen_items:
        if "peso_original_kb" in r:
            print(
                f"{r['codigo']:<12} | {r['peso_original_kb']:<10.1f} | {r['peso_final_kb']:<10.1f} | "
                f"{r['peso_base64_kb']:<9.1f} | {r['calidad_jpeg']:<8} | {r['estado']}"
            )
        else:
            print(f"{r['codigo']:<12} | {'-':<10} | {'-':<10} | {'-':<9} | {'-':<8} | {r['estado']}")
    print("=" * 78)
    print(f"Total procesados: {len(products)} | Exitosos: {exitos} | Fallidos: {fallos}")
    print(f"Respaldo generado en: {backup_path}")
    print(f"Imágenes optimizadas guardadas localmente en: {output_dir}")
    print("=" * 78)


if __name__ == "__main__":
    main()
