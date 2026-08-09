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

    if "redis-ha" in host and "headless" not in host:
        return [
            (
                f"redis-ha-node-{i}.redis-ha-headless.redis.svc.cluster.local",
                sentinel_port,
            )
            for i in range(3)
        ]
    return [(host, sentinel_port)]


def _sentinel_conn(host: str, port: int, password: str | None, timeout: float) -> redis.Redis:
    kwargs: dict = {
        "host": host,
        "port": port,
        "socket_timeout": timeout,
        "socket_connect_timeout": timeout,
        "decode_responses": True,
    }
    if password is not None:
        kwargs["password"] = password
    return redis.Redis(**kwargs)


def _discover_master_addr(
    endpoints: list[tuple[str, int]],
    master: str,
    password: str | None,
    timeout: float,
) -> tuple[str, int, str]:
    """Same path as redis-cli SENTINEL GET-MASTER-ADDR-BY-NAME (avoids redis-py Sentinel quirks)."""
    errors: list[str] = []
    seen_names: list[str] = []

    for host, port in endpoints:
        for auth_label, pwd in (("pass", password), ("no-auth", None)):
            if auth_label == "no-auth" and password is None:
                continue
            try:
                s = _sentinel_conn(host, port, pwd, timeout)
                addr = s.execute_command("SENTINEL", "GET-MASTER-ADDR-BY-NAME", master)
                if addr and len(addr) >= 2 and addr[0] and addr[1]:
                    return str(addr[0]), int(addr[1]), f"{host}:{port}/{auth_label}"
                try:
                    masters = s.execute_command("SENTINEL", "MASTERS")
                    names = _master_names_from_sentinel(masters)
                    for n in names:
                        if n not in seen_names:
                            seen_names.append(n)
                except Exception:
                    pass
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{host}:{port}/{auth_label}: {type(exc).__name__}: {exc}")

    hint = f" known masters={seen_names}" if seen_names else ""
    raise redis.sentinel.MasterNotFoundError(
        f"No master found for {master!r} via {endpoints!r}{hint} — {'; '.join(errors) or 'no sentinel reply'}"
    )


def _master_names_from_sentinel(masters) -> list[str]:
    """Parse SENTINEL MASTERS reply (list of field/value lists)."""
    names: list[str] = []
    if not isinstance(masters, list):
        return names
    for entry in masters:
        if not isinstance(entry, (list, tuple)):
            continue
        fields = [str(x) for x in entry]
        for i in range(0, len(fields) - 1, 2):
            if fields[i] == "name":
                names.append(fields[i + 1])
                break
    return names


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

    # 1) redis-cli equivalent — works from npd-movie when Sentinel() does not
    try:
        mhost, mport, via = _discover_master_addr(
            endpoints, sentinel_master, password, socket_connect_timeout
        )
        print(f"[redis] sentinel master {sentinel_master}={mhost}:{mport} via {via}")
        client_kw: dict = {
            "host": mhost,
            "port": mport,
            "db": db,
            "decode_responses": True,
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
        }
        if password is not None:
            client_kw["password"] = password
        if username:
            client_kw["username"] = username
        client = redis.Redis(**client_kw)
        client.ping()
        return client
    except Exception as discover_err:  # noqa: BLE001
        discover_detail = f"{type(discover_err).__name__}: {discover_err}"

    # 2) Fallback: redis-py Sentinel class
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
    errors: list[str] = [f"cli-discover: {discover_detail}"]
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
    raise redis.sentinel.MasterNotFoundError(
        f"No master found for {sentinel_master!r} via {endpoints!r} — {' | '.join(errors)}"
    ) from last_err
