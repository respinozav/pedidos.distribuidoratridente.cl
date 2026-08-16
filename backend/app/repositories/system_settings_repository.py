from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.system_settings import SystemSettings
from app.schemas.system_settings import SystemSettingsUpdate


class SystemSettingsRepository:
    def get_settings(self, db: Session) -> SystemSettings:
        settings = db.query(SystemSettings).filter(SystemSettings.id == 1).first()
        if not settings:
            env_config = get_settings()
            settings = SystemSettings(
                id=1,
                smtp_host=env_config.smtp_host or None,
                smtp_port=env_config.smtp_port or None,
                smtp_username=env_config.smtp_username or None,
                smtp_password=env_config.smtp_password or None,
                smtp_from_email=env_config.smtp_from_email or None,
                smtp_from_name=env_config.smtp_from_name or "Distribuidora Tridente",
                whatsapp_enabled=False,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    def update_settings(self, db: Session, settings_data: SystemSettingsUpdate) -> SystemSettings:
        settings = self.get_settings(db)

        for key, value in settings_data.model_dump(exclude_unset=True).items():
            setattr(settings, key, value)

        db.commit()
        db.refresh(settings)
        return settings
