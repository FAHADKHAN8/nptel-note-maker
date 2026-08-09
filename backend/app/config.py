from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "NPTEL AI Notes Generator"
    database_url: str = "sqlite:///./nptel_notes.db"
    gemini_api_key: str = ""
    gemini_model: str = ""
    gemini_request_timeout: int = 120
    gemini_max_retries: int = 3
    gemini_max_concurrency: int = 1
    caption_service_url: str = "http://caption-service:3001"
    caption_service_timeout: int = 60
    backend_cors_origins: str = "http://localhost:5173"
    export_directory: str = "./exports"
    transcript_chunk_size: int = 12000
    transcript_chunk_overlap: int = 500
    scraper_request_delay: float = 1.0
    scraper_timeout: int = 30
    rate_limit_per_minute: int = 12

    @field_validator("gemini_model")
    @classmethod
    def require_model_when_key_set(cls, value: str, info):
        if info.data.get("gemini_api_key") and not value:
            raise ValueError("GEMINI_MODEL is required when GEMINI_API_KEY is set")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
