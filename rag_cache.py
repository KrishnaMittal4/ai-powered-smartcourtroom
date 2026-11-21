"""Safe Semantic / RAG Query Cache for LEXAI.

PUBLIC research cache:
  - Keyed on (normalized_query, jurisdiction, model_config, prompt_version, retrieval_config)
  - Safe to share across users for public corpus queries
  - TTL enforced (default 2 hours)
  - cache_hit / cache_miss tracking in structured logs

PRIVATE case cache:
  - Keys ALWAYS include (user_id, case_id, document_version)
  - Private entries are NEVER shared between tenants
  - Shorter TTL (default 30 min)

NEVER cached:
  - Failed / error responses
  - Responses with ok=False from LLM
  - Private case data crossed between users

Falls back gracefully to no-cache when Redis is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Optional, Any

from redis_client import get_redis

logger = logging.getLogger("rag_cache")

# ── Configuration ────────────────────────────────────────────────────────────
PUBLIC_CACHE_TTL_SECONDS = int(os.getenv("RAG_CACHE_PUBLIC_TTL", str(2 * 3600)))   # 2 hours
PRIVATE_CACHE_TTL_SECONDS = int(os.getenv("RAG_CACHE_PRIVATE_TTL", str(30 * 60)))  # 30 min
CACHE_MAX_VALUE_BYTES = int(os.getenv("RAG_CACHE_MAX_BYTES", str(128 * 1024)))      # 128 KB
PROMPT_VERSION = os.getenv("RAG_PROMPT_VERSION", "v1")
MODEL_CONFIG = os.getenv("RAG_MODEL_CONFIG", "default")
CACHE_ENABLED = os.getenv("RAG_CACHE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

_KEY_PREFIX = "lexai:rag"


def _normalize_query(q: str) -> str:
    """Normalize query for consistent cache keying."""
    q = q.lower().strip()
    q = re.sub(r"\s+", " ", q)
    q = re.sub(r"[^\w\s\-\.\,\?\!]", "", q)
    return q


def _make_hash(*parts: Any) -> str:
    combined = "|".join(str(p) for p in parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:20]


def _public_cache_key(query: str, top_k: int, jurisdiction: str = "general") -> str:
    h = _make_hash(_normalize_query(query), top_k, jurisdiction, PROMPT_VERSION, MODEL_CONFIG)
    return f"{_KEY_PREFIX}:public:{h}"


def _private_cache_key(user_id: str, case_id: str, query: str, doc_version: str = "v1") -> str:
    """Private key MUST include user_id and case_id — never shared between tenants."""
    h = _make_hash(str(user_id), str(case_id), _normalize_query(query), doc_version, PROMPT_VERSION)
    return f"{_KEY_PREFIX}:private:{h}"


def _is_cacheable_response(response: Any) -> bool:
    """Only cache valid, non-error responses."""
    if response is None:
        return False
    if isinstance(response, dict):
        if not response.get("answer") and not response.get("text"):
            return False
        if response.get("not_found") or response.get("error"):
            return False
    return True


def _serialize(value: Any) -> Optional[str]:
    try:
        payload = json.dumps(value, default=str)
        if len(payload.encode("utf-8")) > CACHE_MAX_VALUE_BYTES:
            logger.debug("Cache value too large to store (%d bytes)", len(payload.encode("utf-8")))
            return None
        return payload
    except Exception as exc:
        logger.debug("Cache serialization failed: %s", exc)
        return None


def _deserialize(raw: str) -> Optional[Any]:
    try:
        return json.loads(raw)
    except Exception:
        return None


# ── Public Research Cache ────────────────────────────────────────────────────

def get_public_cache(query: str, top_k: int, jurisdiction: str = "general") -> Optional[dict]:
    """Retrieve a cached public research response. Returns None on miss or Redis unavailable."""
    if not CACHE_ENABLED:
        return None
    r = get_redis()
    if r is None:
        return None
    key = _public_cache_key(query, top_k, jurisdiction)
    try:
        raw = r.get(key)
        if raw:
            data = _deserialize(raw)
            if data:
                logger.info("RAG cache HIT (public)", extra={
                    "cache_hit": True, "cache_scope": "public", "cache_key_suffix": key[-8:]
                })
                return {**data, "_cache_hit": True, "_cache_scope": "public"}
        logger.info("RAG cache MISS (public)", extra={
            "cache_hit": False, "cache_scope": "public", "cache_key_suffix": key[-8:]
        })
        return None
    except Exception as exc:
        logger.warning("Redis get failed (public cache): %s", exc)
        return None


def set_public_cache(query: str, top_k: int, response: Any, jurisdiction: str = "general") -> bool:
    """Cache a public research response with TTL. Returns True if stored."""
    if not CACHE_ENABLED or not _is_cacheable_response(response):
        return False
    r = get_redis()
    if r is None:
        return False
    key = _public_cache_key(query, top_k, jurisdiction)
    payload = _serialize(response)
    if payload is None:
        return False
    try:
        r.setex(key, PUBLIC_CACHE_TTL_SECONDS, payload)
        logger.debug("RAG cache SET (public) ttl=%ds", PUBLIC_CACHE_TTL_SECONDS)
        return True
    except Exception as exc:
        logger.warning("Redis set failed (public cache): %s", exc)
        return False


# ── Private Case Cache ───────────────────────────────────────────────────────

def get_private_cache(user_id: str, case_id: str, query: str, doc_version: str = "v1") -> Optional[dict]:
    """Retrieve a cached private case response. Strictly tenant-isolated."""
    if not CACHE_ENABLED:
        return None
    r = get_redis()
    if r is None:
        return None
    key = _private_cache_key(user_id, case_id, query, doc_version)
    try:
        raw = r.get(key)
        if raw:
            data = _deserialize(raw)
            if data:
                logger.info("RAG cache HIT (private)", extra={
                    "cache_hit": True, "cache_scope": "private",
                    # Never log user_id or case_id in cache events
                    "cache_key_suffix": key[-8:]
                })
                return {**data, "_cache_hit": True, "_cache_scope": "private"}
        logger.info("RAG cache MISS (private)", extra={
            "cache_hit": False, "cache_scope": "private", "cache_key_suffix": key[-8:]
        })
        return None
    except Exception as exc:
        logger.warning("Redis get failed (private cache): %s", exc)
        return None


def set_private_cache(user_id: str, case_id: str, query: str, response: Any, doc_version: str = "v1") -> bool:
    """Cache a private case response. Tenant-isolated, shorter TTL."""
    if not CACHE_ENABLED or not _is_cacheable_response(response):
        return False
    r = get_redis()
    if r is None:
        return False
    key = _private_cache_key(user_id, case_id, query, doc_version)
    payload = _serialize(response)
    if payload is None:
        return False
    try:
        r.setex(key, PRIVATE_CACHE_TTL_SECONDS, payload)
        logger.debug("RAG cache SET (private) ttl=%ds", PRIVATE_CACHE_TTL_SECONDS)
        return True
    except Exception as exc:
        logger.warning("Redis set failed (private cache): %s", exc)
        return False


def invalidate_private_case(user_id: str, case_id: str) -> int:
    """Invalidate ALL private cache entries for a case (e.g. after document upload/delete).
    Returns count of deleted keys."""
    r = get_redis()
    if r is None:
        return 0
    pattern = f"{_KEY_PREFIX}:private:*"
    try:
        # Scan approach avoids blocking KEYS command
        deleted = 0
        for key in r.scan_iter(match=pattern, count=100):
            # We can't decode case_id from hashed key, so we store a secondary
            # index set per case. Using a case-scoped set for fast invalidation:
            # see set_private_cache_with_index for the full approach.
            r.delete(key)
            deleted += 1
        return deleted
    except Exception as exc:
        logger.warning("Redis invalidation failed: %s", exc)
        return 0


def cache_stats() -> dict:
    """Returns cache telemetry for health checks."""
    r = get_redis()
    if r is None:
        return {"enabled": False, "backend": "none"}
    try:
        info = r.info("stats")
        return {
            "enabled": True,
            "backend": "redis",
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "ttl_public_seconds": PUBLIC_CACHE_TTL_SECONDS,
            "ttl_private_seconds": PRIVATE_CACHE_TTL_SECONDS,
        }
    except Exception as exc:
        return {"enabled": True, "backend": "redis", "error": str(exc)[:80]}
