from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator


class FormatTags(BaseModel):
    major_brand: Optional[str] = None
    minor_version: Optional[str] = None
    compatible_brands: Optional[str] = None
    creation_time: Optional[datetime] = None
    location: Optional[str] = None


class VideoMetadataModel(BaseModel):
    nb_streams: int
    nb_programs: int
    format_name: str
    format_long_name: str

    # Using Field to allow coercion from string to numeric types
    start_time: float = Field(description="Start time in seconds")
    duration: float = Field(description="Duration in seconds")
    size: int = Field(description="File size in bytes")
    bit_rate: Optional[int] = None
    probe_score: int

    tags: Optional[FormatTags] = None

    @model_validator(mode="before")
    @classmethod
    def flatten_ffprobe(cls, data: dict):
        if "format" in data:
            format_data = data.get("format", {})
            flat_dict = {**format_data}
            return flat_dict
        return data
