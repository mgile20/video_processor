from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel


class ImageProcessorResultModel(BaseModel):
    exif_data: dict
    thumbnail_bytes: bytes
    captured_at: Optional[datetime] = None
    face_data_targets: List[dict] = []
    face_data_all: List[dict] = []
