import json

from typing import List

from app.models.media_item_model import MediaItemModel
from app.providers.queue_provider import QueueProvider


class LocalListProvider(QueueProvider):
    def __init__(self, initial_data: List[dict], retry_limit=3):
        self.queue = [json.dumps(d) for d in initial_data]
        self.retry_limit = retry_limit
        self.attempts = {}

    def fetch_job(self):
        return self.queue.pop(0) if self.queue else None

    def complete_job(self, job: MediaItemModel):
        print(f"Job {job.id} finished successfully.")
        if job.id in self.attempts:
            del self.attempts[job.id]

    def fail_job(self, job: MediaItemModel | None, job_data: str):
        if not job:
            print("No job, discarding.")
            return

        self.attempts[job.id] = self.attempts.get(job.id, 0) + 1

        if self.attempts[job.id] < self.retry_limit:
            print(f"Job {job.id} failed. Re-queueing (Attempt {self.attempts[job.id]}).")
            self.queue.append(job_data)
        else:
            print(f"Job {job.id} failed {self.retry_limit} times, discarding.")

    def recover_orphans(self):
        pass

    def has_items(self) -> bool:
        return len(self.queue) > 0
