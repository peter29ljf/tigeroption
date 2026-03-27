from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres
    database_url: str = "postgresql+asyncpg://optionflow:changeme_db_password@localhost:5432/optionflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Tiger OpenAPI
    tiger_id: str = ""
    tiger_account: str = ""
    tiger_private_key_path: str = ""
    tiger_license: str = "TBNZ"

    # Claude AI
    anthropic_api_key: str = ""

    # WeChat
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_template_id: str = ""

    # JWT Auth
    jwt_secret: str = "changeme_jwt_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # App
    watchlist: str = "NVDA,AAPL,TSLA,SPY,QQQ,AMZN,MSFT,META,GOOGL,AMD"
    premium_threshold_cents: int = 10_000_000  # $10万 = 10,000,000 cents
    usd_cny_rate: float = 7.25
    log_level: str = "INFO"

    @property
    def watchlist_symbols(self) -> list[str]:
        return [s.strip() for s in self.watchlist.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
