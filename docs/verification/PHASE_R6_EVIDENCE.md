# PHASE_R6_EVIDENCE.md

## `arecall` and `aretain` check in ai-orchestrator
```
--- AI arecall/aretain ---

platform\ai-orchestrator\main.py:28:#   arecall(bank_id: str, query: str, ...) -> RecallResponse
platform\ai-orchestrator\main.py:29:#   aretain(bank_id: str, content: str | list[dict], ...) -> RetainResponse
platform\ai-orchestrator\main.py:74:                memory_results = await hindsight.arecall(
platform\ai-orchestrator\main.py:203:                        await hindsight.aretain(
```

## `arecall` and `aretain` check in knowledge-engine
```
--- KE arecall/aretain ---
platform\knowledge-engine\main.py:77:        results = await hindsight.arecall(
platform\knowledge-engine\main.py:115:        await hindsight.aretain(
```

## Sync methods check
```
--- AI sync check ---
```
(No output for sync methods, meaning they are fully gone from the codebase).

## Syntax Checks
```
ai syntax ok
ke syntax ok
```

## Pytest run for test_e2e_memory_hit.py
```
--- Pytest ---
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\chitt\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\KubePilot\KubePilot-Autonomous-Kubernetes-SRE-Platform\platform\ai-orchestrator
plugins: anyio-4.9.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 1 item

tests/test_e2e_memory_hit.py::test_e2e_memory_hit PASSED                 [100%]

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
tests/test_e2e_memory_hit.py::test_e2e_memory_hit
tests/test_e2e_memory_hit.py::test_e2e_memory_hit
tests/test_e2e_memory_hit.py::test_e2e_memory_hit
  C:\Users\chitt\AppData\Local\Programs\Python\Python313\Lib\site-packages\structlog\processors.py:480: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    return datetime.datetime.utcnow()

main.py:233
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

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 1 passed, 10 warnings in 11.77s =======================
```
