from abc import ABC
from abc import abstractmethod

from app.models.media_item_model import JobModel


class QueueProvider(ABC):
    @abstractmethod
    def fetch_job(self) -> str | None:
        pass

    @abstractmethod
    def complete_job(self, job: JobModel):
        pass

    @abstractmethod
    def fail_job(self, job: JobModel | None, job_data: str):
        pass

    @abstractmethod
    def recover_orphans(self):
        pass

    @abstractmethod
    def has_items(self) -> bool:
        pass
