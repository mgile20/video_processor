import json
import sys
import time

import redis

from app.common.settings import settings


def get_redis_client():
    """Retries connection if the Redis container is still booting up."""
    while True:
        try:
            r = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                decode_responses=True,
            )
            r.ping()
            return r
        except redis.ConnectionError:
            print("Connecting to Redis... (is the container running?)")
            time.sleep(2)


def process_queue():
    r = get_redis_client()

    data = {
        "image": "video_processor",
    }

    data_string = json.dumps(data)
    r.lpush(settings.redis_task_queue_name, data_string)


if __name__ == "__main__":
    try:
        process_queue()
    except KeyboardInterrupt:
        print("\nWorker shutting down manually.")
        sys.exit(0)
