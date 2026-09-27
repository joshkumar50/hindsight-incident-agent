from fastapi import FastAPI
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry

config = get_config()
logger = configure_logging("inventory-service")

app = FastAPI(title="Inventory Service", version="1.0.0")

bootstrap_telemetry(app, "inventory-service", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "inventory-service")


class InventoryItem(BaseModel):
    item_id: str
    quantity: int


class InventoryRequest(BaseModel):
    items: list[InventoryItem]


@app.on_event("startup")
async def startup():
    logger.info("Inventory Service started")


@app.post("/inventory/deduct")
async def deduct_inventory(request: InventoryRequest):
    logger.info("deducting_inventory", items=len(request.items))
    # Mock inventory deduction success
    return {"status": "deducted"}
