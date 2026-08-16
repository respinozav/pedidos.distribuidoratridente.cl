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


class SystemSettingsUpdate(SystemSettingsBase):
    pass


class SystemSettingsResponse(SystemSettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
