"""Redis client — Bitnami Sentinel HA (master) hoặc standalone URL."""
from __future__ import annotations

import os
from urllib.parse import unquote, urlparse

import redis
from redis.sentinel import Sentinel


def _parse_url(redis_url: str) -> tuple[str, int, str | None, str | None, int]:
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
    base_conn = {"protocol": 2}

    attempts: list[tuple[str, dict, dict]] = []
    if password is not None:
        attempts.append(
            (
                "pass-only",
                {**base_conn, "password": password},
                {**base_conn, "password": password},
            )
        )
        user = username or os.getenv("REDIS_USERNAME", "").strip() or None
        if user:
            attempts.append(
                (
                    f"acl:{user}",
                    {**base_conn, "username": user, "password": password},
                    {**base_conn, "username": user, "password": password},
                )
            )
    else:
        attempts.append(("no-auth", dict(base_conn), dict(base_conn)))

    last_err: Exception | None = None
    errors: list[str] = []
    for label, sentinel_kw, master_kw in attempts:
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
            errors.append(f"{label}: {type(exc).__name__}: {exc}")
            continue

    assert last_err is not None
    detail = " | ".join(errors) if errors else str(last_err)
    raise redis.sentinel.MasterNotFoundError(
        f"No master found for {sentinel_master!r} via {endpoints!r} — {detail}"
    ) from last_err
