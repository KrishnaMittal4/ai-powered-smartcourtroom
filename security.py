"""Security helpers for the API: admin-key protection and rate limiting.
=====================================================================
Dependency-free (stdlib + FastAPI + optional Redis). Used from main.py as FastAPI dependencies.

ADMIN PROTECTION
    Routes that change or expose server state (upload, delete, feedback
    listing) require the header  X-Admin-Key: <ADMIN_API_KEY>.
    If ADMIN_API_KEY is not set on the server those routes are DISABLED
    (403), so a fresh deploy is closed by default. Wrong keys are throttled
    (ADMIN_MAX_FAILURES per 10 minutes per client) to stop brute forcing.

RATE LIMITING — Redis-backed with in-memory fallback
    When REDIS_ENABLED=true and Redis is reachable: distributed sliding-
    window counters survive restarts and work across multiple workers.
    When Redis is unavailable: falls back automatically to the existing
    in-memory SlidingWindowLimiter (single-process, resets on restart).

    Centralized limit configuration:
        RATE_LIMIT_PER_MIN         per IP per minute          (default 6)
        RATE_LIMIT_PER_DAY         per IP per day             (default 100)
        RATE_LIMIT_GLOBAL_PER_MIN  all clients, per minute    (default 12)
        RATE_LIMIT_ENABLED=0       turn everything off (local testing)

    Rate-limited endpoints return:
        HTTP 429 Too Many Requests
        Retry-After: <seconds>

CLIENT IP BEHIND A PROXY (Render / Vercel rewrites)
    TRUST_PROXY_HOPS (default 1) = number of trusted proxies in front of the
    app. The client IP is taken from the RIGHT side of X-Forwarded-For.
    Set to 0 to ignore X-Forwarded-For entirely.
"""
import hmac
import logging
import os
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

logger = logging.getLogger("security")


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def client_ip(request: Request) -> str:
    hops = _int_env("TRUST_PROXY_HOPS", 1)
    if hops > 0:
        xff = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-min(hops, len(parts))]
    return request.client.host if request.client else "unknown"


def _human(seconds: int) -> str:
    if seconds < 90:
        return f"{seconds} seconds"
    if seconds < 5400:
        return f"{round(seconds / 60)} minutes"
    return f"{round(seconds / 3600)} hours"


# ── In-Memory Sliding Window (fallback) ─────────────────────────────────────

class SlidingWindowLimiter:
    """Thread-safe sliding-window counters. `try_acquire` checks ALL the given
    (key, limit, window_seconds) rules first and records a hit on every rule
    only if all of them pass, so a denied request never uses up quota."""

    def __init__(self):
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()
        self._calls = 0

    def try_acquire(self, rules):
        now = time.monotonic()
        with self._lock:
            self._calls += 1
            if self._calls % 2000 == 0:
                for k in [k for k, q in self._hits.items() if not q or now - q[-1] > 90000]:
                    del self._hits[k]
            worst_wait = 0
            for key, limit, window in rules:
                q = self._hits.setdefault(key, deque())
                while q and now - q[0] >= window:
                    q.popleft()
                if len(q) >= limit:
                    worst_wait = max(worst_wait, int(window - (now - q[0])) + 1)
            if worst_wait:
                return False, worst_wait
            for key, _, _ in rules:
                self._hits[key].append(now)
            return True, 0

    def reset(self):
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


# ── Redis-backed Sliding Window ──────────────────────────────────────────────

def _redis_try_acquire(rules) -> tuple[bool, int]:
    """Distributed rate limiting via Redis sorted sets (sliding window).
    Falls back to in-memory limiter on any Redis failure.
    """
    try:
        from redis_client import get_redis
        r = get_redis()
        if r is None:
            return limiter.try_acquire(rules)

        now_ms = int(time.time() * 1000)
        worst_wait = 0

        # First pass: check all rules without committing hits
        for key, limit, window_seconds in rules:
            rkey = f"lexai:rl:{key}"
            window_ms = window_seconds * 1000
            cutoff_ms = now_ms - window_ms
            # Remove expired entries
            r.zremrangebyscore(rkey, "-inf", cutoff_ms)
            count = r.zcard(rkey)
            if count >= limit:
                # Oldest entry in window
                oldest = r.zrange(rkey, 0, 0, withscores=True)
                if oldest:
                    oldest_ms = oldest[0][1]
                    wait_ms = int(oldest_ms + window_ms - now_ms) + 1000
                    worst_wait = max(worst_wait, max(1, wait_ms // 1000))

        if worst_wait:
            return False, worst_wait

        # Second pass: record hits on all rules
        pipe = r.pipeline(transaction=False)
        for key, limit, window_seconds in rules:
            rkey = f"lexai:rl:{key}"
            pipe.zadd(rkey, {f"{now_ms}:{id(rules)}": now_ms})
            pipe.expire(rkey, window_seconds + 10)
        pipe.execute()
        return True, 0

    except Exception as exc:
        # Redis failure: fall back to in-memory limiter without crashing
        logger.warning("Redis rate limit failed, using in-memory fallback: %s", exc)
        return limiter.try_acquire(rules)


# ── FastAPI Dependency Factory ───────────────────────────────────────────────

def rate_limited(
    scope: str = "llm",
    per_min: str = "RATE_LIMIT_PER_MIN",
    per_day: str = "RATE_LIMIT_PER_DAY",
    default_min: int = 6,
    default_day: int = 100,
    use_global: bool = True,
):
    """FastAPI dependency factory: `Depends(rate_limited())`.

    Uses Redis-backed distributed counters when Redis is enabled,
    otherwise falls back to in-memory SlidingWindowLimiter.
    Health check endpoints are never rate-limited.
    """
    from redis_client import redis_enabled as _redis_enabled

    def dependency(request: Request):
        if os.getenv("RATE_LIMIT_ENABLED", "1") == "0":
            return
        # Never rate-limit health/liveness probes
        if request.url.path in {"/health", "/health/live", "/health/ready", "/ping"}:
            return

        ip = client_ip(request)
        rules = [
            (f"{scope}:ip:{ip}:min", _int_env(per_min, default_min), 60),
            (f"{scope}:ip:{ip}:day", _int_env(per_day, default_day), 86400),
        ]
        if use_global:
            rules.append((f"{scope}:global:min", _int_env("RATE_LIMIT_GLOBAL_PER_MIN", 12), 60))

        if _redis_enabled():
            ok, wait = _redis_try_acquire(rules)
        else:
            ok, wait = limiter.try_acquire(rules)

        if not ok:
            logger.warning(
                "Rate limit exceeded: scope=%s ip=%s retry_after=%ds", scope, ip, wait,
                extra={"rate_limit_scope": scope, "client_ip": ip, "retry_after": wait}
            )
            raise HTTPException(
                status_code=429,
                detail=f"Too many requests. Please try again in {_human(wait)}.",
                headers={"Retry-After": str(wait)},
            )

    return dependency


def require_admin(request: Request):
    """FastAPI dependency protecting admin routes with X-Admin-Key."""
    expected = os.getenv("ADMIN_API_KEY", "")
    if not expected:
        raise HTTPException(
            status_code=403,
            detail="Admin endpoints are disabled on this server (ADMIN_API_KEY is not set).",
        )
    sent = request.headers.get("x-admin-key", "")
    if hmac.compare_digest(sent.encode("utf-8"), expected.encode("utf-8")):
        return
    ok, wait = limiter.try_acquire(
        [(f"adminfail:{client_ip(request)}", _int_env("ADMIN_MAX_FAILURES", 10), 600)]
    )
    if not ok:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed attempts. Try again in {_human(wait)}.",
            headers={"Retry-After": str(wait)},
        )
    raise HTTPException(status_code=401, detail="Invalid or missing admin key.")
