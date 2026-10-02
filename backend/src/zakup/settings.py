from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Barcha konfiguratsiya — muhit o'zgaruvchilari / .env orqali (12-factor)."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ZAKUP_", extra="ignore")

    env: Literal["local", "test", "production"] = "local"
    debug: bool = False

    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://postgres@127.0.0.1:5432/zakup"),
    )
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_statement_timeout_ms: int = 5_000

    telegram_bot_token: SecretStr = SecretStr("")
    telegram_init_data_ttl_s: int = 3_600
    # Faqat local: Telegram'siz brauzerda ishlash uchun — production'da taqiqlangan
    dev_auth_bypass: bool = False

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.env == "production" and settings.dev_auth_bypass:
        raise RuntimeError("ZAKUP_DEV_AUTH_BYPASS production'da yoqilishi mumkin emas")
    return settings
