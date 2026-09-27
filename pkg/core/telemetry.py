import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger("telemetry")


def bootstrap_telemetry(app: FastAPI, service_name: str, otlp_endpoint: str):
    """
    Bootstraps both Prometheus metrics and OpenTelemetry tracing for a FastAPI app.
    Ensures complete request instrumentation.
    """
    # 1. Prometheus Metrics Setup
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/readiness", "/liveness"],
        env_var_name="ENABLE_METRICS",
    )
    instrumentator.instrument(app).expose(app, endpoint="/metrics")

    # 2. OpenTelemetry Tracing Setup
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            # We attempt to setup OTLP but with a very short timeout or we catch socket errors.
            # BatchSpanProcessor exports in the background, but OTLPSpanExporter can block resolving the endpoint.
            import socket
            from urllib.parse import urlparse
            
            parsed_url = urlparse(otlp_endpoint)
            host = parsed_url.hostname
            # Pre-flight DNS check to avoid blocking the main thread
            socket.gethostbyname(host)
            
            processor = BatchSpanProcessor(
                OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            )
            provider.add_span_processor(processor)
            logger.info(f"OTel exporter configured for endpoint {otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP Exporter to {otlp_endpoint}, continuing without tracing: {e}")

    trace.set_tracer_provider(provider)

    try:
        # Actually instrument the FastAPI app for automatic HTTP spans
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI app: {e}")

    return trace.get_tracer(service_name)
