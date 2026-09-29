import httpx
from fastapi import FastAPI, Header
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import HindsightIncidentAgentException, register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("order-service")

app = FastAPI(title="Order Service", version="1.0.0")

bootstrap_telemetry(app, "order-service", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "order-service")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")


class OrderItem(BaseModel):
    item_id: str
    quantity: int


class OrderRequest(BaseModel):
    items: list[OrderItem]


@app.on_event("startup")
async def startup():
    await event_bus.connect()
    logger.info("Order Service started")


@app.post("/order/place")
async def place_order(request: OrderRequest, authorization: str = Header(None)):
    logger.info("placing_order", items=len(request.items))

    # 1. Deduct Inventory (Synchronous REST call)
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            inv_url = "http://inventory-service.hindsight-agent-apps.svc.cluster.local/inventory/deduct"
            inv_res = await client.post(
                inv_url, json={"items": [i.model_dump() for i in request.items]}
            )
            inv_res.raise_for_status()
    except Exception as e:
        logger.error("inventory_service_failed", error=str(e))
        raise HindsightIncidentAgentException("Inventory check failed", "INVENTORY_ERROR", 500)

    # 2. Process Payment (Synchronous REST call)
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            pay_url = "http://payment-service.hindsight-agent-apps.svc.cluster.local/payment/process"
            pay_res = await client.post(
                pay_url,
                json={"amount": 99.99, "currency": "USD"},
                headers={"Authorization": authorization},
            )
            pay_res.raise_for_status()
    except Exception as e:
        logger.error("payment_service_failed", error=str(e))
        # If payment fails, we ideally rollback inventory, but skipping for demo simplicity
        raise HindsightIncidentAgentException("Payment processing failed", "PAYMENT_ERROR", 500)

    # 3. Publish Async Event for Notification
    await event_bus.publish(
        "order_events", "ORDER_PLACED", {"order_id": "ord_999", "status": "completed"}
    )

    return {"status": "order_placed", "order_id": "ord_999"}
