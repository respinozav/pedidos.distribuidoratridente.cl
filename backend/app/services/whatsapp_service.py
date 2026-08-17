import base64
import logging
import httpx
from fastapi import HTTPException
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def format_whatsapp_phone(phone: str) -> str:
    """Limpia y estandariza el número de teléfono con código de país."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return ""
    # Si es número móvil chileno de 9 dígitos (ej. 912345678), agregar 56
    if len(digits) == 9 and digits.startswith("9"):
        return f"56{digits}"
    # Si viene con 8 dígitos sin el 9 (ej. 12345678), agregar 569
    if len(digits) == 8:
        return f"569{digits}"
    return digits


class WhatsAppService:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.evolution_api_url.rstrip("/")
        self.headers = {
            "apikey": settings.evolution_api_global_key,
            "Content-Type": "application/json",
        }
        self.instance_name = settings.whatsapp_instance_name

    async def get_instance_state(self) -> dict:
        """Verifica si la instancia está conectada."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/instance/connectionState/{self.instance_name}",
                    headers=self.headers,
                )
                if response.status_code == 200:
                    return response.json()
                return {"instance": {"state": "DISCONNECTED"}}
            except Exception:
                logger.warning("No se pudo conectar a Evolution API en %s", self.base_url)
                return {"instance": {"state": "ERROR_API_DOWN"}}

    async def create_and_get_qr(self) -> dict:
        """Crea la instancia si no existe y devuelve el QR en base64."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                create_payload = {
                    "instanceName": self.instance_name,
                    "integration": "WHATSAPP-BAILEYS",
                }
                try:
                    await client.post(
                        f"{self.base_url}/instance/create",
                        json=create_payload,
                        headers=self.headers,
                    )
                except Exception:
                    pass

                response = await client.get(
                    f"{self.base_url}/instance/connect/{self.instance_name}",
                    headers=self.headers,
                )

                if response.status_code in (200, 201):
                    data = response.json()
                    qr_code = data.get("base64") or (
                        data.get("qrcode", {}).get("base64")
                        if isinstance(data.get("qrcode"), dict)
                        else None
                    )
                    return {
                        "qr_code": qr_code,
                        "state": "QR_READY" if qr_code else data.get("instance", {}).get("state", "CONNECTED"),
                    }

                raise HTTPException(status_code=500, detail="No se pudo generar el QR de WhatsApp")
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Error al comunicarse con Evolution API")
                raise HTTPException(status_code=503, detail=f"Evolution API no disponible ({str(e)})")

    def send_message_sync(self, phone: str, text: str) -> dict:
        """Envía un mensaje de texto síncrono."""
        clean_phone = format_whatsapp_phone(phone)
        if not clean_phone:
            return {"status": "ERROR", "message": "Número telefónico inválido"}
        with httpx.Client(timeout=15.0) as client:
            payload = {
                "number": clean_phone,
                "text": text,
                "delay": 1200,
            }
            response = client.post(
                f"{self.base_url}/message/sendText/{self.instance_name}",
                json=payload,
                headers=self.headers,
            )
            return response.json()

    def send_pdf_document_sync(self, phone: str, pdf_bytes: bytes, filename: str, caption: str = "") -> dict:
        """Envía un documento PDF adjunto con mensaje/caption."""
        clean_phone = format_whatsapp_phone(phone)
        if not clean_phone:
            return {"status": "ERROR", "message": "Número telefónico inválido"}
        base64_media = base64.b64encode(pdf_bytes).decode("utf-8")
        with httpx.Client(timeout=25.0) as client:
            payload = {
                "number": clean_phone,
                "mediatype": "document",
                "mimetype": "application/pdf",
                "caption": caption,
                "media": base64_media,
                "fileName": filename,
            }
            response = client.post(
                f"{self.base_url}/message/sendMedia/{self.instance_name}",
                json=payload,
                headers=self.headers,
            )
            if response.status_code in (200, 201):
                return response.json()
            # Si falla el envío de media, intentar enviar como texto de respaldo
            logger.warning(
                "Fallo al enviar PDF por WhatsApp (status %s). Enviando texto de respaldo.",
                response.status_code,
            )
            return self.send_message_sync(clean_phone, caption)

    async def send_message(self, phone: str, text: str) -> dict:
        """Envía un mensaje de texto asíncrono."""
        clean_phone = format_whatsapp_phone(phone)
        if not clean_phone:
            return {"status": "ERROR", "message": "Número telefónico inválido"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "number": clean_phone,
                "text": text,
                "delay": 1200,
            }
            response = await client.post(
                f"{self.base_url}/message/sendText/{self.instance_name}",
                json=payload,
                headers=self.headers,
            )
            return response.json()

