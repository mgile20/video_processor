from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VideoProcessorResultModel(BaseModel):
    thumbnail_bytes: bytes
    gif_bytes: Optional[bytes] = None
    captured_at: Optional[datetime] = None
