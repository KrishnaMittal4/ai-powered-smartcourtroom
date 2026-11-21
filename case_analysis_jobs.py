"""Enhanced Case Analysis Job Queue for LEXAI.

Provides a durable background job system with real per-stage progress tracking.
Architecture:
  - When Redis is enabled → job metadata persisted in Redis (survives restarts)
  - When Redis unavailable → in-memory dict (existing behavior, demo-safe)

Stages (granular, real — never fake progress %):
  QUEUED → preparing_documents → extracting_text → chunking_embeddings
        → retrieving_context → generating_analysis → normalizing → COMPLETED
                                                                 → FAILED
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Callable

from redis_client import get_redis

logger = logging.getLogger("case_analysis_jobs")

_in_memory_jobs: dict[str, dict] = {}
_lock = threading.RLock()
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="case-intel")

REDIS_JOB_TTL = 60 * 60 * 6   # 6 hours — jobs expire from Redis after this
REDIS_KEY_PREFIX = "lexai:job:"

# Ordered stage definitions with human-readable labels and progress %
JOB_STAGES = [
    ("queued",                 "Queued",                                  0),
    ("preparing_documents",    "Preparing private case documents",        10),
    ("extracting_text",        "Extracting text from documents",          25),
    ("chunking_embeddings",    "Chunking and generating embeddings",      40),
    ("retrieving_context",     "Selecting source-grounded case excerpts", 55),
    ("generating_analysis",    "Generating structured Case Intelligence", 70),
    ("normalizing",            "Validating and normalizing analysis",     90),
    ("completed",              "Case Intelligence ready",                100),
    ("failed",                 "Analysis failed",                          0),
]

STAGE_PROGRESS = {stage: (label, pct) for stage, label, pct in JOB_STAGES}


def _now() -> int:
    return int(time.time())


def _stage_info(stage: str, custom_message: Optional[str] = None) -> dict:
    label, pct = STAGE_PROGRESS.get(stage, (stage.replace("_", " ").title(), 0))
    return {
        "stage": stage,
        "stage_label": custom_message or label,
        "progress_pct": pct,
    }


# ── Redis persistence helpers ────────────────────────────────────────────────

def _redis_key(job_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}{job_id}"


def _save_to_redis(job: dict) -> None:
    r = get_redis()
    if r is None:
        return
    try:
        import json
        # Strip the result from Redis to avoid storing large case analysis text in Redis
        slim = {k: v for k, v in job.items() if k != "result"}
        r.setex(_redis_key(job["job_id"]), REDIS_JOB_TTL, json.dumps(slim, default=str))
    except Exception as exc:
        logger.debug("Redis job save failed: %s", exc)


def _load_from_redis(job_id: str) -> Optional[dict]:
    r = get_redis()
    if r is None:
        return None
    try:
        import json
        raw = r.get(_redis_key(job_id))
        if raw:
            return json.loads(raw)
        return None
    except Exception:
        return None


# ── Job Management ───────────────────────────────────────────────────────────

def _get_job(job_id: str) -> Optional[dict]:
    with _lock:
        job = _in_memory_jobs.get(job_id)
        if job:
            return job
    # Fallback: try Redis for jobs created on a previous instance
    return _load_from_redis(job_id)


def _update_job(job_id: str, **updates) -> None:
    updates["updated_at"] = _now()
    with _lock:
        if job_id in _in_memory_jobs:
            _in_memory_jobs[job_id].update(updates)
            job_snapshot = dict(_in_memory_jobs[job_id])
        else:
            return
    # Persist asynchronously to Redis (best-effort)
    try:
        _save_to_redis(job_snapshot)
    except Exception:
        pass


def start(user_id: str, case_id: str, fn: Callable) -> dict:
    """Start a background Case Intelligence job.

    fn(progress_callback) is called in a thread pool.
    progress_callback(stage, message=None) updates job state in real-time.
    """
    job_id = uuid.uuid4().hex
    si = _stage_info("queued")
    job = {
        "job_id": job_id,
        "user_id": str(user_id),
        "case_id": str(case_id),
        "status": "queued",
        **si,
        "message": si["stage_label"],
        "created_at": _now(),
        "updated_at": _now(),
        "result": None,
        "error": None,
    }

    with _lock:
        _in_memory_jobs[job_id] = job
    _save_to_redis(job)

    def progress(stage: str, message: Optional[str] = None) -> None:
        si = _stage_info(stage, message)
        _update_job(
            job_id,
            status="processing" if stage not in ("completed", "failed") else stage,
            **si,
            message=si["stage_label"],
        )

    def runner():
        try:
            progress("preparing_documents")
            result = fn(progress)
            si = _stage_info("completed")
            _update_job(
                job_id,
                status="completed",
                **si,
                message="Case Intelligence ready",
                result=result,
            )
            logger.info("Case analysis job completed: job_id=%s case_id=%s", job_id, case_id)
        except Exception as exc:
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                message = detail.get("message") or detail.get("detail") or str(detail)
                code = detail.get("code") or "analysis_failed"
                retryable = bool(detail.get("retryable", True))
            else:
                message = str(detail or exc) or "Case Intelligence failed"
                code = "analysis_failed"
                retryable = True

            si = _stage_info("failed", message)
            _update_job(
                job_id,
                status="failed",
                **si,
                message=message,
                error={"code": code, "message": message, "retryable": retryable},
            )
            logger.warning(
                "Case analysis job failed: job_id=%s case_id=%s code=%s retryable=%s",
                job_id, case_id, code, retryable
            )

    _executor.submit(runner)

    # Return safe public view (no user_id)
    return {k: v for k, v in job.items() if k not in {"user_id", "result"}}


def get(user_id: str, case_id: str, job_id: str) -> Optional[dict]:
    """Get job status, enforcing ownership. Returns None if not found or unauthorized."""
    job = _get_job(job_id)
    if not job:
        return None
    if job.get("user_id") != str(user_id) or job.get("case_id") != str(case_id):
        return None
    return {k: v for k, v in job.items() if k != "user_id"}
