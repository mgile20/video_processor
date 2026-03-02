from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.auth import OperationFailure


async def drop_index_safe(collection: AsyncIOMotorCollection, index_name: str):
    try:
        await collection.drop_index(index_name)
        print(f"Index '{index_name}' dropped successfully.")
    except OperationFailure as e:
        # Error code 27 is "index not found"
        if e.code == 27:
            print(f"Index '{index_name}' does not exist. Skipping.")
        else:
            raise e
