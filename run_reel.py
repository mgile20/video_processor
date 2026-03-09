import asyncio

from pathlib import Path
from uuid import uuid4

import cv2

from bson import ObjectId

from app.common.app_context import AppContext
from app.common.file_manager import FileManager
from app.data.items import Items
from app.logic import highlight_reel

app_context = AppContext()
file_manager = FileManager()

project_root = app_context.paths.project_root
reel_dir = project_root.joinpath("media/reel")
audio_path = project_root.joinpath("media/audio/fsm-team-happy-days.mp3")

reel_dir.mkdir(parents=True, exist_ok=True)


async def get_images():

    data = []
    cursor = (
        Items.collection.find(
            {
                "project_id": ObjectId("69aa657acdf3e772bfe7bb00"),
                "type": "image",
            }
        )
        .sort({"order": 1})
        .limit(2)
    )
    async for row in cursor:
        data.append(row)

    return data


async def get_videos():

    data = []
    cursor = (
        Items.collection.find(
            {
                "project_id": ObjectId("69aa657acdf3e772bfe7bb00"),
                "type": "video",
            }
        )
        .sort({"order": 1})
        .limit(1)
    )
    async for row in cursor:
        data.append(row)

    return data


async def get_all():

    data = []
    cursor = (
        Items.collection.find(
            {
                "project_id": ObjectId("69aa657acdf3e772bfe7bb00"),
            }
        ).sort({"order": 1})
        # .limit(10)
    )
    async for row in cursor:
        data.append(row)

    return data


def save_to_disk(path: Path, file_bytes: bytes) -> Path:
    with open(path, "wb+") as file:
        file.write(file_bytes)

    return path


async def run_async():
    data = await get_all()
    # data = await get_images()
    # data.extend(await get_videos())

    reel_data = []

    for row in data:
        try:
            bucket = row["bucket"]
            key = row["key"]
            file_name = Path(key).name
            # file_bytes = file_manager.get_object(bucket, key)
            file_path = reel_dir.joinpath(file_name)
            # save_to_disk(file_path, file_bytes)

            d = {
                "path": file_path,
                "type": row["type"],
                # "faces": [r["box"] for r in row["face_data_targets"] if "face_data_targets" in row],
            }
            reel_data.append(d)
        except Exception as ex:
            print(ex)

    highlight_reel.create_highlight_video(reel_data, audio_path)


if __name__ == "__main__":
    asyncio.run(run_async())
