import httpx
from fastapi import FastAPI, Header
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import HindsightIncidentAgentException, register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("payment-service")

app = FastAPI(title="Payment Service", version="1.0.0")

bootstrap_telemetry(app, "payment-service", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "payment-service")


class PaymentRequest(BaseModel):
    amount: float
    currency: str


@app.on_event("startup")
async def startup():
    logger.info("Payment Service started")


@app.post("/payment/process")
async def process_payment(request: PaymentRequest, authorization: str = Header(None)):
    logger.info("processing_payment", amount=request.amount)

    # Crucial cascading failure logic: Payment service has a strict 3-second timeout to Auth.
    # If Auth is suffering from chaos (5 second delay), Payment WILL crash.
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            auth_url = (
                "http://auth-service.hindsight-agent-apps.svc.cluster.local/auth/validate"
            )
            response = await client.get(
                auth_url, headers={"Authorization": authorization}
            )
            response.raise_for_status()
    except httpx.ReadTimeout:
        logger.error("auth_service_timeout", timeout=3.0)
        raise HindsightIncidentAgentException(
            message="Upstream authentication service timed out",
            error_code="UPSTREAM_TIMEOUT",
            status_code=504,
        )
    except httpx.HTTPStatusError as e:
        logger.error("auth_service_error", status_code=e.response.status_code)
        raise HindsightIncidentAgentException(
            message="Upstream authentication failed",
            error_code="AUTH_FAILED",
            status_code=401,
        )
    except Exception as e:
        logger.error("auth_service_unavailable", error=str(e))
        raise HindsightIncidentAgentException(
            message="Authentication service unavailable",
            error_code="UPSTREAM_UNAVAILABLE",
            status_code=502,
        )

    # Proceed with payment
    return {"status": "success", "transaction_id": "txn_123456"}
