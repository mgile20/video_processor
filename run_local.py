import asyncio
import os
import shutil

from pathlib import Path

from bson import ObjectId

from app.data.items import Items
from app.data.projects import Projects
from app.logic.worker import Worker
from app.providers.local_list_provider import LocalListProvider


async def get_data():

    data = []
    cursor = Items.collection.find(
        {
            # "_id": ObjectId("69a9122ecdf3e772bfe7bafa"),
            "project_id": ObjectId("69a8ff40cdf3e772bfe7baf3"),
        }
    )
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


async def run_async():
    data = await get_data()

    provider = LocalListProvider(data)
    processing_path = Path("processing")
    processing_path.mkdir(parents=True, exist_ok=True)

    worker = Worker(provider, processing_path, 5)
    await worker.run()

    shutil.rmtree(processing_path)


if __name__ == "__main__":
    asyncio.run(run_async())
