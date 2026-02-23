from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from app.common.app_context import AppContext
from app.data.motor_manager import MotorClientManager

AppContext()
motor_manager = MotorClientManager()

client: AsyncIOMotorClient = motor_manager.get_client()
db = client.get_database("video_maker")
collection = db.get_collection("processor")

collection.insert_one({"hello": datetime.now()})
