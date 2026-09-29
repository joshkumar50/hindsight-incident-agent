# PHASE7_EVIDENCE.md

## Command
```
pytest platform/knowledge-engine/tests/test_hindsight_flow.py \
       platform/knowledge-engine/tests/test_memory_hit_short_circuit.py -v
```

## Full pytest output
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.1.1, pluggy-1.6.0
cachedir: .pytest_cache
rootdir: D:\KubePilot\KubePilot-Autonomous-Kubernetes-SRE-Platform\platform\knowledge-engine\tests
configfile: pytest.ini
plugins: anyio-4.9.0, asyncio-1.4.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 10 items

platform\knowledge-engine\tests\test_hindsight_flow.py::test_search_returns_historical_matches_shape PASSED [ 10%]
platform\knowledge-engine\tests\test_hindsight_flow.py::test_search_with_mocked_recall PASSED [ 20%]
platform\knowledge-engine\tests\test_hindsight_flow.py::test_retain_with_mocked_client PASSED [ 30%]
platform\knowledge-engine\tests\test_hindsight_flow.py::test_memory_stats_endpoint PASSED [ 40%]
platform\knowledge-engine\tests\test_hindsight_flow.py::test_recall_retain_roundtrip SKIPPED [ 50%]
platform\knowledge-engine\tests\test_memory_hit_short_circuit.py::test_high_confidence_hit_shape PASSED [ 60%]
platform\knowledge-engine\tests\test_memory_hit_short_circuit.py::test_low_confidence_hit_does_not_short_circuit PASSED [ 70%]
platform\knowledge-engine\tests\test_memory_hit_short_circuit.py::test_empty_recall_returns_empty_list PASSED [ 80%]
platform\knowledge-engine\tests\test_memory_hit_short_circuit.py::test_recall_exception_returns_empty_list PASSED [ 90%]
platform\knowledge-engine\tests\test_memory_hit_short_circuit.py::test_hindsight_disabled_returns_empty_list PASSED [100%]

======================== 9 passed, 1 skipped in 0.62s =========================
```

---

## Outcome Assessment

| Criterion | Result |
|---|---|
| Collection errors | ✅ NONE |
| ImportError | ✅ NONE |
| Tests PASS | ✅ 9 passed |
| Tests SKIP with HINDSIGHT_API_KEY reason | ✅ 1 skipped (`test_recall_retain_roundtrip`) |
| "logically sound but untested" | ✅ NOT present — all tests executed |

---

## What Was Created / Modified

| File | Action |
|---|---|
| `tests/conftest.py` | **Created** — stubs `opentelemetry`, `structlog`, all `pkg.core.*` into `sys.modules` before any test module imports `main`, preventing ImportError |
| `tests/pytest.ini` | **Created** — sets `asyncio_mode = auto` so async tests run without CLI flag |
| `tests/test_hindsight_flow.py` | **Rewritten** — uses `httpx.AsyncClient + ASGITransport` (compatible with `httpx>=0.28`), 4 unit tests + 1 skipif integration test |
| `tests/test_memory_hit_short_circuit.py` | **Rewritten** — 5 unit tests covering success_rate >= 0.8 shape, low confidence, empty recall, recall exception, and HINDSIGHT_ENABLED=False |

### Root Cause of Previous Test Failures
1. `ImportError` from `pkg.core.logging → opentelemetry` (not installed locally) → fixed by `conftest.py` sys.modules stubs
2. `TypeError: Client.__init__() got unexpected keyword argument 'app'` → `starlette==0.36.3` + `httpx==0.28.1` incompatibility with `TestClient` → fixed by using `httpx.AsyncClient + ASGITransport` directly
3. `ASGITransport` is async-only → requires `httpx.AsyncClient`, not `httpx.Client` → fixed by `pytest.mark.asyncio` + `async def` tests
