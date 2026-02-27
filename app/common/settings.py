from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    mongo_uri: str
    minio_url: str
    minio_username: str
    minio_password: str
    redis_host: str
    redis_port: int
    redis_password: str
    redis_task_queue_name: str

    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
