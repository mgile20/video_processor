import redis

from app.models.media_item_model import JobModel
from app.providers.queue_provider import QueueProvider


class RedisProvider(QueueProvider):
    def __init__(self, client: redis.Redis, queue_name: str, retry_limit=3):
        self.client = client
        self.queue = queue_name
        self.processing_queue = f"{queue_name}:processing"
        self.retry_limit = retry_limit
        self.dlq = f"{queue_name}:dead_letter"

    def fetch_job(self) -> str | None:
        """
        Atomically moves a job from main queue to processing queue.
        This prevents data loss if the worker dies during execution.
        """
        return self.client.lmove(self.queue, self.processing_queue, src="RIGHT", dest="LEFT")

    def complete_job(self, job: JobModel):
        """
        Removes the job from the processing queue permanently.
        Pass the full job dictionary to ensure we find the exact match.
        """

        removed_count = self.client.lrem(self.processing_queue, 1, job.raw_context)

        if removed_count > 0:
            print(f"Redis: Job {job.id} confirmed and removed from processing.")

            retry_key = f"retry_count:{job.id}"
            self.client.delete(retry_key)
        else:
            print(f"Warning: Job {job.id} not found in processing queue.")

    def fail_job(self, job: JobModel | None, job_data: str):
        """
        Increments a retry counter in Redis and either re-queues or moves to DLQ.
        """

        self.client.lrem(self.processing_queue, 1, job_data)

        if not job:
            print("Redis: Moving job to DLQ.")
            self.client.rpush(self.dlq, job_data)
            return

        retry_key = f"retry_count:{job.id}"
        current_retries = self.client.incr(retry_key)
        self.client.expire(retry_key, 3600)

        if current_retries < self.retry_limit:
            print(f"Redis: Re-queueing job {job.id} (Attempt {current_retries})")
            self.client.rpush(self.queue, job_data)
        else:
            print("Redis: Moving job to DLQ.")
            self.client.rpush(self.dlq, job_data)
            self.client.delete(retry_key)

    def recover_orphans(self):
        """
        Moves all items from the processing queue back to the main queue.
        Run this at worker startup to handle previous crashes.
        """
        processing_count = self.client.llen(self.processing_queue)
        if processing_count > 0:
            print(f"Redis: Found {processing_count} orphaned jobs. Recovering...")

            while self.client.llen(self.processing_queue) > 0:
                self.client.lmove(self.processing_queue, self.queue, src="LEFT", dest="RIGHT")
            print("Redis: Recovery complete.")
        else:
            print("Redis: No orphaned jobs found.")

    def has_items(self) -> bool:
        """Checks if the main queue has items."""
        return self.client.llen(self.queue) > 0
