from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://mattilda:mattilda_secret@localhost:5432/mattilda_db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    api_v1_prefix: str = "/api/v1"
    project_name: str = "Mattilda Backend"
    project_version: str = "1.0.0"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 minutes

    # JWT Auth
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
