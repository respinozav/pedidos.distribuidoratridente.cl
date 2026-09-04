from typing import Optional
from pydantic import BaseModel, ConfigDict


class SystemSettingsBase(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    whatsapp_enabled: bool = False
    whatsapp_api_key: Optional[str] = None
    whatsapp_phone_number: Optional[str] = None
    jwt_access_token_expire_minutes: Optional[int] = 60
    timezone: Optional[str] = "America/Santiago"


class SystemSettingsUpdate(SystemSettingsBase):
    pass


class SystemSettingsResponse(SystemSettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TestEmailRequest(BaseModel):
    recipient: str
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None


class TestEmailResponse(BaseModel):
    success: bool
    message: str
    recipient: str

