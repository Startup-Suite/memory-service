from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_")

    # Embedding
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_device: str = "cuda"

    # Postgres (pgvector)
    database_url: str = "postgresql://memory:memory@localhost:5432/memory"

    # API
    api_key: str | None = None
    host: str = "0.0.0.0"
    port: int = 8100


@lru_cache
def get_settings() -> Settings:
    return Settings()
