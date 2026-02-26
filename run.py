import asyncio
import os
import shutil

from pathlib import Path

from app.common.app_context import AppContext
from app.data.motor_manager import MotorClientManager
from app.logic.worker import Worker
from app.providers.local_list_provider import LocalListProvider

AppContext()
motor_manager = MotorClientManager()

provider = LocalListProvider(
    [
        # {
        #     "_id": "6999451e0323cf7727ede74a",
        #     "project_id": "6997fb28f401a1be515e8f36",
        #     "bucket": "video-maker",
        #     "key": "6997fb28f401a1be515e8f36/raw/IMG_1076.MP4",
        # },
        {
            "_id": "6999451e0323cf7727ede74a",
            "project_id": "6997fb28f401a1be515e8f36",
            "bucket": "video-maker",
            "key": "inbox/PXL_20260208_205246673.jpg",
        },
        {
            "_id": "6999451e0323cf7727ede74a",
            "project_id": "6997fb28f401a1be515e8f36",
            "bucket": "video-maker",
            "key": "inbox/PXL_20260117_194436350.mp4",
        },
    ]
)


async def run_async():
    items_collection = motor_manager.get_client().get_database("video_maker").get_collection("items")

    data = []
    cursor = items_collection.find({}, {"project_id": 1, "bucket": 1, "key": 1})
    async for row in cursor:
        data.append(
            {
                "_id": str(row["_id"]),
                "project_id": str(row["project_id"]),
                "bucket": str(row["bucket"]),
                "key": str(row["key"]),
            }
        )

    return data


if __name__ == "__main__":
    # data = asyncio.run(run_async())
    # provider = LocalListProvider(data)
    processing_path = Path("processing")
    processing_path.mkdir(parents=True, exist_ok=True)

    worker = Worker(provider, processing_path, 5)
    worker.start()

    shutil.rmtree(processing_path)
