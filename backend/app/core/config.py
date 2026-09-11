from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Label Police Backend"
    API_V1_STR: str = "/api/v1"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    DATABASE_URL: str = "sqlite:///./label_police.db"
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENAI_VISION_MODEL: str = "gpt-4o-mini"
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it:free"
    OPENROUTER_SITE_URL: Optional[str] = None
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if value is None or value == "":
            return ["*"]
        if isinstance(value, list):
            return value or ["*"]
        text = str(value).strip()
        if text.startswith("["):
            import json

            try:
                parsed = json.loads(text)
                if isinstance(parsed, list) and parsed:
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in text.split(",") if part.strip()] or ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def sanitize_database_url(cls, value: Optional[str]) -> str:
        if not value:
            import os
            value = os.environ.get("DATABASE_URL", "sqlite:///./label_police.db")
        text = str(value).strip()
        if text.startswith("postgres://"):
            return "postgresql://" + text[len("postgres://"):]
        return text

    @field_validator("GEMINI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", mode="before")
    @classmethod
    def empty_key_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @property
    def has_vision_provider(self) -> bool:
        return bool(self.OPENROUTER_API_KEY or self.GEMINI_API_KEY or self.OPENAI_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
