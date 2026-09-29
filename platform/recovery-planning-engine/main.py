from fastapi import FastAPI
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("recovery-planning-engine")
app = FastAPI(title="Recovery Planning Engine", version="1.0.0")

bootstrap_telemetry(app, "recovery-planning-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "recovery-planning-engine")


class PlanContext(BaseModel):
    decision: dict


@app.post("/plan")
async def generate_plan(context: PlanContext):
    """
    Generates the execution workflow for the authorized recovery action.
    """
    logger.info("generating_recovery_plan")

    context.decision.get("authorized_action")
    target = context.decision.get("target")

    return {
        "workflow": [
            {
                "step": 1,
                "command": f"kubectl rollout restart deployment {target} -n hindsight-agent-apps",
            },
            {"step": 2, "command": "verify_health_probes"},
            {"step": 3, "command": "verify_metrics_normalized"},
        ],
        "estimated_mttr": "45 seconds",
        "rollback_procedure": "If health probes fail after 120s, escalate to human.",
    }
