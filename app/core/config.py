from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    SECRET_KEY: str = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    DATABASE_URL: str

    AZURE_AI_FOUNDRY_ENDPOINT: str = ""
    AZURE_AI_FOUNDRY_API_KEY: str = ""
    AZURE_CHAT_DEPLOYMENT: str = "gpt-4o"
    AZURE_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    AZURE_IMAGE_EDIT_DEPLOYMENT: str = ""
    AZURE_IMAGE_GEN_DEPLOYMENT: str = ""

    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = ["http://localhost:3000"]

    RATE_LIMIT_PER_MINUTE: int = 60
    CHAT_RATE_LIMIT_PER_MINUTE: int = 20
    IMAGE_GEN_RATE_LIMIT_PER_HOUR: int = 10
    UPLOAD_RATE_LIMIT_PER_HOUR: int = 30

    MAX_IMAGE_BYTES: int = 5 * 1024 * 1024
    MAX_REQUEST_BYTES: int = 8 * 1024 * 1024

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def ai_configured(self) -> bool:
        return bool(self.AZURE_AI_FOUNDRY_ENDPOINT and self.AZURE_AI_FOUNDRY_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()
