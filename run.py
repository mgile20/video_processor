import os
import shutil

from pathlib import Path

from app.logic.worker import Worker
from app.providers.local_list_provider import LocalListProvider

provider = LocalListProvider(
    [
        {
            "_id": "6999451e0323cf7727ede74a",
            "project_id": "6997fb28f401a1be515e8f36",
            "bucket": "video-maker",
            "key": "6997fb28f401a1be515e8f36/raw/IMG_1076.MP4",
        }
    ]
)

if __name__ == "__main__":
    processing_path = Path("processing")
    processing_path.mkdir(parents=True, exist_ok=True)

    worker = Worker(provider, processing_path, 5)
    worker.start()

    shutil.rmtree(processing_path)
