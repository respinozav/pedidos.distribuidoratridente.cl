"""Script batch para estandarizar, limpiar y mejorar drásticamente la nitidez
de todas las imágenes de la tabla Producto en la base de datos local.

Mejoras aplicadas:
1. Limpieza de franjas laterales de marcas ajenas (banners BAT, tiras verticales).
2. Limpieza de etiquetas/textos flotantes superiores/inferiores.
3. Limpieza de fondo: convierte fondos grises, sombras y ruido a blanco puro (#FFFFFF) de estudio.
4. Encuadre estandarizado por categoría:
   - Cigarrillos y vapes (BAT, MARLBORO, LATINOS, ATLAS, VAPORIZADORES): altura idéntica estandarizada al 88%.
   - Confites, chocolates y abarrotes (CONFITES, ABARROTES, TABACOS, TABAQUERIA): ajuste al 86% centrado.
5. Ultra-nitidez: UnsharpMask (radio 1.8, 175%) + micro-contraste y saturación sutil para textos y logos nítidos.
6. Canvas 1:1 (cuadrado) perfecto sobre fondo blanco.
7. Respaldo automático JSON antes de aplicar cambios para revertir si se desea.
8. Invalidación automática de caché de catálogo PDF.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from io import BytesIO
import base64
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.entities import Producto, Categoria
from app.services.image_service import (
    clean_and_square_image,
    optimize_product_image_base64,
    CATEGORY_CONFIG,
)
from app.services.catalog import invalidate_catalog_cache


def create_backup(db, backup_dir: str = "backup") -> str:
    """Crea un respaldo JSON de todas las imágenes actuales de productos."""
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_imagenes_productos_{timestamp}.json")

    prods = db.query(Producto).filter(Producto.imagen_url.isnot(None), Producto.imagen_url != "").all()
    data = []
    for p in prods:
        data.append({
            "id": str(p.id),
            "codigo": p.codigo,
            "nombre": p.nombre,
            "categoria": p.categoria.nombre if p.categoria else None,
            "imagen_url": p.imagen_url,
        })

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    print(f">> [Respaldo] Guardadas {len(data)} imágenes originales en: {backup_file}")
    return backup_file


def generate_comparison_image(orig_b64: str, new_b64: str, title: str, output_path: str, category_name: str = None):
    """Crea una imagen comparativa de 3 paneles (Original vs. HD Estudio vs. Capa Dibujo Animado)."""
    try:
        raw_orig = base64.b64decode(orig_b64.split(",")[-1])
        raw_new = base64.b64decode(new_b64.split(",")[-1])

        orig_img = Image.open(BytesIO(raw_orig)).convert("RGB")
        hd_img = Image.open(BytesIO(raw_new)).convert("RGB")

        # Generar versión dibujo animado (cel-shaded pop art)
        from app.services.image_service import stylize_cartoon_product_image
        cartoon_img = stylize_cartoon_product_image(hd_img)

        w, h = 420, 420
        canvas = Image.new("RGB", (w * 3 + 20, h), (235, 238, 242))
        canvas.paste(orig_img.resize((w, h), Image.Resampling.LANCZOS), (0, 0))
        canvas.paste(hd_img.resize((w, h), Image.Resampling.LANCZOS), (w + 10, 0))
        canvas.paste(cartoon_img.resize((w, h), Image.Resampling.LANCZOS), (w * 2 + 20, 0))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        canvas.save(output_path, format="JPEG", quality=92)
    except Exception as e:
        print(f"Error generando comparativa {title}: {e}")


def process_images(
    dry_run: bool = False,
    category_filter: str = None,
    export_samples: str = None,
    samples_limit: int = 15,
):
    db = SessionLocal()
    try:
        query = db.query(Producto).filter(Producto.imagen_url.isnot(None), Producto.imagen_url != "")
        if category_filter:
            cat_obj = db.query(Categoria).filter(Categoria.nombre.ilike(category_filter.strip())).first()
            if not cat_obj:
                print(f"ERROR: No se encontró la categoría '{category_filter}'.")
                return
            query = query.filter(Producto.categoria_id == cat_obj.id)

        prods = query.all()
        total = len(prods)
        print(f"\n========================================================")
        print(f" MEJORA DE IMÁGENES: {total} productos a procesar")
        print(f" Modo: {'[SIMULACIÓN DRY-RUN - BD INTACTA]' if dry_run else '[APLICANDO A BASE DE DATOS LOCAL]'}")
        if category_filter:
            print(f" Filtro de categoría: {category_filter}")
        print(f"========================================================\n")

        if not dry_run:
            create_backup(db)

        updated_count = 0
        error_count = 0
        category_stats = {}
        samples_exported = 0

        for idx, p in enumerate(prods, 1):
            cat_name = p.categoria.nombre if p.categoria else "SIN_CATEGORIA"
            if cat_name not in category_stats:
                category_stats[cat_name] = {"total": 0, "updated": 0, "errors": 0}
            category_stats[cat_name]["total"] += 1

            try:
                original_b64 = p.imagen_url
                optimized_b64 = optimize_product_image_base64(
                    original_b64,
                    quality=90,
                    category_name=cat_name,
                )

                if optimized_b64 and optimized_b64 != original_b64:
                    if not dry_run:
                        p.imagen_url = optimized_b64

                    updated_count += 1
                    category_stats[cat_name]["updated"] += 1

                    # Exportar muestras visuales (3 paneles: Original vs HD vs Dibujo Animado)
                    if export_samples and samples_exported < samples_limit:
                        sample_path = os.path.join(
                            export_samples,
                            f"comparativa_3paneles_{cat_name}_{p.codigo}_{idx}.jpg"
                        )
                        generate_comparison_image(
                            original_b64,
                            optimized_b64,
                            f"{p.codigo} - {p.nombre}",
                            sample_path,
                            category_name=cat_name
                        )
                        samples_exported += 1

                    if idx % 25 == 0 or idx == total:
                        print(f"[{idx}/{total}] Procesando... ({cat_name}) {p.codigo}: {p.nombre[:30]}")

            except Exception as e:
                error_count += 1
                category_stats[cat_name]["errors"] += 1
                print(f"[{p.codigo}] ERROR al procesar {p.nombre}: {e}")

        print("\n========================================================")
        print(" RESUMEN POR CATEGORÍA")
        print("========================================================")
        for cat, stats in sorted(category_stats.items()):
            print(f" - {cat:15s} | Total: {stats['total']:3d} | Mejorados: {stats['updated']:3d} | Errores: {stats['errors']}")

        if not dry_run and updated_count > 0:
            db.commit()
            invalidate_catalog_cache()
            print(f"\n>> [ÉXITO] Base de datos local actualizada con {updated_count} productos mejorados.")
            print(">> Caché de catálogo PDF invalidada para reflejar las nuevas imágenes.")
        elif dry_run:
            print(f"\n>> [Modo Dry-Run completado] Se revisaron {updated_count} productos SIN modificar la base de datos.")

        if export_samples and samples_exported > 0:
            print(f">> Muestras comparativas (Original vs HD vs Dibujo Animado) guardadas en: {export_samples}")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Estandarizar y mejorar nitidez de imágenes de productos")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin modificar la base de datos")
    parser.add_argument("--category", type=str, help="Filtrar por nombre de categoría (ej: BAT, CONFITES)")
    parser.add_argument("--export-samples", type=str, default="assets/samples_cartoon_comparison", help="Directorio donde exportar comparativas")
    parser.add_argument("--samples-limit", type=int, default=15, help="Límite de muestras comparativas a guardar")
    parser.add_argument("--apply", action="store_true", help="Aplicar directamente los cambios a la base de datos local")

    args = parser.parse_args()

    # Por defecto corre en dry-run (sin tocar la base de datos) salvo que se pase --apply explícito
    is_dry = args.dry_run or not args.apply
    if is_dry and not args.dry_run:
        print("[Aviso] Ejecutando en modo seguro (BD intacta). Para escribir en BD se requiere --apply.")

    process_images(
        dry_run=is_dry,
        category_filter=args.category,
        export_samples=args.export_samples,
        samples_limit=args.samples_limit,
    )

