"""Worker configuration settings."""

import os
import uuid

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Worker configuration loaded from environment variables."""

    # Database
    database_url: str = "postgresql://slide2anki:slide2anki@localhost:5432/slide2anki"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "slide2anki"
    minio_secure: bool = False

    # LLM Configuration
    openai_api_key: str | None = None
    google_api_key: str | None = None
    xai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Worker Configuration
    worker_id: str = os.getenv("HOSTNAME", str(uuid.uuid4())[:8])
    worker_concurrency: int = 2
    log_level: str = "INFO"

    # Pipeline Configuration
    # Use holistic pipeline (recommended) for higher quality document processing
    # Set to False to use legacy per-slide extraction pipeline
    use_holistic_pipeline: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
