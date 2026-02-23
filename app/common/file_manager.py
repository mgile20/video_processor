from threading import Lock
from typing import Dict
from typing import Optional
from typing import TypedDict

import boto3

from botocore.response import StreamingBody
from motor.motor_asyncio import AsyncIOMotorClient
from types_boto3_s3 import S3Client
from types_boto3_s3.type_defs import GetObjectOutputTypeDef
from types_boto3_s3.type_defs import PutObjectOutputTypeDef


class ClientConfig(TypedDict):
    url: str
    access_key: str
    secret_key: str


class FileManager:
    _instance: Optional["FileManager"] = None
    _lock: Lock = Lock()
    _clients: Dict[str, AsyncIOMotorClient]
    _config: Dict[str, ClientConfig]

    def __new__(cls) -> "FileManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FileManager, cls).__new__(cls)
                cls._instance._clients = {}
                cls._instance._config = {}
            return cls._instance

    def add_client_config(self, name: str, url: str, access_key: str, secret_key: str, overwrite: bool = False) -> None:
        if name in self._clients and not overwrite:
            raise RuntimeError(f"Client '{name}' is already active. Use overwrite=True to reset.")

        self._config[name] = {
            "url": url,
            "access_key": access_key,
            "secret_key": secret_key,
        }

    def get_client(self, name: str = "default") -> S3Client:
        if name not in self._clients:
            config = self._config.get(name)
            if not config:
                raise ValueError(f"Configuration for '{name}' not found. " f"Available configs: {list(self._config.keys())}")

            self._clients[name] = boto3.client(
                "s3",
                endpoint_url=config["url"],
                aws_access_key_id=config["access_key"],
                aws_secret_access_key=config["secret_key"],
            )

        return self._clients[name]

    def put_object(self, bucket: str, key: str, data: bytes, client_name: str = "default") -> PutObjectOutputTypeDef:
        client = self.get_client(client_name)

        if not client:
            raise RuntimeError(f"Client '{client_name}' does not exist.")

        response = client.put_object(Bucket=bucket, Key=key, Body=data, ContentType="application/octet-stream")
        return response

    def get_object(self, bucket: str, key: str, client_name: str = "default") -> bytes:
        client = self.get_client(client_name)

        if not client:
            raise RuntimeError(f"Client '{client_name}' does not exist.")

        response: GetObjectOutputTypeDef = client.get_object(Bucket=bucket, Key=key)

        body: StreamingBody = response["Body"]
        return body.read()
