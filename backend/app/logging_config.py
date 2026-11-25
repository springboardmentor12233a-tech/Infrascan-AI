"""Structured JSON Logging Configuration for InfraScan.

Formats all application logs as structured JSON objects containing:
- timestamp (ISO-8601 UTC)
- level (INFO, WARN, ERROR, DEBUG)
- logger (module name)
- message
- request_id (UUID propagated from request header or generated)
- user_id (if authenticated)
- path, method, status_code, latency_ms (for request traces)
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import sys
from typing import Any, Dict, Optional
import uuid

# Context variables for per-request tracing
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)


class JSONFormatter(logging.Formatter):
    """Custom JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        req_id = request_id_ctx.get()
        if req_id:
            log_obj["request_id"] = req_id

        u_id = user_id_ctx.get()
        if u_id is not None:
            log_obj["user_id"] = u_id

        # Attach extra structured fields if present
        for key in ["method", "path", "status_code", "latency_ms", "model_id"]:
            if hasattr(record, key):
                log_obj[key] = getattr(record, key)

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def configure_logging():
    """Configure root logger to use JSONFormatter."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Avoid adding duplicate handlers
    if not any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, JSONFormatter) for h in root.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        root.handlers = [handler]
