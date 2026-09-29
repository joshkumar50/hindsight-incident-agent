"""
conftest.py — stubs out heavy/unavailable dependencies before any test
module imports `main`. This prevents ImportError from pkg.core.* and
opentelemetry, which are not installed in the local dev/CI environment.

All stubs return no-op callables/objects so the FastAPI app constructs
cleanly and routes can be tested in isolation.
"""
import sys
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Stub opentelemetry top-level and sub-packages
# ---------------------------------------------------------------------------
for mod_name in [
    "opentelemetry",
    "opentelemetry.trace",
    "opentelemetry.sdk",
    "opentelemetry.sdk.trace",
    "opentelemetry.sdk.trace.export",
    "opentelemetry.exporter",
    "opentelemetry.exporter.otlp",
    "opentelemetry.exporter.otlp.proto",
    "opentelemetry.exporter.otlp.proto.grpc",
    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter",
    "opentelemetry.instrumentation",
    "opentelemetry.instrumentation.fastapi",
    "opentelemetry.instrumentation.httpx",
    "opentelemetry.instrumentation.redis",
    "opentelemetry.propagate",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# ---------------------------------------------------------------------------
# 2. Stub structlog (used by pkg.core.logging)
# ---------------------------------------------------------------------------
if "structlog" not in sys.modules:
    sys.modules["structlog"] = MagicMock()
    sys.modules["structlog.stdlib"] = MagicMock()
    sys.modules["structlog.processors"] = MagicMock()

# ---------------------------------------------------------------------------
# 3. Stub pkg.core.* modules so that `from pkg.core.X import Y` works
# ---------------------------------------------------------------------------
def _make_pkg_stub(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__path__ = []
    return mod


for pkg_name in ["pkg", "pkg.core", "pkg.eventbus", "pkg.telemetry",
                 "pkg.math_engine", "pkg.security"]:
    if pkg_name not in sys.modules:
        sys.modules[pkg_name] = _make_pkg_stub(pkg_name)

# pkg.core.config
_config_mod = types.ModuleType("pkg.core.config")

class _FakeConfig:
    redis_host = "localhost"
    redis_port = 6379
    otel_exporter_otlp_endpoint = "http://localhost:4317"

_config_mod.get_config = lambda: _FakeConfig()
sys.modules["pkg.core.config"] = _config_mod

# pkg.core.logging
_logging_mod = types.ModuleType("pkg.core.logging")
_logging_mod.configure_logging = lambda service_name, **kw: MagicMock()
sys.modules["pkg.core.logging"] = _logging_mod

# pkg.core.errors
_errors_mod = types.ModuleType("pkg.core.errors")
_errors_mod.register_error_handlers = lambda app: None
_errors_mod.ErrorResponse = MagicMock()
_errors_mod.HindsightIncidentAgentException = Exception
sys.modules["pkg.core.errors"] = _errors_mod

# pkg.core.health
_health_mod = types.ModuleType("pkg.core.health")
_health_mod.register_health_endpoints = lambda app, name: None
sys.modules["pkg.core.health"] = _health_mod

# pkg.core.telemetry
_telemetry_mod = types.ModuleType("pkg.core.telemetry")
_telemetry_mod.bootstrap_telemetry = lambda app, name, endpoint: None
sys.modules["pkg.core.telemetry"] = _telemetry_mod

# pkg.eventbus.client
_eventbus_mod = types.ModuleType("pkg.eventbus.client")
_eventbus_mod.EventBusClient = MagicMock
sys.modules["pkg.eventbus.client"] = _eventbus_mod

# ---------------------------------------------------------------------------
# 4. Stub hindsight_client (conditional import in main.py)
# ---------------------------------------------------------------------------
if "hindsight_client" not in sys.modules:
    sys.modules["hindsight_client"] = MagicMock()
