import asyncio

from app.data.items import Items
from app.data.projects import Projects


async def run_async():
    await create_sample_data()
    # await create_indexes()
    pass


async def create_sample_data():
    await Projects.insert_sample_data()
    await Items.insert_sample_data()


async def create_indexes():
    await Items.create_indexes()
    await Items.print_indexes()


if __name__ == "__main__":
    asyncio.run(run_async())
