from datetime import datetime
from datetime import timezone

import pymongo
import pymongo.errors

from bson import ObjectId
from bson.codec_options import CodecOptions
from fractional_indexing import generate_key_between

from app.common.app_context import AppContext
from app.data import util
from app.data.motor_manager import MotorClientManager
from app.models.media_item_model import JobModel

AppContext()
motor_manager = MotorClientManager()

INDEXING_DIGITS = "abcdefghijklmnopqrstuvwxyz"


class Items:
    aware_utc_options = CodecOptions(tz_aware=True, tzinfo=timezone.utc)

    client = motor_manager.get_client()
    database = client.get_database("video_maker", codec_options=aware_utc_options)
    collection = database.get_collection("items")

    @classmethod
    async def update_order(cls, job: JobModel, captured_at: datetime | None) -> str:
        if not captured_at:
            return

        prev_item = await cls.collection.find_one(
            {
                "project_id": job.project_id,
                "$or": [
                    {
                        "captured_at": {
                            "$lt": captured_at,
                        }
                    },
                    {
                        "captured_at": captured_at,
                        "_id": {"$lt": job.id},
                    },
                ],
                "order": {
                    "$exists": True,
                },
            },
            sort=[("captured_at", -1), ("_id", -1)],
            projection={"order": 1},
        )

        next_item = await cls.collection.find_one(
            {
                "project_id": job.project_id,
                "$or": [
                    {
                        "captured_at": {
                            "$gt": captured_at,
                        }
                    },
                    {
                        "captured_at": captured_at,
                        "_id": {
                            "$gt": job.id,
                        },
                    },
                ],
                "order": {
                    "$exists": True,
                },
            },
            sort=[("captured_at", 1), ("_id", 1)],
            projection={"order": 1},
        )

        prev_order = prev_item.get("order") if prev_item else None
        next_order = next_item.get("order") if next_item else None

        new_rank = generate_key_between(prev_order, next_order, INDEXING_DIGITS)

        try:
            await cls.collection.update_one({"_id": job.id}, {"$set": {"order": new_rank, "captured_at": captured_at}})
            return new_rank
        except pymongo.errors.DuplicateKeyError:
            return await cls.update_order(job, captured_at)

    @classmethod
    async def update(cls, job: JobModel, update: dict):
        await cls.collection.update_one({"_id": job.id}, {"$set": update})

    @classmethod
    async def create_indexes(cls):
        await util.drop_index_safe(cls.collection, "neighbor_lookup_idx")
        await util.drop_index_safe(cls.collection, "unique_project_order_idx")

        neighbor_index = pymongo.IndexModel(
            [
                ("project_id", pymongo.ASCENDING),
                ("captured_at", pymongo.ASCENDING),
                ("_id", pymongo.ASCENDING),
            ],
            name="neighbor_lookup_idx",
        )

        order_index = pymongo.IndexModel(
            [
                ("project_id", pymongo.ASCENDING),
                ("order", pymongo.ASCENDING),
            ],
            unique=True,
            name="unique_project_order_idx",
            partialFilterExpression={
                "order": {"$type": "string"},
            },
        )

        await cls.collection.create_indexes([neighbor_index, order_index])

    @classmethod
    async def print_indexes(cls):
        async for index in cls.collection.list_indexes():
            print(index)

    @classmethod
    async def insert_sample_data(cls):
        await cls.collection.delete_one({"project_id": ObjectId("69a06248947603081ae0ff84")})

        data = [
            {
                "project_id": ObjectId("69a06248947603081ae0ff84"),
                "bucket": "video-maker",
                "key": "69a06248947603081ae0ff84/raw/photo.jpg",
                "created_at": datetime.now(timezone.utc),
            },
            {
                "project_id": ObjectId("69a06248947603081ae0ff84"),
                "bucket": "video-maker",
                "key": "69a06248947603081ae0ff84/raw/video.mp4",
                "created_at": datetime.now(timezone.utc),
            },
        ]

        await cls.collection.insert_many(data)
