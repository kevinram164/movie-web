import json

import redis

from app.config import settings


def get_redis() -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_media_job(payload: dict) -> None:
    r = get_redis()
    r.lpush(settings.media_queue, json.dumps(payload))
