from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "postgres"
    database_schema: str = "bdtridente"
    database_user: str = "postgres"
    database_password: str = "postgres"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5175,http://127.0.0.1:5175"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Distribuidora Tridente"
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_global_key: str = "tridente_global_secret_123"
    whatsapp_instance_name: str = "tridente_ws"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
    )

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.database_user,
            password=self.database_password,
            host=self.database_host,
            port=self.database_port,
            database=self.database_name,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_username and self.smtp_password and self.smtp_from_email)


@lru_cache
def get_settings() -> Settings:
    return Settings()
