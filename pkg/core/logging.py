import logging
import sys

import structlog
from opentelemetry import trace


def add_otel_trace_id(logger, log_method, event_dict):
    """Extracts OpenTelemetry trace_id and span_id and injects into structlog JSON."""
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging(service_name: str, level: str = "INFO"):
    """
    Configures enterprise-grade JSON logging using structlog.
    Intercepts Uvicorn/FastAPI logs and injects OpenTelemetry Trace IDs.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            add_otel_trace_id,  # Inject trace IDs for EDA correlation
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(service_name)
