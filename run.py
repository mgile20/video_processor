import asyncio

from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient

from app.common.app_context import AppContext
from app.data.motor_manager import MotorClientManager

AppContext()
motor_manager = MotorClientManager()

client: AsyncIOMotorClient = motor_manager.get_client()
db = client.get_database("video_maker")
collection = db.get_collection("processor")


async def run_async():
    await collection.insert_one({"hello": datetime.now()})
    count = await collection.count_documents({})
    print(count)


if __name__ == "__main__":
    asyncio.run(run_async())
