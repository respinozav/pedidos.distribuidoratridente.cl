from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # SMTP Settings
    smtp_host: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_username: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_password: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_from_email: Mapped[str | None] = mapped_column(String, nullable=True)
    smtp_from_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # WhatsApp Settings (Preparado para el futuro)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    whatsapp_phone_number: Mapped[str | None] = mapped_column(String, nullable=True)
