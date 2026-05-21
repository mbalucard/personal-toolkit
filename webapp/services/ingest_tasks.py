from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from typing import Any


_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def create_job(initial_data: dict[str, Any]) -> str:
    """
    创建一个内存任务。

    Args:
        initial_data (dict[str, Any]): 任务初始数据（状态、日志、统计字段等）。

    Returns:
        str: 新任务的 job_id。
    """
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = initial_data
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
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(updates)


def append_job_log(job_id: str, message: str) -> None:
    """
    追加一条任务日志。

    Args:
        job_id (str): 任务 ID。
        message (str): 日志内容。

    Returns:
        None: 无返回值。
    """
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        logs = job.setdefault("logs", [])
        logs.append(message)


def get_job(job_id: str) -> dict[str, Any] | None:
    """
    获取任务快照（深拷贝）。

    Args:
        job_id (str): 任务 ID。

    Returns:
        dict[str, Any] | None: 任务数据快照；不存在则返回 None。
    """
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return deepcopy(job)
