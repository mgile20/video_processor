import asyncio

from pathlib import Path

from bson import ObjectId

from app.common.app_context import AppContext
from app.common.file_manager import FileManager
from app.data.items import Items
from app.logic import highlight_reel
from app.logic.highlight_reel import SyncPolicy

app_context = AppContext()
file_manager = FileManager()
settings = app_context.settings

project_root = app_context.paths.project_root
reel_dir = project_root.joinpath("media/reel")
audio_dir = project_root.joinpath("media/audio")

reel_dir.mkdir(parents=True, exist_ok=True)
audio_dir.mkdir(parents=True, exist_ok=True)


async def get_images():

    data = []
    cursor = (
        Items.collection.find(
            {
                "project_id": ObjectId("69af953262162437daba001d"),
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
                "project_id": ObjectId("69af953262162437daba001d"),
                "type": "video",
            }
        )
        .sort({"order": 1})
        .limit(4)
    )
    async for row in cursor:
        data.append(row)

    return data


async def get_all():

    data = []
    cursor = (
        Items.collection.find(
            {
                "project_id": ObjectId("69b5ed5daae9ef061a1faac1"),
            }
        ).sort({"order": 1})
        # .limit(5)
    )
    async for row in cursor:
        data.append(row)

    return data


def get_audio_path():

    file_name = Path("710137c6582b468d835a3e4ca1207773.mp3").name
    file_path = audio_dir.joinpath(file_name)

    if file_path.exists():
        return file_path

    key = Path.joinpath(Path("audio"), file_name)

    file_bytes = file_manager.get_object("video-maker", str(key))
    save_to_disk(file_path, file_bytes)

    return file_path


def get_asset_path(bucket: str, key: str):
    file_name = Path(key).name
    file_path = reel_dir.joinpath(file_name)

    if file_path.exists():
        return file_path

    file_bytes = file_manager.get_object(bucket, key)
    save_to_disk(file_path, file_bytes)

    return file_path


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
            file_path = get_asset_path(bucket, key)

            d = {
                "path": file_path,
                "type": row["type"],
                "faces": [r["box"] for r in row.get("face_data_targets", [])],
            }
            reel_data.append(d)
        except Exception as ex:
            print(ex)

    audio_path = get_audio_path()

    highlight_reel.create_highlight_video(
        reel_data,
        audio_path,
        "media/output/november_2021_1.mp4",
        sync_policy=SyncPolicy(
            diagnostics_path="media/output/november_2021_1.sync_report.json",
            drift_tolerance_ms=settings.reel_sync_drift_tolerance_ms,
            enable_async_resample=settings.reel_sync_enable_async_resample,
            music_offset_seconds=settings.reel_sync_music_offset_seconds,
            enable_diagnostics=settings.reel_sync_enable_diagnostics,
            output_shortest=True,
        ),
    )


if __name__ == "__main__":
    asyncio.run(run_async())
