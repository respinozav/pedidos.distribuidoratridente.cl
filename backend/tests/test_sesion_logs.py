from uuid import uuid4
from fastapi import HTTPException
from app.models.entities import SesionLog, Usuario, Cliente, Rol
from app.schemas.dto import UserLogin, CustomerLogin
from app.controllers.routes import (
    login,
    customer_login,
    record_session_log,
    list_session_logs,
    session_logs_stats,
)
from app.core.database import SessionLocal
from app.core.security import hash_password


class MockRequest:
    def __init__(self, ip="192.168.1.100", user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestSuite/1.0"):
        self.headers = {
            "x-forwarded-for": ip,
            "user-agent": user_agent,
        }
        self.client = None


def test_session_logs_recording_and_queries():
    db = SessionLocal()
    try:
        req = MockRequest(ip="200.50.100.25", user_agent="Mozilla/5.0 (TridenteTestAgent)")
        admin_mock = ("admin_uuid", "Administrador")

        # 1. Test direct log recording
        log = record_session_log(
            database=db,
            tipo_usuario="ADMINISTRADOR",
            correo="auditoria_directa@tridente.cl",
            estado="EXITOSO",
            mensaje="Inicio directo de prueba",
            nombre="Tester Directo",
            ip_address="200.50.100.25",
            user_agent="Mozilla/5.0 (TridenteTestAgent)",
        )
        assert log.id is not None
        assert log.tipo_usuario == "ADMINISTRADOR"
        assert log.estado == "EXITOSO"

        # 2. Test failed login - non existent admin
        try:
            login(
                payload=UserLogin(correo="no_existe_admin_xyz@tridente.cl", password="Password123!"),
                request=req,
                database=db,
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 401

        # Verify failed log was created in DB
        failed_admin_log = (
            db.query(SesionLog)
            .filter(SesionLog.correo == "no_existe_admin_xyz@tridente.cl")
            .order_by(SesionLog.created_at.desc())
            .first()
        )
        assert failed_admin_log is not None
        assert failed_admin_log.estado == "FALLIDO"
        assert failed_admin_log.mensaje == "Usuario no encontrado"
        assert failed_admin_log.ip_address == "200.50.100.25"
        assert failed_admin_log.user_agent == "Mozilla/5.0 (TridenteTestAgent)"

        # 3. Test failed customer login - non existent customer
        try:
            customer_login(
                payload=CustomerLogin(correo="no_existe_cliente_xyz@tridente.cl", password="Password123!"),
                request=req,
                database=db,
            )
            assert False, "Should have raised HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 401

        failed_customer_log = (
            db.query(SesionLog)
            .filter(SesionLog.correo == "no_existe_cliente_xyz@tridente.cl")
            .order_by(SesionLog.created_at.desc())
            .first()
        )
        assert failed_customer_log is not None
        assert failed_customer_log.estado == "FALLIDO"
        assert failed_customer_log.tipo_usuario == "CLIENTE"
        assert failed_customer_log.mensaje == "Cliente no encontrado"

        # 4. Test list_session_logs endpoint
        logs_page = list_session_logs(
            database=db,
            _=admin_mock,
            search="no_existe_admin_xyz",
            page=1,
            page_size=10,
        )
        assert logs_page.total >= 1
        assert any(item.correo == "no_existe_admin_xyz@tridente.cl" for item in logs_page.items)

        # 5. Test session_logs_stats endpoint
        stats = session_logs_stats(database=db, _=admin_mock)
        assert stats.total >= 3
        assert stats.fallidos >= 2
        assert stats.exitosos >= 1
        assert stats.admin_total >= 2
        assert stats.cliente_total >= 1

        print("[OK] test_session_logs_recording_and_queries passed")
    finally:
        # Clean up test logs
        db.query(SesionLog).filter(
            SesionLog.correo.in_([
                "auditoria_directa@tridente.cl",
                "no_existe_admin_xyz@tridente.cl",
                "no_existe_cliente_xyz@tridente.cl",
            ])
        ).delete(synchronize_session=False)
        db.commit()
        db.close()
