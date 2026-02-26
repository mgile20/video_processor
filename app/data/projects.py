from datetime import datetime
from datetime import timezone

from bson import ObjectId
from bson.codec_options import CodecOptions

from app.common.app_context import AppContext
from app.data.motor_manager import MotorClientManager

AppContext()
motor_manager = MotorClientManager()


class Projects:
    aware_utc_options = CodecOptions(tz_aware=True, tzinfo=timezone.utc)

    client = motor_manager.get_client()
    database = client.get_database("video_maker", codec_options=aware_utc_options)
    collection = database.get_collection("projects")

    @classmethod
    async def insert_sample_data(cls):
        await cls.collection.delete_one({"_id": ObjectId("69a06248947603081ae0ff84")})

        data = {
            "_id": ObjectId("69a06248947603081ae0ff84"),
            "name": "Test",
            "created_at": datetime.now(timezone.utc),
        }

        await cls.collection.insert_one(data)
