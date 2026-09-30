from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AboroDesk Developer"
    environment: str = "development"
    database_url: str = "sqlite:///./ki_email.db"
    secret_key: str = "development-only-change-me"
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-now"
    session_cookie_secure: bool = False
    max_attachment_bytes: int = 10 * 1024 * 1024
    max_attachment_count: int = 10
    max_total_attachment_bytes: int = 25 * 1024 * 1024
    bedrock_region: str = "eu-central-1"
    bedrock_model_id: str = "eu.anthropic.claude-sonnet-4-6"
    bedrock_api_key_file: str = "bedrock-long-term-api-key.csv"
    update_status_file: str = "/var/lib/aborodesk-updater/status.json"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
