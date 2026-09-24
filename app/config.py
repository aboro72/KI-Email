from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KI-Email"
    database_url: str = "sqlite:///./ki_email.db"
    secret_key: str = "development-only-change-me"
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-now"
    session_cookie_secure: bool = False
    bedrock_region: str = "eu-central-1"
    # Diese Adresse muss exakt in Google Cloud als Redirect URI eingetragen sein.
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
