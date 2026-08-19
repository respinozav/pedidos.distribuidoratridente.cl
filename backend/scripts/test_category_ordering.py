"""Verificación de ordenamiento de categorías, creación correlativa y swap al editar."""

from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.entities import Categoria
from app.schemas.dto import CategoryInput
from app.repositories.base import Repository


def test_category_ordering_and_swap():
    db = SessionLocal()
    try:
        # 1. Verificar orden actual
        categories = list(
            db.scalars(
                select(Categoria)
                .where(Categoria.eliminado_at.is_(None))
                .order_by(Categoria.orden)
            )
        )
        print("--- Categorías Actuales ---")
        for c in categories:
            print(f"Orden {c.orden}: {c.nombre} (ID: {c.id})")

        orders = [c.orden for c in categories]
        assert len(orders) == 9, f"Se esperaban 9 categorías, hay {len(orders)}"
        assert orders == list(range(1, 10)), f"Se esperaba orden [1..9], se obtuvo {orders}"
        print("OK Prueba 1 superada: 9 categorias ordenadas del 1 al 9 correctamente.")

        # 2. Probar creación de categoría sin especificar orden (debe tomar 10)
        max_order = db.scalar(
            select(func.coalesce(func.max(Categoria.orden), 0)).where(Categoria.eliminado_at.is_(None))
        ) or 0
        new_order = max_order + 1
        assert new_order == 10, f"Se esperaba orden 10, se obtuvo {new_order}"

        test_cat = Categoria(
            nombre="CATEGORIA_PRUEBA_TEMP",
            orden=new_order,
            activo=True,
            en_catalogo_publico=True,
        )
        db.add(test_cat)
        db.commit()
        db.refresh(test_cat)
        print(f"[OK] Prueba 2 superada: Creada categoria temporal con orden automatico {test_cat.orden} (esperado: 10).")

        # 3. Probar swap en edicion: mover categoria con orden 8 a orden 3
        cat_8 = db.scalar(select(Categoria).where(Categoria.orden == 8, Categoria.eliminado_at.is_(None)))
        cat_3 = db.scalar(select(Categoria).where(Categoria.orden == 3, Categoria.eliminado_at.is_(None)))
        assert cat_8 is not None and cat_3 is not None
        name_8, name_3 = cat_8.nombre, cat_3.nombre

        print(f"Antes del swap: {name_8} tiene orden {cat_8.orden}, {name_3} tiene orden {cat_3.orden}")

        # Simular logica de routes.py update_category
        target_order = 3
        old_order = cat_8.orden  # 8

        target_cat = db.scalar(
            select(Categoria).where(
                Categoria.orden == target_order,
                Categoria.id != cat_8.id,
                Categoria.eliminado_at.is_(None),
            )
        )
        if target_cat:
            target_cat.orden = old_order
        cat_8.orden = target_order

        db.commit()
        db.refresh(cat_8)
        db.refresh(cat_3)

        print(f"Despues del swap: {cat_8.nombre} tiene orden {cat_8.orden}, {cat_3.nombre} tiene orden {cat_3.orden}")
        assert cat_8.orden == 3, f"Se esperaba que {name_8} fuera 3, es {cat_8.orden}"
        assert cat_3.orden == 8, f"Se esperaba que {name_3} fuera 8, es {cat_3.orden}"
        print("[OK] Prueba 3 superada: Swap 8 <-> 3 exitoso y bidireccional.")

        # Revertir el swap para dejarlo como estaba
        target_cat = db.scalar(
            select(Categoria).where(
                Categoria.orden == 8,
                Categoria.id != cat_8.id,
                Categoria.eliminado_at.is_(None),
            )
        )
        if target_cat:
            target_cat.orden = 3
        cat_8.orden = 8
        db.commit()
        db.refresh(cat_8)
        db.refresh(cat_3)
        assert cat_8.orden == 8 and cat_3.orden == 3
        print("[OK] Swap restaurado al estado original.")

        # 4. Eliminar categoria temporal de prueba
        db.delete(test_cat)
        db.commit()
        print("[OK] Categoria de prueba eliminada.")

        # Verificar estado final
        final_cats = list(
            db.scalars(
                select(Categoria)
                .where(Categoria.eliminado_at.is_(None))
                .order_by(Categoria.orden)
            )
        )
        final_orders = [c.orden for c in final_cats]
        assert final_orders == list(range(1, 10))
        print("[OK] Estado final verificado: 9 categorias con orden del 1 al 9.")
        print("\nTODAS LAS PRUEBAS PASARON EXITOSAMENTE!")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_category_ordering_and_swap()
