from fastapi import APIRouter

from app.api.dependencies import AdminUser, DatabaseSession
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.schemas.system_settings import SystemSettingsResponse, SystemSettingsUpdate

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
