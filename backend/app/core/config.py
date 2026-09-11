from functools import lru_cache
from typing import Dict, List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

OPTIONAL_SECRET_FIELDS = (
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENROUTER_SITE_URL",
    "AZURE_VISION_KEY",
    "AZURE_VISION_ENDPOINT",
    "GOOGLE_CLOUD_VISION_KEY",
    "OCRSPACE_API_KEY",
    "BARCODE_LOOKUP_API_KEY",
    "TAVILY_API_KEY",
    "SERPAPI_KEY",
)

DEFAULT_VISION_PROVIDER_ORDER = [
    "gemini",
    "openai",
    "anthropic",
    "openrouter",
    "ocrspace",
    "azure",
    "google",
]


class Settings(BaseSettings):
    """Environment-backed application settings. Secrets are never hardcoded."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Label Police Backend"
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    SECRET_KEY: str = "dev-insecure-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    DATABASE_URL: str = "sqlite:///./label_police.db"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    VISION_REQUEST_TIMEOUT_SECONDS: float = 45.0

    # PRIMARY_VISION_AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # FALLBACK_VISION_AI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_VISION_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: str = "google/gemma-4-31b-it:free"
    OPENROUTER_SITE_URL: Optional[str] = None
    VISION_PROVIDER_ORDER: str = "gemini,openai,anthropic,openrouter,azure,google"

    # DEDICATED_OCR
    AZURE_VISION_KEY: Optional[str] = None
    AZURE_VISION_ENDPOINT: Optional[str] = None
    GOOGLE_CLOUD_VISION_KEY: Optional[str] = None
    OCRSPACE_API_KEY: Optional[str] = None

    # PRODUCT_DATABASE_API
    BARCODE_LOOKUP_API_KEY: Optional[str] = None
    OPEN_FOOD_FACTS_URL: str = "https://world.openfoodfacts.org"

    # WEB_VERIFICATION_API
    TAVILY_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None

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

    @field_validator("VISION_PROVIDER_ORDER", mode="before")
    @classmethod
    def parse_provider_order(cls, value: Union[str, List[str], None]) -> str:
        if value is None or value == "":
            return ",".join(DEFAULT_VISION_PROVIDER_ORDER)
        if isinstance(value, list):
            parsed = [str(item).strip().lower() for item in value if str(item).strip()]
            return ",".join(parsed or DEFAULT_VISION_PROVIDER_ORDER)
        return str(value).strip() or ",".join(DEFAULT_VISION_PROVIDER_ORDER)

    @property
    def vision_provider_order_list(self) -> List[str]:
        parsed = [part.strip().lower() for part in self.VISION_PROVIDER_ORDER.split(",") if part.strip()]
        return parsed or list(DEFAULT_VISION_PROVIDER_ORDER)

    @field_validator(*OPTIONAL_SECRET_FIELDS, mode="before")
    @classmethod
    def empty_key_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    def is_gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    def is_openai_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    def is_anthropic_configured(self) -> bool:
        return bool(self.ANTHROPIC_API_KEY)

    def is_openrouter_configured(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    def is_azure_vision_configured(self) -> bool:
        return bool(self.AZURE_VISION_KEY and self.AZURE_VISION_ENDPOINT)

    def is_google_cloud_vision_configured(self) -> bool:
        return bool(self.GOOGLE_CLOUD_VISION_KEY)

    def is_ocrspace_configured(self) -> bool:
        return bool(self.OCRSPACE_API_KEY)

    def is_barcode_lookup_configured(self) -> bool:
        return bool(self.BARCODE_LOOKUP_API_KEY)

    def is_open_food_facts_configured(self) -> bool:
        return bool(self.OPEN_FOOD_FACTS_URL)

    def is_tavily_configured(self) -> bool:
        return bool(self.TAVILY_API_KEY)

    def is_serpapi_configured(self) -> bool:
        return bool(self.SERPAPI_KEY)

    def is_product_database_configured(self) -> bool:
        return self.is_barcode_lookup_configured() or self.is_open_food_facts_configured()

    def is_web_verification_configured(self) -> bool:
        return self.is_tavily_configured() or self.is_serpapi_configured()

    def is_provider_configured(self, provider_id: str) -> bool:
        checks = {
            "gemini": self.is_gemini_configured,
            "openai": self.is_openai_configured,
            "anthropic": self.is_anthropic_configured,
            "openrouter": self.is_openrouter_configured,
            "ocrspace": self.is_ocrspace_configured,
            "azure": self.is_azure_vision_configured,
            "google": self.is_google_cloud_vision_configured,
        }
        checker = checks.get(provider_id.strip().lower())
        return bool(checker and checker())

    def configured_vision_providers(self) -> List[str]:
        return [provider_id for provider_id in self.vision_provider_order_list if self.is_provider_configured(provider_id)]

    @property
    def has_vision_provider(self) -> bool:
        return bool(self.configured_vision_providers())

    def provider_status(self) -> Dict[str, bool]:
        """Booleans only — never include secret values."""
        return {
            "gemini": self.is_gemini_configured(),
            "openai": self.is_openai_configured(),
            "anthropic": self.is_anthropic_configured(),
            "openrouter": self.is_openrouter_configured(),
            "ocrspace": self.is_ocrspace_configured(),
            "azure_vision": self.is_azure_vision_configured(),
            "google_cloud_vision": self.is_google_cloud_vision_configured(),
            "barcode_lookup": self.is_barcode_lookup_configured(),
            "open_food_facts": self.is_open_food_facts_configured(),
            "tavily": self.is_tavily_configured(),
            "serpapi": self.is_serpapi_configured(),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
