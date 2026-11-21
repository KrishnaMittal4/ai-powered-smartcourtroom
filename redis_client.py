"""Redis connection manager for LEXAI.

Provides a gracefully degrading Redis client:
- When REDIS_ENABLED=true and REDIS_URL is set → real Redis connection.
- When Redis is unavailable or REDIS_ENABLED is false → all operations
  silently no-op (None returned), so calling code never crashes.

Usage:
    from redis_client import get_redis, redis_enabled

    r = get_redis()
    if r:
        r.set("key", "value", ex=300)
    else:
        # fallback to in-memory / skip cache
        pass
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger("redis_client")

_redis_instance = None
_redis_lock = threading.Lock()
_redis_error_logged = False


def redis_enabled() -> bool:
    return os.getenv("REDIS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_redis():
    """Return a connected Redis client or None if Redis is unavailable/disabled.

    Thread-safe singleton — connects once on first call, then reuses the
    connection pool. Failure does not raise: returns None so callers can
    gracefully fall back to in-memory alternatives.
    """
    global _redis_instance, _redis_error_logged

    if not redis_enabled():
        return None

    if _redis_instance is not None:
        return _redis_instance

    with _redis_lock:
        # Double-checked locking
        if _redis_instance is not None:
            return _redis_instance

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379").strip()
        try:
            import redis as redis_lib  # type: ignore
            client = redis_lib.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=False,
                health_check_interval=30,
            )
            # Validate the connection
            client.ping()
            _redis_instance = client
            logger.info("Redis connected successfully at %s", redis_url.split("@")[-1])
            return _redis_instance
        except ImportError:
            if not _redis_error_logged:
                logger.warning("redis package not installed; Redis features disabled (pip install redis>=5.0.0)")
                _redis_error_logged = True
            return None
        except Exception as exc:
            if not _redis_error_logged:
                logger.warning("Redis connection failed (%s); falling back to in-memory mode", exc)
                _redis_error_logged = True
            return None


def redis_health() -> dict:
    """Returns Redis health status for /health/ready endpoint."""
    if not redis_enabled():
        return {"enabled": False, "status": "disabled"}
    r = get_redis()
    if r is None:
        return {"enabled": True, "status": "unavailable"}
    try:
        r.ping()
        return {"enabled": True, "status": "connected"}
    except Exception as exc:
        return {"enabled": True, "status": "error", "error": str(exc)[:80]}
