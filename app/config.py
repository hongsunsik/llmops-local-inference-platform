from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ollama_base_url: str = "http://127.0.0.1:11434"
    default_model: str = "qwen3:8b"
    coder_model: str = "qwen3-coder:30b"
    fallback_model: str = "glm-4.7-flash:latest"
    request_timeout_seconds: float = 120.0
    max_concurrent_requests: int = 4


@lru_cache
def get_settings() -> Settings:
    return Settings()
