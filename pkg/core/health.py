"""Minimal health module."""

def register_health_endpoints(app, name: str = None):
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    @app.get("/liveness")
    async def liveness():
        return {"status": "ok"}
    @app.get("/readiness")
    async def readiness():
        return {"status": "ok"}
