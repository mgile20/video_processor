from os import getenv

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

if getenv("environment") == "local_dev":
    secrets_dir = "~/secrets"
else:
    secrets_dir = "/run/secrets"


class Settings(BaseSettings):
    mongo_uri: str
    minio_url: str
    minio_username: str
    minio_password: str
    redis_host: str
    redis_port: int
    redis_password: str
    redis_processing_queue_name: str
    reel_sync_drift_tolerance_ms: float = 40.0
    reel_sync_enable_async_resample: bool = False
    reel_sync_enable_diagnostics: bool = True
    reel_sync_music_offset_seconds: float = 0.0

    model_config = SettingsConfigDict(
        secrets_dir=secrets_dir,
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
