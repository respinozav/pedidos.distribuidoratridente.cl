from fastapi import APIRouter
from app.api.dependencies import AdminUser
from app.services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])
ws_service = WhatsAppService()


@router.get("/status")
async def get_whatsapp_status(_: AdminUser):
    return await ws_service.get_instance_state()


@router.get("/qr")
async def get_whatsapp_qr(_: AdminUser):
    return await ws_service.create_and_get_qr()
