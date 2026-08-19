"""Script para reordenar las categorías existentes con orden 1 al 9."""

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.entities import Categoria


def reorder_categories():
    db = SessionLocal()
    try:
        categories = list(
            db.scalars(
                select(Categoria)
                .where(Categoria.eliminado_at.is_(None))
                .order_by(Categoria.nombre)
            )
        )
        print(f"Encontradas {len(categories)} categorías no eliminadas.")
        for index, cat in enumerate(categories, start=1):
            old_order = cat.orden
            cat.orden = index
            print(f"[{index}] {cat.nombre}: {old_order} -> {cat.orden}")
        db.commit()
        print("Reordenamiento completado exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"Error al reordenar: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reorder_categories()
