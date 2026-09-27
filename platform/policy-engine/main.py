from fastapi import FastAPI
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("policy-engine")
app = FastAPI(title="Policy Engine", version="1.0.0")

bootstrap_telemetry(app, "policy-engine", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "policy-engine")


class PolicyRequest(BaseModel):
    target: str
    action: str


@app.post("/authorize")
async def authorize_action(req: PolicyRequest):
    """
    Deterministic rule-based policy engine.
    Ensures that AI does not execute destructive commands on critical namespaces.
    """
    logger.info("evaluating_policy", target=req.target, action=req.action)

    # Example deterministic policy
    critical_targets = ["api-gateway", "postgres-db", "redis-master"]

    if req.target in critical_targets:
        logger.warn("policy_rejected_critical_target", target=req.target)
        return {"authorized": False, "reason": "Target is marked as CRITICAL."}

    logger.info("policy_approved", target=req.target)
    return {"authorized": True, "reason": "Target is non-critical, action approved."}
