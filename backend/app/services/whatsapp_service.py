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
        """Verifica si la instancia está conectada y obtiene los datos del número vinculado."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/instance/connectionState/{self.instance_name}",
                    headers=self.headers,
                )
                state = "DISCONNECTED"
                if response.status_code == 200:
                    state_data = response.json()
                    state = (
                        state_data.get("instance", {}).get("state")
                        or state_data.get("state")
                        or "DISCONNECTED"
                    )

                profile_name = None
                owner_number = None
                profile_pic_url = None

                if state in ("open", "CONNECTED"):
                    try:
                        inst_resp = await client.get(
                            f"{self.base_url}/instance/fetchInstances",
                            params={"instanceName": self.instance_name},
                            headers=self.headers,
                        )
                        if inst_resp.status_code == 200:
                            data = inst_resp.json()
                            instances = data if isinstance(data, list) else data.get("instances", [])
                            target = next(
                                (i for i in instances if i.get("name") == self.instance_name or i.get("instanceName") == self.instance_name),
                                instances[0] if instances else None
                            )
                            if target:
                                owner_jid = target.get("ownerJid") or target.get("owner") or target.get("wuid") or ""
                                raw_phone = owner_jid.split("@")[0] if "@" in owner_jid else owner_jid
                                if raw_phone:
                                    owner_number = f"+{raw_phone}" if not raw_phone.startswith("+") else raw_phone
                                profile_name = target.get("profileName") or target.get("name")
                                profile_pic_url = target.get("profilePicUrl")
                    except Exception:
                        pass

                return {
                    "instance": {
                        "instanceName": self.instance_name,
                        "state": state,
                        "phone_number": owner_number,
                        "profile_name": profile_name,
                        "profile_pic_url": profile_pic_url,
                    }
                }
            except Exception:
                logger.warning("No se pudo conectar a Evolution API en %s", self.base_url)
                return {"instance": {"state": "ERROR_API_DOWN"}}

    def get_instance_state_sync(self) -> dict:
        """Verifica si la instancia está conectada de manera síncrona."""
        with httpx.Client(timeout=8.0) as client:
            try:
                response = client.get(
                    f"{self.base_url}/instance/connectionState/{self.instance_name}",
                    headers=self.headers,
                )
                if response.status_code == 200:
                    return response.json()
                return {"instance": {"state": "DISCONNECTED"}}
            except Exception:
                logger.warning("No se pudo conectar a Evolution API en %s", self.base_url)
                return {"instance": {"state": "ERROR_API_DOWN"}}

    def is_connected_sync(self) -> bool:
        """Indica si WhatsApp está realmente vinculado y listo para enviar mensajes."""
        try:
            state_data = self.get_instance_state_sync()
            state = (
                state_data.get("instance", {}).get("state")
                or state_data.get("state")
                or ""
            )
            return state.lower() in ("open", "connected")
        except Exception:
            return False

    async def logout_instance(self) -> dict:
        """Desvincula y cierra la sesión de WhatsApp en Evolution API."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.delete(
                    f"{self.base_url}/instance/logout/{self.instance_name}",
                    headers=self.headers,
                )
                return {
                    "status": "SUCCESS",
                    "message": "Dispositivo desvinculado correctamente",
                    "code": response.status_code,
                }
            except Exception as e:
                logger.exception("Error al desvincular dispositivo en Evolution API")
                raise HTTPException(status_code=500, detail=f"No se pudo desvincular: {str(e)}")


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
            try:
                data = response.json()
                logger.info("Resultado sendText WhatsApp (%s): %s", response.status_code, data)
                return data
            except Exception:
                logger.warning("Respuesta sendText WhatsApp (%s): %s", response.status_code, response.text)
                return {"status": response.status_code, "text": response.text}

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
                try:
                    return response.json()
                except Exception:
                    return {"status": "SUCCESS"}
            # Si falla el envío de media, intentar enviar como texto de respaldo
            logger.warning(
                "Fallo al enviar PDF por WhatsApp (status %s, resp: %s). Enviando texto de respaldo.",
                response.status_code,
                response.text,
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

