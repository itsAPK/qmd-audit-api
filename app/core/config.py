import secrets
from typing import List

from pydantic import  EmailStr
from pydantic_settings import BaseSettings
from app.core.enums import LogLevel


class Settings(BaseSettings):
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = []
    UVICORN_HOST: str
    UVICORN_PORT: int
    USE_CORRELATION_ID: bool
    LOG_LEVEL: str
    DATABASE_URL: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int# 60 minutes * 24 hours * 1 = 1 day
    SECRET_KEY: str
    RESET_TOKEN_EXPIRE_MINUTES: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: EmailStr | None = None
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_FROM_NAME: str
    FRONTEND_URL: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()  # type: ignore[call-arg]
