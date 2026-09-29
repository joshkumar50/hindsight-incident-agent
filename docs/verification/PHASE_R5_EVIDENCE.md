# PHASE_R5_EVIDENCE.md

## Step 1 Output
```
--- STEP 1 ---
top score: 1.0972866997123532
top text: Incident INC-044 occurred on 2026-09-29, involving an auth-service pod OOMKill due to a 128Mi memory limit, causing a pod restart loop, 502 errors on /auth/validate, and a 5000ms latency spike; it was
Unclosed client session
client_session: <aiohttp.client.ClientSession object at 0x0000020697AE3A10>
Unclosed connector
connections: ['[(<aiohttp.client_proto.ResponseHandler object at 0x00000206994B21B0>, 11275.2041726)]']
connector: <aiohttp.connector.TCPConnector object at 0x0000020697AE3620>
```

## Step 2 Output
```
--- STEP 2 ---
C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\opentelemetry\instrumentation\dependencies.py:4: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  from pkg_resources import (
Failed to configure OTLP Exporter to http://otel-collector.incident-agent-observability.svc.cluster.local:4317, continuing without tracing: [Errno 11001] getaddrinfo failed
{"base_url": "https://api.hindsight.vectorize.io", "event": "hindsight_enabled", "level": "info", "logger": "ai-orchestrator", "timestamp": "2026-09-29T06:30:44.269646Z"}
orchestrator imports ok
```

## Step 3 Output
```
--- STEP 3 ---
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\chitt\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\KubePilot\KubePilot-Autonomous-Kubernetes-SRE-Platform
plugins: anyio-4.9.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit FAILED [100%]

================================== FAILURES ===================================
_____________________________ test_e2e_memory_hit _____________________________

    @pytest.mark.asyncio
    async def test_e2e_memory_hit():
        # Mock event_bus.publish
        with patch.object(main.event_bus, 'publish', new_callable=AsyncMock) as mock_publish:
            # We also mock httpx.AsyncClient.post just in case it falls through,
            # so we can assert it was NOT called.
            with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
                payload = {
                    "incident_id": "TEST-123",
                    "description": "auth-service OOMKilled pod restart loop"
                }
    
                await main.coordinate_ai_workflow('INCIDENT_DECLARED', payload, 'msg-1')
    
                # Assert RCA was NOT called
>               mock_post.assert_not_called()

platform\ai-orchestrator\tests\test_e2e_memory_hit.py:20: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

self = <AsyncMock name='post' id='2303975867792'>

    def assert_not_called(self):
        """assert that the mock was never called.
        """
        if self.call_count != 0:
            msg = ("Expected '%s' to not have been called. Called %s times.%s"
                   % (self._mock_name or 'mock',
                      self.call_count,
                      self._calls_repr()))
>           raise AssertionError(msg)
E           AssertionError: Expected 'post' to not have been called. Called 1 times.
E           Calls: [call('http://root-cause-analysis-engine.incident-agent-system.svc.cluster.local/analyze', json={'incident_id': 'TEST-123', 'description': 'auth-service OOMKilled pod restart loop'}),
E            call().json()].

C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\unittest\mock.py:940: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  ai-orchestrator:main.py:130 {"incident_id": "TEST-123", "error": "This event loop is already running", "event": "hindsight_recall_failed", "level": "warning", "logger": "ai-orchestrator", "timestamp": "2026-09-29T06:30:48.787303Z"}
ERROR    ai-orchestrator:main.py:220 {"incident_id": "TEST-123", "error": "'coroutine' object has no attribute 'get'", "event": "orchestration_failed", "level": "error", "logger": "ai-orchestrator", "timestamp": "2026-09-29T06:30:49.187006Z"}
============================== warnings summary ===============================
<frozen importlib._bootstrap>:488
  <frozen importlib._bootstrap>:488: DeprecationWarning: Type google._upb._message.MessageMapContainer uses PyType_Spec with a metaclass that has custom tp_new. This is deprecated and will no longer be allowed in Python 3.14.

<frozen importlib._bootstrap>:488
  <frozen importlib._bootstrap>:488: DeprecationWarning: Type google._upb._message.ScalarMapContainer uses PyType_Spec with a metaclass that has custom tp_new. This is deprecated and will no longer be allowed in Python 3.14.

C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\opentelemetry\instrumentation\dependencies.py:4
  C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\opentelemetry\instrumentation\dependencies.py:4: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
    from pkg_resources import (

C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\pkg_resources\__init__.py:3146
  C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\pkg_resources\__init__.py:3146: DeprecationWarning: Deprecated call to `pkg_resources.declare_namespace('google')`.
  Implementing implicit namespace packages (as specified in PEP 420) is preferred to `pkg_resources.declare_namespace`. See https://setuptools.pypa.io/en/latest/references/keywords.html#keyword-namespace-packages
    declare_namespace(pkg)

C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\structlog\processors.py:480
platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit
platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit
platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit
  C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\structlog\processors.py:480: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    return datetime.datetime.utcnow()

platform\ai-orchestrator\main.py:233
  d:\KubePilot\KubePilot-Autonomous-Kubernetes-SRE-Platform\platform\ai-orchestrator\main.py:233: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\applications.py:4495
  C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\fastapi\applications.py:4495: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)

platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit
  d:\KubePilot\KubePilot-Autonomous-Kubernetes-SRE-Platform\platform\ai-orchestrator\main.py:130: RuntimeWarning: coroutine 'Hindsight.arecall' was never awaited
    logger.warning(
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit
  D:\KubePilot\KubePilot-Autonomous-Kubernetes-SRE-Platform\platform\ai-orchestrator\tests\test_e2e_memory_hit.py:17: RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
    await main.coordinate_ai_workflow('INCIDENT_DECLARED', payload, 'msg-1')
  Enable tracemalloc to get traceback where the object was allocated.
  See https://docs.pytest.org/en/stable/how-to/capture-warnings.html#resource-warnings for more info.

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED platform/ai-orchestrator/tests/test_e2e_memory_hit.py::test_e2e_memory_hit
======================= 1 failed, 12 warnings in 4.33s ========================
```
