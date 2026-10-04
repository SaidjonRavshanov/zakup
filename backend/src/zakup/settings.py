from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "local-dev-only-jwt-secret-change-me-0123456789"  # noqa: S105 — faqat local/test


class IikoServerSettings(BaseModel):
    """Bitta filial iikoRMS serveri. `department_code` — iiko bo'limi kodi (Sebzar=1, Drujba=2, Keles=8, Chorsu=9)."""

    code: str = Field(pattern=r"^[a-z0-9_-]{2,32}$")
    name: str
    base_url: HttpUrl  # ".../resto" — API yo'li shundan keyin: /api/auth
    login: str
    password: SecretStr
    department_code: str | None = None


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
    # Birinchi kirishda avtomatik admin bo'ladigan Telegram ID'lar (JSON: [123456789])
    bootstrap_admin_ids: list[int] = []

    # Access JWT imzosi; production'da majburiy, kamida 32 belgi
    jwt_secret: SecretStr = SecretStr(_DEV_JWT_SECRET)
    access_token_ttl_s: int = 15 * 60
    refresh_token_ttl_s: int = 7 * 24 * 3600

    # iiko: JSON ro'yxat (ZAKUP_IIKO_SERVERS). Har serverga bir vaqtda faqat bitta sessiya (litsenziya, ADR-05)
    iiko_servers: list[IikoServerSettings] = []
    iiko_timeout_s: float = 120.0
    iiko_lock_wait_s: float = 300.0

    # Xarid: tasdiqlash limitlari (so'm; null — cheklanmagan) — anketa javobigacha default (WORKFLOW B5)
    approval_limits: dict[str, Decimal | None] = {
        "buyer": Decimal(2_000_000),
        "approver": Decimal(10_000_000),
        "admin": None,
    }
    # Yetkazuvchi javobida narx dopuski: ±% va (ixtiyoriy) pozitsiya bo'yicha so'm (WORKFLOW B7)
    price_tolerance_pct: Decimal = Decimal(3)
    price_tolerance_abs: Decimal | None = None
    supplier_response_hours: int = 4
    # Yetkazuvchi havolasi: {public_base_url}/s/{token} — Mini App domeni
    public_base_url: str = "http://127.0.0.1:5173"
    company_name: str = "Tarnov"

    # Qabul dopusklari (WORKFLOW B9): vaznli tovar %, donali %, narx oshishi %
    receiving_qty_weight_pct: Decimal = Decimal(3)
    receiving_qty_piece_pct: Decimal = Decimal(0)
    receiving_price_pct: Decimal = Decimal(3)
    # Fayllar (nakladnoy fotosi) — lokal papka; production'da S3
    media_dir: str = "var/media"
    # iiko kirimi: o'tkazilgan holda (Tarnov amaliyoti); nizo bo'lgan qabul — o'tkazilmagan, buxgalter tekshiradi
    iiko_post_invoices: bool = True
    iiko_post_disputed: bool = False

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.env == "production" and settings.dev_auth_bypass:
        raise RuntimeError("ZAKUP_DEV_AUTH_BYPASS production'da yoqilishi mumkin emas")
    if settings.env == "production" and settings.jwt_secret.get_secret_value() == _DEV_JWT_SECRET:
        raise RuntimeError("ZAKUP_JWT_SECRET production'da o'rnatilishi shart")
    return settings
