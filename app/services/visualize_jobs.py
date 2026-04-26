"""In-memory tracker for asynchronous visualize jobs.

Each /visualize/ POST returns immediately with a task_id while the actual
gpt-image generation (~2-4 min) runs as a background asyncio task. Clients
poll GET /visualize/{task_id} until status == "done".

State is process-local — fine for a single-worker dev/MVP. For multi-worker
production swap this for a Redis-backed store or move into Postgres.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Literal

JobStatus = Literal["pending", "done", "failed"]

# Clean up job records older than this on each create_job() call.
JOB_TTL_SECONDS = 60 * 60  # 1 hour


@dataclass
class VisualizeJob:
    id: uuid.UUID
    user_id: uuid.UUID
    session_id: uuid.UUID
    product_id: uuid.UUID | None   # None for composite multi-category renders
    room_image_id: uuid.UUID
    status: JobStatus = "pending"
    image_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


_jobs: dict[uuid.UUID, VisualizeJob] = {}


def _gc() -> None:
    cutoff = time.time() - JOB_TTL_SECONDS
    stale = [k for k, v in _jobs.items() if v.updated_at < cutoff]
    for k in stale:
        _jobs.pop(k, None)


def create_job(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    product_id: uuid.UUID | None,   # None for composite renders
    room_image_id: uuid.UUID,
) -> VisualizeJob:
    _gc()
    job = VisualizeJob(
        id=uuid.uuid4(),
        user_id=user_id,
        session_id=session_id,
        product_id=product_id,
        room_image_id=room_image_id,
    )
    _jobs[job.id] = job
    return job


def get_job(job_id: uuid.UUID) -> VisualizeJob | None:
    return _jobs.get(job_id)


def mark_done(job_id: uuid.UUID, *, image_id: uuid.UUID, message_id: uuid.UUID) -> None:
    j = _jobs.get(job_id)
    if not j:
        return
    j.status = "done"
    j.image_id = image_id
    j.message_id = message_id
    j.updated_at = time.time()


def mark_failed(job_id: uuid.UUID, error: str) -> None:
    j = _jobs.get(job_id)
    if not j:
        return
    j.status = "failed"
    j.error = error[:500]
    j.updated_at = time.time()
