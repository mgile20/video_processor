import argparse
import shutil

from pathlib import Path

from gridfs.grid_file import ObjectId
from redis import asyncio

from app.data.items import Items
from app.data.projects import Projects

parser = argparse.ArgumentParser(description="Render a video with assets for a given project.")
parser.add_argument("--pid", type=str, help="object id of the project you wish to render", required=True)

args = parser.parse_args()


async def get_all(project_id: str | ObjectId):

    data = []
    cursor = Items.collection.find(
        {
            "project_id": ObjectId(project_id),
        }
    ).sort({"order": 1})
    async for row in cursor:
        data.append(row)

    return data


async def run_async():
    processing_path = Path("assets")
    processing_path.mkdir(parents=True, exist_ok=True)

    project = await Projects.collection.find_one({"_id": ObjectId(args.pid)})

    if not project:
        raise Exception("Project not found")

    data = await get_all(args.pid)

    shutil.rmtree(processing_path)


if __name__ == "__main__":
    asyncio.run(run_async())
