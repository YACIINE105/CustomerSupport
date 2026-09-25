from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Customer Support Platform"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    jwt_secret_key: str = Field(default="", repr=False)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    jwt_issuer: str = "customer-support"
    jwt_audience: str = "customer-support-api"

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if value and len(value.encode()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")
        return value

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/customer_support"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
