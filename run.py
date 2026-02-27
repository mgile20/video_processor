import asyncio
import shutil

from pathlib import Path

from app.common.app_context import AppContext
from app.common.redis_manager import RedisManager
from app.logic.worker import Worker
from app.providers.redis_provider import RedisProvider

app_context = AppContext()
redis_client = RedisManager().get_client()


async def run_async():

    provider = RedisProvider(redis_client, app_context.settings.redis_processing_queue_name)
    processing_path = Path("processing")
    processing_path.mkdir(parents=True, exist_ok=True)

    worker = Worker(provider, processing_path, 30)
    await worker.run()

    shutil.rmtree(processing_path)


if __name__ == "__main__":
    asyncio.run(run_async())
