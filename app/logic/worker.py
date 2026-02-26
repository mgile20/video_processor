import json
import time

from pathlib import Path
from uuid import uuid4

from app.common.app_context import AppContext
from app.common.file_manager import FileManager
from app.data.items import Items
from app.logic import ffmpeg_util
from app.logic.image_processor import ImageProcessor
from app.logic.video_processor import VideoProcessor
from app.models.media_item_model import JobModel
from app.providers.queue_provider import QueueProvider

AppContext()
file_manager = FileManager()


class Worker:
    def __init__(self, provider: QueueProvider, processing_path: Path, cooldown: int = 30):
        self.provider = provider
        self.cooldown = cooldown
        self.processing_path = processing_path

    def save_to_disk(self, file_bytes: bytes) -> Path:
        file_path = self.processing_path.joinpath(uuid4().hex)
        with open(file_path, "wb+") as file:
            file.write(file_bytes)

        return file_path

    async def run(self):
        while self.provider.has_items():
            job_data = self.provider.fetch_job()
            if not job_data:
                break

            try:
                job_dict = json.loads(job_data)
                job = JobModel.model_validate(job_dict)
            except Exception as e:
                print(f"Failed to parse job data: {e}")
                self.provider.fail_job(None, job_data)

            try:
                file_bytes = file_manager.get_object(job.bucket, job.key)
                file_path = self.save_to_disk(file_bytes)
                media_type, metadata = ffmpeg_util.identify_file(file_path)

                update_data = {}

                if media_type == "image":
                    result = ImageProcessor.run(file_path)
                elif media_type == "video":
                    result = VideoProcessor.run(file_path)

                if hasattr(result, "thumbnail_bytes"):
                    key = f"{job.project_id}/thumbnail/{job.file_name_no_ext}.jpg"
                    file_manager.put_object(job.bucket, key, result.thumbnail_bytes)
                    update_data["thumbnail_key"] = key
                if hasattr(result, "gif_bytes"):
                    key = f"{job.project_id}/gif/{job.file_name_no_ext}.gif"
                    file_manager.put_object(job.bucket, key, result.gif_bytes)
                    update_data["gif_key"] = key
                if hasattr(result, "exif_data"):
                    update_data["exif_data"] = result.exif_data

                await Items.update(job, update_data)
                await Items.update_order(job, result.captured_at)

                file_path.unlink()
                self.provider.complete_job(job)

            except Exception as e:
                print(f"Error: {e}")
                self.provider.fail_job(job, job_data)

            # Cooldown logic (only if items remain)
            if not self.provider.has_items():
                print("cooldown...")
                time.sleep(self.cooldown)

        print("All jobs processed or discarded. Worker exiting.")
