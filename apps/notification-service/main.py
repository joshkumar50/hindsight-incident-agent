import asyncio

from pkg.core.config import get_config
from pkg.core.logging import configure_logging
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("notification-service")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")


async def handle_order_event(event_type: str, payload: dict, message_id: str):
    logger.info(
        "received_event", event_type=event_type, payload=payload, message_id=message_id
    )
    if event_type == "ORDER_PLACED":
        logger.info("sending_email", order_id=payload.get("order_id"))
        await asyncio.sleep(0.5)  # Simulate email send time
        logger.info("email_sent")


from fastapi import FastAPI
from pkg.core.health import register_health_endpoints

app = FastAPI(title="Notification Service")
register_health_endpoints(app, "notification-service")

@app.on_event("startup")
async def startup_event():
    logger.info("Notification Service starting...")
    await event_bus.connect()

    logger.info("Starting consumer loop on 'order_events'...")
    asyncio.create_task(event_bus.consume(
        stream="order_events",
        group="notification_group",
        consumer="notifier_1",
        callback=handle_order_event,
    ))
