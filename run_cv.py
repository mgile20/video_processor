import asyncio

from pathlib import Path
from uuid import uuid4

import cv2

from bson import ObjectId

from app.common.app_context import AppContext
from app.common.file_manager import FileManager
from app.data.items import Items
from app.logic import cv2_util
from app.logic import pil_util

app_context = AppContext()
file_manager = FileManager()

project_root = app_context.paths.project_root
from_projects_dir = project_root.joinpath("media/from_projects")
output_dir = project_root.joinpath("media/detect_face_dnn")

from_projects_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)


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


def save_to_disk(path: Path, file_bytes: bytes) -> Path:
    with open(path, "wb+") as file:
        file.write(file_bytes)

    return path


async def run_async():
    data = await get_data()
    for row in data:
        try:
            bucket = row["bucket"]
            key = row["key"]
            file_name = Path(key).name
            file_bytes = file_manager.get_object(bucket, key)
            file_path = save_to_disk(from_projects_dir.joinpath(file_name), file_bytes)

            if file_name.lower().endswith("heic"):
                cv_img = cv2.cvtColor(pil_util.to_np_array(file_path), cv2.COLOR_RGB2BGR)
                result = cv2_util.overlay_face_box(cv_img)
                cv2.imwrite(output_dir.joinpath(file_path.name.replace("heic", "jpg")), result, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            else:
                result = cv2_util.overlay_face_box(file_path)
                cv2.imwrite(output_dir.joinpath(file_path.name), result, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        except Exception as ex:
            print(ex)


if __name__ == "__main__":
    asyncio.run(run_async())
