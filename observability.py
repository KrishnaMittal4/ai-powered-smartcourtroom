"""Observability, Structured Logging, and Sentry Integration for LEXAI.

Provides:
- Request ID correlation via contextvars
- JSON-formatted structured logging
- Sentry integration with automatic sensitive legal data & PII scrubbing
- RAG and LLM telemetry logging helpers
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Optional

# Context variable holding the correlation ID for the active request
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

def get_request_id() -> str:
    return request_id_ctx.get() or "system"

def set_request_id(req_id: str) -> None:
    request_id_ctx.set(req_id)

# Keys that must NEVER appear in unscrubbed external logs or Sentry events
SENSITIVE_KEY_PATTERNS = {
    "key", "token", "secret", "password", "auth", "credential", "cookie",
    "private_key", "jwt", "authorization", "bearer"
}

LEGAL_CONTENT_KEYS = {
    "prompt", "untrusted_document_context", "document_text", "legal_text",
    "evidence_text", "full_text", "case_text", "chunk_text"
}

def is_sensitive_key(key: str) -> bool:
    k = key.lower()
    return any(pattern in k for pattern in SENSITIVE_KEY_PATTERNS)

def scrub_sensitive_dict(data: Any, max_depth: int = 3) -> Any:
    """Recursively scrub sensitive keys, API keys, tokens, and large private legal texts."""
    if max_depth <= 0:
        return "<depth-limit>"
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            k_str = str(k)
            if is_sensitive_key(k_str):
                scrubbed[k_str] = "[REDACTED]"
            elif k_str.lower() in LEGAL_CONTENT_KEYS and isinstance(v, str):
                scrubbed[k_str] = f"[LEGAL_TEXT_REDACTED len={len(v)}]"
            else:
                scrubbed[k_str] = scrub_sensitive_dict(v, max_depth - 1)
        return scrubbed
    elif isinstance(data, list):
        return [scrub_sensitive_dict(item, max_depth - 1) for item in data[:50]]
    elif isinstance(data, str):
        # Redact JWTs or bearer tokens appearing inline in strings
        if len(data) > 60 and ("eyJh" in data or "gsk_" in data or "AIza" in data):
            return "[TOKEN_REDACTED]"
        return data
    return data


class JSONLogFormatter(logging.Formatter):
    """Produces JSON-formatted log lines conforming to production telemetry standards."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id(),
        }

        # Include custom fields passed in extra={...}
        for attr, val in record.__dict__.items():
            if attr not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "msg", "name", "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName"
            } and not attr.startswith("_"):
                log_entry[attr] = scrub_sensitive_dict(val)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Configures root logger with JSON formatter in production or standard console in dev."""
    root_logger = logging.getLogger()
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Avoid duplicate handlers
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if json_format:
            handler.setFormatter(JSONLogFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] %(message)s"
            ))
        root_logger.addHandler(handler)


def sentry_event_scrubber(event: dict, hint: dict) -> Optional[dict]:
    """Sentry before_send hook: rigorously strips sensitive headers, tokens, and legal texts."""
    try:
        # Scrub request headers
        if "request" in event:
            req = event["request"]
            if "headers" in req and isinstance(req["headers"], dict):
                for h in list(req["headers"].keys()):
                    if is_sensitive_key(h):
                        req["headers"][h] = "[REDACTED]"
            if "data" in req:
                req["data"] = scrub_sensitive_dict(req["data"])
            if "cookies" in req:
                req["cookies"] = "[REDACTED]"

        # Scrub breadcrumbs
        if "breadcrumbs" in event and "values" in event["breadcrumbs"]:
            for b in event["breadcrumbs"]["values"]:
                if "data" in b and isinstance(b["data"], dict):
                    b["data"] = scrub_sensitive_dict(b["data"])

        # Scrub extra contexts
        if "extra" in event and isinstance(event["extra"], dict):
            event["extra"] = scrub_sensitive_dict(event["extra"])

        return event
    except Exception:
        # Fallback to returning original event if scrubber fails, ensuring Sentry doesn't crash app
        return event


def init_sentry() -> bool:
    """Initializes Sentry SDK if SENTRY_DSN is configured, with safe fallback and PII scrubbing."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logging.getLogger("observability").info("Sentry DSN not configured; error tracking disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        environment = os.getenv("LEXAI_ENV", "production").strip().lower()
        release = os.getenv("RENDER_GIT_COMMIT", os.getenv("VERCEL_GIT_COMMIT_SHA", "latest"))
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            before_send=sentry_event_scrubber,
            send_default_pii=False,
            integrations=[FastApiIntegration(transaction_style="endpoint")],
        )
        logging.getLogger("observability").info("Sentry initialized successfully for environment: %s", environment)
        return True
    except ImportError:
        logging.getLogger("observability").warning("sentry-sdk not installed; skipping Sentry initialization.")
        return False
    except Exception as exc:
        logging.getLogger("observability").error("Failed to initialize Sentry: %s", exc)
        return False


def log_rag_event(
    logger: logging.Logger,
    event_type: str,
    *,
    retrieval_ms: float = 0.0,
    reranking_ms: float = 0.0,
    llm_ms: float = 0.0,
    retrieved_chunk_count: int = 0,
    crag_retry_count: int = 0,
    citation_count: int = 0,
    confidence_level: str = "unknown",
    query_type: str = "general",
    extra_data: Optional[dict] = None,
) -> None:
    """Safe structured logging for RAG queries without exposing legal queries or context."""
    total_latency_ms = round(retrieval_ms + reranking_ms + llm_ms, 2)
    payload = {
        "event_type": f"rag_{event_type}",
        "retrieval_ms": round(retrieval_ms, 2),
        "reranking_ms": round(reranking_ms, 2),
        "llm_ms": round(llm_ms, 2),
        "total_latency_ms": total_latency_ms,
        "retrieved_chunk_count": retrieved_chunk_count,
        "crag_retry_count": crag_retry_count,
        "citation_count": citation_count,
        "confidence_level": confidence_level,
        "query_type": query_type,
    }
    if extra_data:
        payload.update(scrub_sensitive_dict(extra_data))

    logger.info("RAG Execution Completed", extra=payload)


def log_llm_event(
    logger: logging.Logger,
    provider: str,
    *,
    model: str,
    latency_ms: float,
    attempt: int = 1,
    fallback_used: bool = False,
    status: str = "success",
    token_budget: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Safe structured logging for LLM provider attempts and fallbacks."""
    payload = {
        "event_type": "llm_call",
        "provider": provider,
        "model": model,
        "latency_ms": round(latency_ms, 2),
        "attempt": attempt,
        "fallback_used": fallback_used,
        "status": status,
        "token_budget": token_budget,
    }
    if error:
        payload["error_summary"] = str(error)[:160]

    logger.info(f"LLM Call {status.upper()}: {provider}/{model}", extra=payload)
