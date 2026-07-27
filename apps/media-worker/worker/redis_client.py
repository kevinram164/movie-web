"""Redis client — Bitnami Sentinel HA (master) hoặc standalone URL."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

import redis
from redis.sentinel import Sentinel


def _parse_url(redis_url: str) -> tuple[str, int, str | None, str | None, int]:
    """host, port, username, password, db — password unquoted (Mbfs%402025 → Mbfs@2025)."""
    u = urlparse(redis_url)
    host = u.hostname or "redis-ha.redis.svc.cluster.local"
    port = u.port or 6379
    raw_user = u.username
    username = unquote(raw_user) if raw_user else None
    if not username:
        username = None
    password = unquote(u.password) if u.password else None
    db = 0
    if u.path and u.path not in ("", "/"):
        try:
            db = int(u.path.lstrip("/").split("/")[0] or 0)
        except ValueError:
            db = 0
    return host, port, username, password, db


def _sentinel_endpoints(host: str, sentinel_port: int) -> list[tuple[str, int]]:
    """
    Prefer Bitnami headless pods — ClusterIP:26379 from other namespaces
    sometimes breaks redis-py AUTH (redis-cli in-pod still works).
    Override: REDIS_SENTINEL_HOSTS=host1:26379,host2:26379,host3:26379
    """
    raw = os.getenv("REDIS_SENTINEL_HOSTS", "").strip()
    if raw:
        out: list[tuple[str, int]] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                h, p = part.rsplit(":", 1)
                out.append((h, int(p)))
            else:
                out.append((part, sentinel_port))
        if out:
            return out

    # Default Bitnami release redis-ha, ns redis, 3 nodes
    if "redis-ha" in host and "headless" not in host:
        return [
            (
                f"redis-ha-node-{i}.redis-ha-headless.redis.svc.cluster.local",
                sentinel_port,
            )
            for i in range(3)
        ]
    return [(host, sentinel_port)]


def _try_sentinel(
    endpoints: list[tuple[str, int]],
    *,
    master: str,
    db: int,
    socket_timeout: float,
    socket_connect_timeout: float,
    sentinel_kwargs: dict,
    master_kwargs: dict,
) -> redis.Redis:
    sentinel = Sentinel(
        endpoints,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        sentinel_kwargs=sentinel_kwargs,
        **{k: v for k, v in master_kwargs.items() if k in ("username", "password")},
    )
    client = sentinel.master_for(
        master,
        db=db,
        decode_responses=True,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        **master_kwargs,
    )
    client.ping()
    return client


def get_redis_client(
    redis_url: str,
    *,
    sentinel_master: str = "",
    sentinel_port: int = 26379,
    socket_timeout: float = 30.0,
    socket_connect_timeout: float = 5.0,
) -> redis.Redis:
    host, _port, username, password, db = _parse_url(redis_url)

    if not sentinel_master:
        return redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
        )

    endpoints = _sentinel_endpoints(host, sentinel_port)
    # protocol=2: avoid RESP3 HELLO auth quirks with Bitnami Sentinel
    base_conn = {"protocol": 2}

    attempts: list[tuple[dict, dict]] = []
    if password is not None:
        user = username or os.getenv("REDIS_USERNAME", "default").strip() or "default"
        # A) ACL user default (matches: redis-cli --user default -a ...)
        attempts.append(
            (
                {**base_conn, "username": user, "password": password},
                {**base_conn, "username": user, "password": password},
            )
        )
        # B) password-only requirepass
        attempts.append(
            (
                {**base_conn, "password": password},
                {**base_conn, "password": password},
            )
        )
    else:
        attempts.append((dict(base_conn), dict(base_conn)))

    last_err: Exception | None = None
    for sentinel_kw, master_kw in attempts:
        try:
            return _try_sentinel(
                endpoints,
                master=sentinel_master,
                db=db,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                sentinel_kwargs=sentinel_kw,
                master_kwargs=master_kw,
            )
        except (
            redis.AuthenticationError,
            redis.sentinel.MasterNotFoundError,
            redis.ConnectionError,
            OSError,
        ) as exc:
            last_err = exc
            continue

    assert last_err is not None
    raise last_err
