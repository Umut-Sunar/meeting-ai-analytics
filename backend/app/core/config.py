from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = Field(...)

    # Redis
    REDIS_URL: str = Field(...)
    REDIS_PASSWORD: str = Field(default="")
    REDIS_REQUIRED: bool = Field(default=True)

    # Storage
    MINIO_ENDPOINT: str = Field(...)
    MINIO_ACCESS_KEY: str = Field(...)
    MINIO_SECRET_KEY: str = Field(...)
    MINIO_SECURE: bool = Field(default=False)

    # File
    MAX_UPLOAD_SIZE: int = Field(default=100 * 1024 * 1024)
    MULTIPART_CHUNK_SIZE: int = Field(default=5 * 1024 * 1024)
    PRESIGNED_URL_EXPIRE_SECONDS: int = Field(default=3600)

    # Security
    SECRET_KEY: str = Field(...)
    JWT_AUDIENCE: str = Field(...)
    JWT_ISSUER: str = Field(...)
    JWT_PUBLIC_KEY_PATH: str = Field(...)

    # Realtime/WS
    MAX_WS_CLIENTS_PER_MEETING: int = Field(default=20)
    MAX_INGEST_MSG_BYTES: int = Field(default=32768)
    INGEST_SAMPLE_RATE: int = Field(default=16000)
    INGEST_CHANNELS: int = Field(default=1)

    # Deepgram
    DEEPGRAM_API_KEY: str = Field(...)
    DEEPGRAM_MODEL: str = Field(default="nova-2")
    DEEPGRAM_LANGUAGE: str = Field(default="tr")
    DEEPGRAM_ENDPOINT: str = Field(default="wss://api.deepgram.com/v1/listen")

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()