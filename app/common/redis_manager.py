from threading import Lock
from typing import Dict
from typing import Optional
from typing import TypedDict

import redis


class ClientConfig(TypedDict):
    host: str
    port: int
    password: str


class RedisManager:
    _instance: Optional["RedisManager"] = None
    _lock: Lock = Lock()
    _clients: Dict[str, redis.Redis]
    _config: Dict[str, ClientConfig]

    def __new__(cls) -> "RedisManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RedisManager, cls).__new__(cls)
                cls._instance._clients = {}
                cls._instance._config = {}
            return cls._instance

    def add_client_config(self, name: str, host: str, port: int, password: str, overwrite=False) -> None:
        if name in self._clients and not overwrite:
            raise RuntimeError(f"Client '{name}' is already active. Use overwrite=True to reset.")

        self._config[name] = {
            "host": host,
            "port": port,
            "password": password,
        }

    def get_client(self, name: str = "default") -> redis.Redis:
        if name not in self._clients:
            config = self._config.get(name)
            if not config:
                raise ValueError(f"Configuration for '{name}' not found. " f"Available configs: {list(self._config.keys())}")

            self._clients[name] = redis.Redis(
                host=config["host"],
                port=config["port"],
                password=config["password"],
                decode_responses=True,
            )

        return self._clients[name]
