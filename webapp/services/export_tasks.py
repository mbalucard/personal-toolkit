from __future__ import annotations

import threading
import uuid
from copy import deepcopy
from typing import Any


_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def create_job(initial_data: dict[str, Any]) -> str:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = initial_data
    return job_id


def update_job(job_id: str, updates: dict[str, Any]) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(updates)


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return deepcopy(job)
