import logging
import logging.config
import sys
import time
import uuid
import random
from contextvars import ContextVar
from typing import Any, Dict, MutableMapping, Tuple

import structlog
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.middlewares.correlation import correlation_id



if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

EventDict: TypeAlias = MutableMapping[str, Any]

LOG_LEVEL = "DEBUG" if settings.DEBUG else settings.LOG_LEVEL



SLOW_REQUEST_MS = getattr(settings, "SLOW_REQUEST_MS", 800)
VERY_SLOW_REQUEST_MS = getattr(settings, "VERY_SLOW_REQUEST_MS", 2000)
SLOW_DB_MS = getattr(settings, "SLOW_DB_MS", 300)
INFO_SAMPLE_RATE = getattr(settings, "INFO_SAMPLE_RATE", 0.3)



trace_id_ctx: ContextVar[str | None] = ContextVar("trace_id", default=None)
span_id_ctx: ContextVar[str | None] = ContextVar("span_id", default=None)


# =========================
# Structlog processors
# =========================

def add_correlation_id(_, __, event_dict: EventDict) -> EventDict:
    cid = correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def add_trace_context(_, __, event_dict: EventDict) -> EventDict:
    trace_id = trace_id_ctx.get()
    span_id = span_id_ctx.get()

    if trace_id:
        event_dict["trace_id"] = trace_id
    if span_id:
        event_dict["span_id"] = span_id

    return event_dict


def remove_color_message(_, __, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def info_sampler(_, __, event_dict: EventDict) -> EventDict:

    if settings.DEBUG:
        return event_dict

    if event_dict.get("level") == "info" and random.random() > INFO_SAMPLE_RATE:
        raise structlog.DropEvent

    return event_dict


SHARED_PROCESSORS: Tuple[structlog.typing.Processor, ...] = (
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.ExtraAdder(),
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    remove_color_message,
    add_correlation_id,
    add_trace_context,
)


LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(
                sort_keys=True,
                ensure_ascii=False,
            ),
            "foreign_pre_chain": SHARED_PROCESSORS,
        },
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                remove_color_message,
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(
                    colors=True,
                    exception_formatter=structlog.dev.plain_traceback,
                ),
            ],
            "foreign_pre_chain": SHARED_PROCESSORS,
        },
        **uvicorn.config.LOGGING_CONFIG["formatters"],
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "level": LOG_LEVEL,
            "formatter": "console" if settings.DEBUG else "json",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "uvicorn.error": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "uvicorn.access": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


def configure_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *SHARED_PROCESSORS,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            info_sampler,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )



db_logger = structlog.get_logger("db")


class DBTimer:
    """
    Use for DB / Redis / HTTP / file IO timing.
    """
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        duration_ms = (time.perf_counter() - self.start) * 1000
        if duration_ms >= SLOW_DB_MS:
            db_logger.warning(
                "slow_operation",
                duration_ms=round(duration_ms, 2),
            )
