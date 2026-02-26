from datetime import datetime

from pydantic import BaseModel


class ImageProcessorResultModel(BaseModel):
    exif_data: dict
    thumbnail_bytes: bytes
    captured_at: datetime
