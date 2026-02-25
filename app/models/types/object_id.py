from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic_core import core_schema


class ObjectIdPydantic(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: Any) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(ObjectId),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(lambda x: str(x)),
        )

    @classmethod
    def validate(cls, v: Any) -> ObjectId:
        if not isinstance(v, ObjectId):
            if isinstance(v, (str, bytes)) or v is None:
                return ObjectId(v)
            if isinstance(v, datetime):
                return ObjectId.from_datetime(v)

            raise TypeError("ObjectId required")
        return v
