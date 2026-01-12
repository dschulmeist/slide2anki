from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = (
        "postgresql+asyncpg://slide2anki:slide2anki@localhost:5432/slide2anki"
    )

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "slide2anki"
    minio_secure: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    # CORS - accepts comma-separated origins or "*" for allow-all
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_all: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
