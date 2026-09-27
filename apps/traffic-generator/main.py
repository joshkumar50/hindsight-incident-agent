import asyncio
import logging
import random
import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.core.health import register_health_endpoints

configure_logging("traffic-generator")
logger = logging.getLogger("traffic-generator")

app = FastAPI(title="Traffic Generator")
bootstrap_telemetry(app, "traffic-generator", os.getenv("OTEL_ENDPOINT", "http://otel-collector.incident-agent-observability.svc.cluster.local:4317"))

class TrafficConfig(BaseModel):
    mode: str = "normal"  # normal, burst, constant, random, high_latency, mixed
    rate: int = 10        # requests per second
    target_url: str = "http://api-gateway.hindsight-agent-apps.svc.cluster.local"

class TrafficState:
    def __init__(self):
        self.is_running = False
        self.config = TrafficConfig()

state = TrafficState()
register_health_endpoints(app, "traffic-generator")

# Proper POST payloads for each route — avoids 405/422 errors from GET on POST-only routes
ENDPOINTS = [
    ("POST", "/auth/login",       {"username": "demo_user", "password": "demo_pass"}),
    ("POST", "/payment/process",  {"order_id": "gen-001", "amount": 9.99, "currency": "USD"}),
    ("POST", "/orders/create",    {"item_id": "sku-42", "quantity": 1, "customer_id": "cust-1"}),
    ("GET",  "/inventory/check",  None),
]

async def send_requests(count: int, mixed: bool = False):
    # Create client inside the coroutine (event-loop safe)
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for _ in range(count):
            method, path, body = random.choice(ENDPOINTS) if mixed else ENDPOINTS[0]
            url = f"{state.config.target_url}{path}"
            if method == "POST":
                tasks.append(client.post(url, json=body))
            else:
                tasks.append(client.get(url))
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successes = sum(
                1 for r in results
                if not isinstance(r, Exception) and r.status_code in (200, 201)
            )
            logger.info(f"Traffic cycle: Sent {count} requests. Success: {successes}")
        except Exception as e:
            logger.error(f"Traffic generation error: {e}")

async def generate_traffic():
    while state.is_running:
        if state.config.mode == "burst":
            await send_requests(state.config.rate * 5)
            await asyncio.sleep(5)
        elif state.config.mode == "mixed":
            await send_requests(random.randint(1, state.config.rate), mixed=True)
            await asyncio.sleep(1)
        else:  # normal, constant, random, high_latency
            rate = random.randint(1, state.config.rate * 2) if state.config.mode == "random" else state.config.rate
            await send_requests(rate)
            await asyncio.sleep(1)

@app.post("/start")
async def start_traffic(config: Optional[TrafficConfig] = None):
    if state.is_running:
        raise HTTPException(status_code=400, detail="Traffic generation is already running")
    if config:
        state.config = config
    state.is_running = True
    asyncio.create_task(generate_traffic())
    logger.info(f"Started traffic generation in {state.config.mode} mode at {state.config.rate} req/s")
    return {"status": "started", "config": state.config.dict()}

@app.post("/stop")
async def stop_traffic():
    state.is_running = False
    logger.info("Stopped traffic generation")
    return {"status": "stopped"}

@app.get("/status")
async def get_status():
    return {"is_running": state.is_running, "config": state.config.dict()}
