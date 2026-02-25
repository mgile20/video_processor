from abc import ABC
from abc import abstractmethod

from app.models.media_item_model import MediaItemModel


class QueueProvider(ABC):
    @abstractmethod
    def fetch_job(self) -> str | None:
        pass

    @abstractmethod
    def complete_job(self, job: MediaItemModel):
        pass

    @abstractmethod
    def fail_job(self, job: MediaItemModel | None, job_data: str):
        pass

    @abstractmethod
    def recover_orphans(self):
        pass

    @abstractmethod
    def has_items(self) -> bool:
        pass
