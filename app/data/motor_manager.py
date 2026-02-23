from threading import Lock
from typing import Any
from typing import Dict
from typing import Optional
from typing import TypedDict

from motor.motor_asyncio import AsyncIOMotorClient


class ClientConfig(TypedDict):
    uri: str
    options: Dict[str, Any]


class MotorClientManager:
    _instance: Optional["MotorClientManager"] = None
    _lock: Lock = Lock()
    _clients: Dict[str, AsyncIOMotorClient]
    _config: Dict[str, ClientConfig]

    def __new__(cls) -> "MotorClientManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MotorClientManager, cls).__new__(cls)
                cls._instance._clients = {}
                cls._instance._config = {}
            return cls._instance

    def add_client_config(self, name: str, uri: str, overwrite: bool = False, **kwargs: Any) -> None:
        """
        Registers a connection string and optional motor settings.
        Example: manager.add_client_config("primary", "mongodb://localhost", maxPoolSize=50)
        """
        if name in self._clients and not overwrite:
            raise RuntimeError(f"Client '{name}' is already active. Use overwrite=True to reset.")

        self._config[name] = {"uri": uri, "options": kwargs}

    def get_client(self, name: str = "default") -> AsyncIOMotorClient:
        """
        Lazy loads the Motor client using the stored config and options.
        """
        if name not in self._clients:
            config = self._config.get(name)
            if not config:
                raise ValueError(f"Configuration for '{name}' not found. " f"Available configs: {list(self._config.keys())}")

            self._clients[name] = AsyncIOMotorClient(config["uri"], **config["options"])

        return self._clients[name]
