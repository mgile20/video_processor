from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import computed_field
from pydantic import model_validator

from app.models.types.object_id import ObjectIdPydantic


class JobModel(BaseModel):
    id: ObjectIdPydantic = Field(alias="_id")
    project_id: ObjectIdPydantic
    bucket: str
    key: str
    raw_context: str

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    @computed_field
    @property
    def file_name(self) -> str:
        return PurePosixPath(self.key).name

    @computed_field
    @property
    def file_name_no_ext(self) -> str:
        return PurePosixPath(self.key).stem
