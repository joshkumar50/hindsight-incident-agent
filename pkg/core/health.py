from typing import Any, Callable, Coroutine, List

from fastapi import FastAPI, Response
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    details: dict[str, str] = {}


def register_health_endpoints(
    app: FastAPI,
    service_name: str,
    readiness_checks: List[Callable[[], Coroutine[Any, Any, bool]]] = None,
):
    """
    Standardizes health check endpoints for Kubernetes.
    Supports a list of readiness checks (e.g., [check_db, check_redis]).
    """

    @app.get("/health", response_model=HealthResponse, tags=["Observability"])
    async def health():
        return HealthResponse(status="ok", service=service_name)

    @app.get("/liveness", response_model=HealthResponse, tags=["Observability"])
    async def liveness():
        return HealthResponse(status="ok", service=service_name)

    @app.get("/readiness", response_model=HealthResponse, tags=["Observability"])
    async def readiness(response: Response):
        if readiness_checks:
            for i, check in enumerate(readiness_checks):
                is_ready = await check()
                if not is_ready:
                    response.status_code = 503
                    return HealthResponse(
                        status="unavailable",
                        service=service_name,
                        details={"reason": f"dependency_check_{i}_failed"},
                    )
        return HealthResponse(status="ready", service=service_name)

    @app.get("/ready", response_model=HealthResponse, tags=["Observability"])
    async def ready_alias(response: Response):
        return await readiness(response)
