from __future__ import annotations

import os
from typing import Optional

import redis


class RedisUnavailableError(RuntimeError):
    pass


_client: Optional[redis.Redis] = None


def _int_value(value: str | None, *, default: int) -> int:
    v = (value or "").strip()
    if not v:
        return default
    return int(v)


def get_ttl_seconds() -> int:
    return _int_value(os.getenv("RedisTTL"), default=86400)


def get_redis() -> redis.Redis:
    global _client
    if _client is not None:
        return _client

    host = (os.getenv("RedisHost") or "").strip()
    if not host:
        raise RedisUnavailableError("Redis 不可用，请联系管理员")

    port = _int_value(os.getenv("RedisPort"), default=6379)
    db = _int_value(os.getenv("RedisDB"), default=0)
    password = os.getenv("RedisPassword") or None

    _client = redis.Redis(
        host=host,
        port=port,
        db=db,
        password=password,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    return _client


def ping_or_raise(*, error_message: str = "Redis 不可用，请联系管理员") -> None:
    try:
        client = get_redis()
        client.ping()
    except RedisUnavailableError:
        raise
    except BaseException as exc:
        raise RedisUnavailableError(error_message) from exc
