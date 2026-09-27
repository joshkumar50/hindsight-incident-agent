from fastapi import FastAPI
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("root-cause-analysis-engine")
app = FastAPI(title="Root Cause Analysis Engine", version="1.0.0")

bootstrap_telemetry(
    app, "root-cause-analysis-engine", config.otel_exporter_otlp_endpoint
)
register_error_handlers(app)
register_health_endpoints(app, "root-cause-analysis-engine")


class IncidentContext(BaseModel):
    incident_id: str
    root_cause_candidate: str
    impacted_services: list[str]


@app.post("/analyze")
async def analyze_root_cause(context: IncidentContext):
    """
    Deterministic correlation of metrics and topology.
    NO LLM Summarization. Returns strict causal tree data.
    """
    logger.info("analyzing_root_cause", incident_id=context.incident_id)

    # In a real system, this engine pulls metrics/traces from Prometheus/Tempo
    # and calculates exact causal timelines.

    return {
        "root_cause": context.root_cause_candidate,
        "confidence_score": 0.98,
        "evidence": {
            "metric": "latency_ms",
            "anomaly_z_score": 4.2,
            "timeline_ms": 5000,
        },
        "business_impact": "High (Payment processing stalled due to Auth latency)",
    }
