from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from app.models.types.object_id import ObjectIdPydantic


class JobModel(BaseModel):
    id: ObjectIdPydantic = Field(alias="_id")
    project_id: ObjectIdPydantic
    bucket: str
    key: str
    raw_context: str = ""

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

    @model_validator(mode="before")
    @classmethod
    def capture_raw_context(cls, data: Any) -> Any:
        if isinstance(data, (dict, str)):
            data["raw_context"] = str(data)
        return data
