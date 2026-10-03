from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "ComicCraft"

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # Hugging Face
    hf_api_key: str = ""
    image_model: str = "stabilityai/stable-diffusion-2-1"
    hf_image_model: Optional[str] = None
    hf_image_provider: str | None = None
    image_provider: str = "auto"

    # Comic
    panels_count: int = 5

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    # AI timeout
    model_timeout_seconds: int = 180

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()