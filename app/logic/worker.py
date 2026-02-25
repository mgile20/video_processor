import time

from pathlib import Path
from uuid import uuid4

from app.common.app_context import AppContext
from app.common.file_manager import FileManager
from app.logic import ffmpeg_util
from app.models.media_item_model import MediaItemModel
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

    def start(self):
        while self.provider.has_items():
            job_data = self.provider.fetch_job()
            if not job_data:
                break

            try:
                job = MediaItemModel.model_validate_json(job_data)
            except Exception as e:
                print(f"Failed to parse job data: {e}")
                self.provider.fail_job(None, job_data)

            try:
                job = MediaItemModel.model_validate_json(job_data)

                file_bytes = file_manager.get_object(job.bucket, job.key)
                file_path = self.save_to_disk(file_bytes)
                ffmpeg_util.identify_file(file_path)

                self.provider.complete_job(job)

            except Exception as e:
                print(f"Error: {e}")
                self.provider.fail_job(job, job_data)

            # Cooldown logic (only if items remain)
            if self.provider.has_items():
                time.sleep(self.cooldown)

        print("All jobs processed or discarded. Worker exiting.")
