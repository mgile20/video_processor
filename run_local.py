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
            # "name": "5cdc3f7f85a74f8793680db613529a66.heic",
            # "project_id": ObjectId("6997fb28f401a1be515e8f36"),  # demo
            # "project_id": ObjectId("69a06248947603081ae0ff84"), #test
            "project_id": ObjectId("69a1c9e727eb84ce903a3b6c"),  # september
            # "_id": ObjectId("69a1ca6027eb84ce903a3bb8"),
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


async def create_sample_data():
    await Projects.insert_sample_data()
    await Items.insert_sample_data()


async def create_indexes():
    await Items.create_indexes()
    await Items.print_indexes()


if __name__ == "__main__":
    # asyncio.run(create_indexes())
    # asyncio.run(create_sample_data())
    asyncio.run(run_async())
