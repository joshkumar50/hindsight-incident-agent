import os

pkg_files = {
    "pkg/__init__.py": '"""Minimal pkg initialization."""\n',
    "pkg/core/__init__.py": '"""Minimal core initialization."""\n',
    "pkg/core/config.py": '''"""Minimal config module."""
import os

class Config:
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.otel_exporter_otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

def get_config():
    return Config()
''',
    "pkg/core/logging.py": '''"""Minimal logging module."""
import logging

def configure_logging(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
''',
    "pkg/core/health.py": '''"""Minimal health module."""

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
''',
    "pkg/core/telemetry.py": '''"""Minimal telemetry module."""

def bootstrap_telemetry(app, name: str, endpoint: str):
    pass  # No-op if endpoint missing
''',
    "pkg/core/errors.py": '''"""Minimal errors module."""

class HindsightIncidentAgentException(Exception):
    def __init__(self, message, error_code=None, status_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = {}

def register_error_handlers(app):
    pass
''',
    "pkg/eventbus/__init__.py": '"""Minimal eventbus initialization."""\n',
    "pkg/eventbus/client.py": '''"""Minimal eventbus client."""
import asyncio

class EventBusClient:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client = None
        self.redis = None

    async def connect(self):
        try:
            import redis.asyncio as redis
            self.client = redis.from_url(self.redis_url)
            self.redis = self.client
        except ImportError:
            pass

    async def publish(self, stream: str, event_type: str, payload: dict):
        pass

    async def consume(self, stream: str, group: str, consumer: str, callback):
        pass
''',
    "pkg/math_engine/__init__.py": '"""Minimal math_engine initialization."""\n',
    "pkg/math_engine/anomaly.py": '''"""Minimal anomaly detection module."""

class RollingStatistics:
    def __init__(self, window_size: int):
        self.window_size = window_size
        self.values = []

    def update(self, value: float):
        self.values.append(value)
        if len(self.values) > self.window_size:
            self.values.pop(0)
        return 0.0  # Dummy z-score
'''
}

for path, content in pkg_files.items():
    full_path = os.path.join(r"f:\temp\KubePilot", path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
print("Files created.")
