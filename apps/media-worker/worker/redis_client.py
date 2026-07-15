"""Redis client — Bitnami Sentinel HA (master) hoặc standalone URL."""
from __future__ import annotations

from urllib.parse import urlparse

import redis
from redis.sentinel import Sentinel


def _parse_url(redis_url: str) -> tuple[str, int, str | None, int]:
    u = urlparse(redis_url)
    host = u.hostname or "redis-ha.redis.svc.cluster.local"
    port = u.port or 6379
    password = u.password
    db = 0
    if u.path and u.path not in ("", "/"):
        try:
            db = int(u.path.lstrip("/").split("/")[0] or 0)
        except ValueError:
            db = 0
    return host, port, password, db


def get_redis_client(
    redis_url: str,
    *,
    sentinel_master: str = "",
    sentinel_port: int = 26379,
) -> redis.Redis:
    host, _port, password, db = _parse_url(redis_url)
    if sentinel_master:
        sentinel = Sentinel(
            [(host, sentinel_port)],
            socket_timeout=5,
            password=password,
            sentinel_kwargs={"password": password} if password else {},
        )
        return sentinel.master_for(
            sentinel_master,
            password=password,
            db=db,
            decode_responses=True,
            socket_timeout=5,
        )
    return redis.from_url(redis_url, decode_responses=True)
