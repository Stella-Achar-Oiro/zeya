import logging
import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Antenatal Education Chatbot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/antenatal_chatbot"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # WhatsApp
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # JWT Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Rate Limiting
    RATE_LIMIT: str = "100/minute"

    # Sentry
    SENTRY_DSN: Optional[str] = None

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }

    @model_validator(mode="after")
    def validate_required_secrets(self):
        if self.DEBUG:
            return self

        missing = []
        if not self.WHATSAPP_ACCESS_TOKEN:
            missing.append("WHATSAPP_ACCESS_TOKEN")
        if not self.WHATSAPP_PHONE_NUMBER_ID:
            missing.append("WHATSAPP_PHONE_NUMBER_ID")
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")

        if missing:
            raise ValueError(
                f"Missing required secrets for production: {', '.join(missing)}. "
                "Set these in your .env file or set DEBUG=true for development."
            )

        if self.JWT_SECRET_KEY == "change-me-in-production":
            warnings.warn(
                "JWT_SECRET_KEY is using the default value. "
                "Set a strong random secret in your .env file.",
                stacklevel=2,
            )

        return self


settings = Settings()
