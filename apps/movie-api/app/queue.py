import json

from app.config import settings
from app.redis_client import get_redis_client


def get_redis():
    return get_redis_client(
        settings.redis_url,
        sentinel_master=settings.redis_sentinel_master,
        sentinel_port=settings.redis_sentinel_port,
    )


def enqueue_media_job(payload: dict) -> None:
    r = get_redis()
    r.lpush(settings.media_queue, json.dumps(payload))
