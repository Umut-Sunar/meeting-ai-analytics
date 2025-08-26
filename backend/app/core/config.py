from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(...)

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage (optional placeholders)
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False

    # File
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    MULTIPART_CHUNK_SIZE: int = 5 * 1024 * 1024
    PRESIGNED_URL_EXPIRE_SECONDS: int = 3600

    # Security
    SECRET_KEY: str = "dev-only-change"
    JWT_AUDIENCE: str = "meetings"
    JWT_ISSUER: str = "our-app"
    JWT_PUBLIC_KEY_PATH: str = "./keys/jwt.pub"

    # Realtime/WS
    MAX_WS_CLIENTS_PER_MEETING: int = 20
    MAX_INGEST_MSG_BYTES: int = 32768
    INGEST_SAMPLE_RATE: int = 48000
    INGEST_CHANNELS: int = 1

    # Deepgram
    DEEPGRAM_API_KEY: str = ""
    DEEPGRAM_MODEL: str = "nova-2"
    DEEPGRAM_LANGUAGE: str = "tr"
    DEEPGRAM_ENDPOINT: str = "wss://api.deepgram.com/v1/listen"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()