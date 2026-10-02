import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import create_customer_access_token, hash_password
from app.main import app
from app.models.entities import AvisoStockCliente, Categoria, Cliente, LogCorreo, Producto
from app.services.stock_notifications import (
    obtener_avisos_pendientes_cliente,
    procesar_avisos_stock_disponible,
    registrar_aviso_stock,
)


def run_tests():
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 1. Crear categoría y cliente de prueba
        test_cat = Categoria(
            nombre=f"CAT_STOCK_{uuid.uuid4().hex[:6]}",
            comision_porcentaje=Decimal("0.00"),
            activo=True,
        )
        db.add(test_cat)
        db.flush()

        test_client = Cliente(
            nombre="Cliente Prueba Stock",
            rut=f"99{uuid.uuid4().hex[:6]}",
            correo=f"test_stock_{uuid.uuid4().hex[:6]}@example.com",
            password_hash=hash_password("password123"),
            activo=True,
        )
        db.add(test_client)
        db.flush()

        # 2. Crear producto SIN stock (cantidad = 0)
        test_prod = Producto(
            categoria_id=test_cat.id,
            codigo=f"SKU_{uuid.uuid4().hex[:6]}",
            nombre="Café Molido Gourmet Test",
            precio=Decimal("4990.00"),
            cantidad=0,
            activo=True,
        )
        db.add(test_prod)
        db.commit()

        # 3. Registrar aviso de reposición de stock
        aviso = registrar_aviso_stock(
            database=db,
            cliente_id=test_client.id,
            producto_id=test_prod.id,
            correo="cliente_notif@example.com",
        )
        assert aviso.estado == "PENDIENTE"
        assert aviso.correo == "cliente_notif@example.com"

        # 4. Verificar que aparece en pendientes
        pendientes = obtener_avisos_pendientes_cliente(db, test_client.id)
        assert test_prod.id in pendientes

        # 5. Ejecutar evaluación cuando stock es 0 -> NO debe notificar
        notificados_cero = procesar_avisos_stock_disponible(db, producto_id=test_prod.id)
        assert notificados_cero == 0
        db.refresh(aviso)
        assert aviso.estado == "PENDIENTE"

        # 6. Actualizar stock a exactamente 1 -> Según requerimiento (> 1 en stock), NO debe notificar
        test_prod.cantidad = 1
        db.commit()
        notificados_uno = procesar_avisos_stock_disponible(db, producto_id=test_prod.id)
        assert notificados_uno == 0
        db.refresh(aviso)
        assert aviso.estado == "PENDIENTE"

        # 7. Actualizar stock a 5 (> 1 en stock) -> DEBE notificar automáticamente
        test_prod.cantidad = 5
        db.commit()
        notificados_cinco = procesar_avisos_stock_disponible(db, producto_id=test_prod.id)
        assert notificados_cinco == 1

        db.refresh(aviso)
        assert aviso.estado == "NOTIFICADO"
        assert aviso.notificado_at is not None

        # 8. Verificar que ya no está en pendientes
        pendientes_despues = obtener_avisos_pendientes_cliente(db, test_client.id)
        assert test_prod.id not in pendientes_despues

        # 9. Verificar registro en log_correos
        log_creado = db.scalar(
            select(LogCorreo).where(
                LogCorreo.cliente_id == test_client.id,
                LogCorreo.tipo == "AVISO_STOCK",
            )
        )
        assert log_creado is not None
        assert log_creado.destinatario == "cliente_notif@example.com"

        # 10. Probar API endpoints cliente
        token = create_customer_access_token(test_client.id)
        client = TestClient(app)

        # Crear otro producto sin stock
        prod_api = Producto(
            categoria_id=test_cat.id,
            codigo=f"SKU_API_{uuid.uuid4().hex[:6]}",
            nombre="Té Verde Orgánico",
            precio=Decimal("2990.00"),
            cantidad=0,
            activo=True,
        )
        db.add(prod_api)
        db.commit()

        # POST /api/cliente/avisos-stock
        resp_post = client.post(
            "/api/cliente/avisos-stock",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "producto_id": str(prod_api.id),
                "correo": "cliente_api@example.com",
            },
        )
        assert resp_post.status_code == 200, resp_post.text
        data_post = resp_post.json()
        assert data_post["estado"] == "PENDIENTE"
        assert data_post["correo"] == "cliente_api@example.com"

        # GET /api/cliente/avisos-stock/pendientes
        resp_get = client.get(
            "/api/cliente/avisos-stock/pendientes",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp_get.status_code == 200, resp_get.text
        data_get = resp_get.json()
        assert str(prod_api.id) in data_get

        print("¡Todas las pruebas de Avisos de Stock pasaron EXITOSAMENTE!")
    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
