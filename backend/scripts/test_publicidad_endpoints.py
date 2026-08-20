import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.entities import Producto, Publicidad, Usuario
from app.controllers.routes import create_publicidad, list_public_publicidades, list_admin_publicidades, update_publicidad, delete_publicidad
from app.schemas.dto import PublicidadInput
from uuid import uuid4

def test_publicidad_flow():
    db = SessionLocal()
    try:
        # Find a product if any
        product = db.query(Producto).filter(Producto.eliminado_at.is_(None)).first()
        prod_id = product.id if product else None
        print(f"Producto encontrado para asociar: {product.nombre if product else 'Ninguno'}")

        # 1. Crear publicidad
        input_data = PublicidadInput(
            producto_id=prod_id,
            titulo="🚚 DESPACHO PRIORITARIO SANTIAGO",
            subtitulo="Asegura la entrega de tus pedidos en tiempo récord para tu negocio.",
            etiqueta_1="✨ 🚚 LOGÍSTICA EXPRESS",
            etiqueta_roja="OFERTA",
            texto_boton="Aprovechar Beneficio →",
            color_fondo="#082620",
            orden=1,
        )

        admin_mock = ("admin_id", "Administrador")
        created = create_publicidad(input_data, db, admin_mock)
        print(f"[OK] Publicidad creada con ID: {created.id}, Titulo: {created.titulo}")
        assert created.titulo == "🚚 DESPACHO PRIORITARIO SANTIAGO"

        # 2. Listar públicas
        public_list = list_public_publicidades(db)
        print(f"[OK] Listado publico tiene {len(public_list)} publicidades")
        assert any(p.id == created.id for p in public_list)

        # 3. Listar admin
        admin_list = list_admin_publicidades(db, admin_mock)
        print(f"[OK] Listado admin tiene {len(admin_list)} publicidades")
        assert any(p.id == created.id for p in admin_list)

        # 4. Actualizar publicidad
        update_data = PublicidadInput(
            producto_id=prod_id,
            titulo="🚚 DESPACHO PRIORITARIO ACTUALIZADO",
            subtitulo="Subtítulo editado",
            etiqueta_1="✨ NUEVO TAG",
            etiqueta_roja="SUPER OFERTA",
            texto_boton="Comprar ahora →",
            color_fondo="#0D382E",
            orden=2,
        )
        updated = update_publicidad(created.id, update_data, db, admin_mock)
        print(f"[OK] Publicidad actualizada: {updated.titulo} - {updated.etiqueta_roja}")
        assert updated.titulo == "🚚 DESPACHO PRIORITARIO ACTUALIZADO"
        assert updated.etiqueta_roja == "SUPER OFERTA"

        # 5. Hard delete
        res = delete_publicidad(created.id, db, admin_mock)
        print(f"[OK] Delete resultado: {res}")
        assert db.get(Publicidad, created.id) is None
        public_list_after = list_public_publicidades(db)
        assert not any(p.id == created.id for p in public_list_after)
        print("[OK] Verificado: La publicidad fue eliminada de la base de datos.")

        print("\n>>> TODAS LAS PRUEBAS DE PUBLICIDAD PASARON CORRECTAMENTE. <<<")
    finally:
        db.close()

if __name__ == "__main__":
    test_publicidad_flow()
