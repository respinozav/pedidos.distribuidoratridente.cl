from fastapi import APIRouter

from app.api.dependencies import AdminUser, DatabaseSession
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.schemas.system_settings import (
    SystemSettingsResponse,
    SystemSettingsUpdate,
    TestEmailRequest,
    TestEmailResponse,
)
from app.services.notifications import send_test_email

router = APIRouter(prefix="/settings", tags=["Ajustes del Sistema"])
repo = SystemSettingsRepository()


@router.get("", response_model=SystemSettingsResponse)
@router.get("/", response_model=SystemSettingsResponse, include_in_schema=False)
def get_system_settings(database: DatabaseSession, _: AdminUser):
    return repo.get_settings(database)


@router.put("", response_model=SystemSettingsResponse)
@router.put("/", response_model=SystemSettingsResponse, include_in_schema=False)
def update_system_settings(
    settings_in: SystemSettingsUpdate,
    database: DatabaseSession,
    _: AdminUser,
):
    return repo.update_settings(database, settings_in)


@router.post("/test-email", response_model=TestEmailResponse)
def test_email_sending(
    payload: TestEmailRequest,
    database: DatabaseSession,
    _: AdminUser,
):
    overrides = {
        "smtp_host": payload.smtp_host,
        "smtp_port": payload.smtp_port,
        "smtp_username": payload.smtp_username,
        "smtp_password": payload.smtp_password,
        "smtp_from_email": payload.smtp_from_email,
        "smtp_from_name": payload.smtp_from_name,
    }
    result = send_test_email(
        recipient=payload.recipient,
        database=database,
        subject=payload.subject,
        body_text=payload.body_text,
        body_html=payload.body_html,
        smtp_overrides=overrides,
    )
    return TestEmailResponse(
        success=result.get("success", True),
        message=result.get("message", "Correo de prueba enviado."),
        recipient=result.get("recipient", payload.recipient),
    )

