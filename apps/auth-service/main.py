import asyncio

from fastapi import FastAPI, Header
from pydantic import BaseModel

from pkg.core.config import get_config
from pkg.core.errors import HindsightIncidentAgentException, register_error_handlers
from pkg.core.health import register_health_endpoints
from pkg.core.logging import configure_logging
from pkg.core.telemetry import bootstrap_telemetry
from pkg.eventbus.client import EventBusClient

config = get_config()
logger = configure_logging("auth-service")

app = FastAPI(title="Auth Service", version="1.0.0")

# Apply enterprise framework
bootstrap_telemetry(app, "auth-service", config.otel_exporter_otlp_endpoint)
register_error_handlers(app)
register_health_endpoints(app, "auth-service")

event_bus = EventBusClient(f"redis://{config.redis_host}:{config.redis_port}")

# Global state for chaos injection
chaos_active = False


class LoginRequest(BaseModel):
    username: str
    password: str


@app.on_event("startup")
async def startup():
    await event_bus.connect()
    logger.info("Auth Service started")


@app.post("/auth/login")
async def login(request: LoginRequest):
    logger.info("login_attempt", username=request.username)
    if chaos_active:
        # Simulate cascading failure trigger: Auth becomes extremely slow
        logger.warn("chaos_active_delay_injected", delay=5.0)
        await asyncio.sleep(5.0)

    if request.username == "admin" and request.password == "password":
        await event_bus.publish(
            "auth_events", "LOGIN_SUCCESS", {"user": request.username}
        )
        return {"token": "valid_token"}

    await event_bus.publish("auth_events", "LOGIN_FAILED", {"user": request.username})
    raise HindsightIncidentAgentException(
        message="Invalid credentials", error_code="AUTH_FAILED", status_code=401
    )


@app.get("/auth/validate")
async def validate(authorization: str = Header(None)):
    if not authorization or authorization != "Bearer valid_token":
        raise HindsightIncidentAgentException(
            message="Invalid token", error_code="UNAUTHORIZED", status_code=401
        )

    if chaos_active:
        logger.warn("chaos_active_delay_injected", delay=5.0)
        await asyncio.sleep(5.0)

    return {"user": "admin", "role": "superuser"}


@app.post("/auth/chaos/enable")
async def enable_chaos():
    global chaos_active
    chaos_active = True
    logger.critical("chaos_enabled", component="auth-service")
    return {"status": "chaos_enabled"}


@app.post("/auth/chaos/disable")
async def disable_chaos():
    global chaos_active
    chaos_active = False
    logger.info("chaos_disabled", component="auth-service")
    return {"status": "chaos_disabled"}
