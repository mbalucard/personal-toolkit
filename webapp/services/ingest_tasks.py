from __future__ import annotations

import uuid
from typing import Any

from webapp.services.redis_client import get_redis, get_ttl_seconds


JOB_KEY_PREFIX = "ptk:ingest:job:"
LOG_KEY_SUFFIX = ":logs"
LOG_MAX_LINES = 500

INT_FIELDS = {
    "rows",
    "waiting_time",
    "max_retries",
    "deleted_rows",
    "inserted_rows",
    "rows_per_page",
    "start_page",
    "end_page",
    "current_page",
    "processed_pages",
    "total_pages",
    "total_records",
}
NULLABLE_INT_FIELDS = {"end_page", "current_page", "total_pages", "total_records"}
FLOAT_FIELDS = {"retry_delay_seconds", "elapsed_seconds", "last_page_elapsed_seconds", "base_elapsed_seconds"}
BOOL_FIELDS = {"clear_existing", "cancel_requested"}


def _job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}"


def _log_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}{job_id}{LOG_KEY_SUFFIX}"


def _serialize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def _deserialize_field(name: str, value: str | None) -> Any:
    if value is None:
        return None
    raw = value
    if name in NULLABLE_INT_FIELDS and raw == "":
        return None
    if name in BOOL_FIELDS:
        return raw in {"1", "true", "True", "yes", "on"}
    if name in INT_FIELDS:
        if raw == "":
            return 0
        try:
            return int(raw)
        except ValueError:
            return 0
    if name in FLOAT_FIELDS:
        if raw == "":
            return 0.0
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return raw

def create_job(initial_data: dict[str, Any]) -> str:
    """
    创建一个任务（Redis 存储）。

    Args:
        initial_data (dict[str, Any]): 任务初始数据（状态、日志、统计字段等）。


    Returns:
        str: 新任务的 job_id。
    """
    job_id = uuid.uuid4().hex
    client = get_redis()
    ttl_seconds = get_ttl_seconds()
    job_key = _job_key(job_id)
    log_key = _log_key(job_id)
    logs = initial_data.get("logs")
    mapping = {k: _serialize_value(v) for k, v in initial_data.items() if k != "logs"}
    pipe = client.pipeline()
    if mapping:
        pipe.hset(job_key, mapping=mapping)
    if logs:
        pipe.delete(log_key)
        pipe.rpush(log_key, *[str(x) for x in logs])
        pipe.ltrim(log_key, -LOG_MAX_LINES, -1)
    pipe.expire(job_key, ttl_seconds)
    pipe.expire(log_key, ttl_seconds)
    pipe.execute()
    return job_id


def update_job(job_id: str, updates: dict[str, Any]) -> None:
    """
    更新任务数据（浅更新）。

    Args:
        job_id (str): 任务 ID。
        updates (dict[str, Any]): 需要更新的字段。

    Returns:
        None: 无返回值。
    """
    client = get_redis()
    ttl_seconds = get_ttl_seconds()
    job_key = _job_key(job_id)
    mapping = {k: _serialize_value(v) for k, v in updates.items() if k != "logs"}
    if not mapping:
        return
    pipe = client.pipeline()
    pipe.hset(job_key, mapping=mapping)
    pipe.expire(job_key, ttl_seconds)
    pipe.expire(_log_key(job_id), ttl_seconds)
    pipe.execute()


def append_job_log(job_id: str, message: str) -> None:
    """
    追加一条任务日志。

    Args:
        job_id (str): 任务 ID。
        message (str): 日志内容。

    Returns:
        None: 无返回值。
    """
    client = get_redis()
    ttl_seconds = get_ttl_seconds()
    log_key = _log_key(job_id)
    pipe = client.pipeline()
    pipe.rpush(log_key, message)
    pipe.ltrim(log_key, -LOG_MAX_LINES, -1)
    pipe.expire(_job_key(job_id), ttl_seconds)
    pipe.expire(log_key, ttl_seconds)
    pipe.execute()


def get_job(job_id: str) -> dict[str, Any] | None:
    """
    获取任务快照。

    Args:
        job_id (str): 任务 ID。

    Returns:
        dict[str, Any] | None: 任务数据快照；不存在则返回 None。
    """
    client = get_redis()
    job_key = _job_key(job_id)
    log_key = _log_key(job_id)
    pipe = client.pipeline()
    pipe.hgetall(job_key)
    pipe.lrange(log_key, 0, -1)
    data, logs = pipe.execute()
    if not data:
        return None
    job: dict[str, Any] = {k: _deserialize_field(k, v) for k, v in data.items()}
    job["logs"] = logs or []
    return job
