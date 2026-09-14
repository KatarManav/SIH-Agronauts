from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "LandslideGuard NER API"
    app_version: str = "0.1.0"
    database_url: str = Field(
        validation_alias=AliasChoices("SUPABASE_DATABASE_URL", "DATABASE_URL")
    )
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    auto_create_tables: bool = False
    h3_resolution: int = Field(default=7, ge=0, le=15)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError(
                "SUPABASE_DATABASE_URL must be a PostgreSQL connection URI, "
                "not the Supabase project HTTPS URL"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
