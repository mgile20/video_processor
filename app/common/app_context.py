from threading import Lock
from typing import Optional

from app.common.file_manager import FileManager
from app.common.redis_manager import RedisManager
from app.common.settings import settings
from app.data.motor_manager import MotorClientManager
from app.models.paths_model import PathsModel


class AppContext:
    _instance: Optional["AppContext"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> "AppContext":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppContext, cls).__new__(cls)

                cls.settings = settings

                FileManager().add_client_config("default", settings.minio_url, settings.minio_username, settings.minio_password)
                MotorClientManager().add_client_config("default", settings.mongo_uri)
                RedisManager().add_client_config("default", settings.redis_host, settings.redis_port, settings.redis_password)

                cls.paths = PathsModel.default()

            return cls._instance
