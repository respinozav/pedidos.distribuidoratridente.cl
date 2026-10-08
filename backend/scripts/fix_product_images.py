"""Script batch para arreglar y normalizar todas las imágenes existentes de productos en la base de datos.

Efectos:
- Recorta pestañas / franjas laterales de marcas o banners ajenos al producto.
- Remueve márgenes sobrantes blancos para centrar el producto.
- Normaliza las imágenes a formato cuadrado (1:1) sobre fondo blanco.
- Optimiza la compresión para que carguen de forma ultrarrápida al comprar y en el catálogo PDF.
- Invalida la caché del catálogo PDF para que tome los cambios inmediatamente.
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.entities import Producto
from app.services.image_service import optimize_product_image_base64
from app.services.catalog import invalidate_catalog_cache


def fix_all_product_images(dry_run: bool = False):
    db = SessionLocal()
    try:
        prods = (
            db.query(Producto)
            .filter(Producto.imagen_url.isnot(None), Producto.imagen_url != "")
            .all()
        )
        print(f"Total productos con imagen a revisar: {len(prods)}")
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for p in prods:
            try:
                original_len = len(p.imagen_url)
                optimized = optimize_product_image_base64(p.imagen_url)
                if optimized and optimized != p.imagen_url:
                    if not dry_run:
                        p.imagen_url = optimized
                    updated_count += 1
                    print(f"[{p.codigo}] {p.nombre[:35]:35s} -> Optimizado ({original_len} -> {len(optimized)} chars)")
                else:
                    skipped_count += 1
            except Exception as e:
                error_count += 1
                print(f"[{p.codigo}] ERROR: {e}")

        if not dry_run and updated_count > 0:
            db.commit()
            invalidate_catalog_cache()
            print(f"\n¡Éxito! Base de datos actualizada con {updated_count} productos optimizados.")
            print("Caché de catálogo PDF invalidada.")
        elif dry_run:
            print(f"\n[Modo Dry-Run] Se habrían actualizado {updated_count} productos.")
        else:
            print("\nNo hubo cambios necesarios.")

        print(f"Resumen: {updated_count} actualizados, {skipped_count} sin cambios, {error_count} errores.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Arreglar y optimizar imágenes de productos")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin modificar la base de datos")
    args = parser.parse_args()
    fix_all_product_images(dry_run=args.dry_run)
