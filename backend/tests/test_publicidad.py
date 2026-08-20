from uuid import uuid4
from datetime import datetime, timezone
from app.models.entities import Producto, Publicidad
from app.schemas.dto import PublicidadInput, PublicidadOutput
from app.controllers.routes import (
    create_publicidad,
    list_public_publicidades,
    list_admin_publicidades,
    update_publicidad,
    delete_publicidad,
)
from app.core.database import SessionLocal


def test_publicidad_crud_cycle():
    db = SessionLocal()
    try:
        product = db.query(Producto).filter(Producto.eliminado_at.is_(None)).first()
        prod_id = product.id if product else None

        # 1. Create
        payload = PublicidadInput(
            producto_id=prod_id,
            titulo="BANNER TEST SUITE",
            subtitulo="Subtitulo test suite",
            etiqueta_1="TAG TEST 1",
            etiqueta_roja="PROMO TEST",
            texto_boton="Aprovechar Beneficio →",
            color_fondo="#112233",
            orden=99,
        )
        admin_mock = ("admin_uuid", "Administrador")
        created = create_publicidad(payload, db, admin_mock)
        assert created.id is not None
        assert created.titulo == "BANNER TEST SUITE"
        assert created.etiqueta_roja == "PROMO TEST"
        if prod_id:
            assert created.producto is not None
            assert created.producto.id == prod_id

        # 2. List public & admin
        public_list = list_public_publicidades(db)
        admin_list = list_admin_publicidades(db, admin_mock)
        assert any(p.id == created.id for p in public_list)
        assert any(p.id == created.id for p in admin_list)

        # 3. Update
        update_payload = PublicidadInput(
            producto_id=prod_id,
            titulo="BANNER TEST SUITE UPDATED",
            subtitulo="Subtitulo test suite modificado",
            etiqueta_1="TAG TEST 1 MOD",
            etiqueta_roja="NUEVA PROMO",
            texto_boton="Comprar Ya",
            color_fondo="#445566",
            orden=1,
        )
        updated = update_publicidad(created.id, update_payload, db, admin_mock)
        assert updated.titulo == "BANNER TEST SUITE UPDATED"
        assert updated.color_fondo == "#445566"

        # 4. Hard Delete
        res = delete_publicidad(created.id, db, admin_mock)
        assert res.get("message") == "Publicidad eliminada correctamente"

        # Verify not in DB and not in lists
        assert db.get(Publicidad, created.id) is None
        public_list_after = list_public_publicidades(db)
        assert not any(p.id == created.id for p in public_list_after)
        admin_list_after = list_admin_publicidades(db, admin_mock)
        assert not any(p.id == created.id for p in admin_list_after)

        print("[OK] test_publicidad_crud_cycle passed")
    finally:
        db.close()
