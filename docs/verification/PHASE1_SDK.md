# PHASE1_SDK.md — Hindsight SDK API Verification

## 1. Package Installation

**Command:** `pip install hindsight-client`
**Result:** ✅ SUCCESS — `hindsight-client==0.10.1` installed.
**Package name on PyPI:** `hindsight-client`
**Import module name:** `hindsight_client`

No fallback packages (`vectorize-hindsight`, `hindsight`) were needed.

---

## 2. Raw Command Outputs

### `python -c "import hindsight_client; print(hindsight_client.__file__)"`
```
C:\Users\chitt\AppData\Local\Temp\hs_verify\Lib\site-packages\hindsight_client\__init__.py
```

### `python -c "import hindsight_client; print(dir(hindsight_client))"`
```
['BankProfileResponse', 'DispositionTraits', 'Hindsight', 'ListMemoryUnitsResponse', 
'RecallResponse', 'RecallResult', 'ReflectFact', 'ReflectResponse', 'RetainResponse', 
'VersionResponse', '_RecallResponse', '_RecallResult', '__all__', '__builtins__', 
'__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', 
'__path__', '__spec__', '_recall_response_getitem', '_recall_response_iter', 
'_recall_response_len', '_recall_response_to_prompt_string', '_recall_result_repr', 
'hindsight_client']
```

### `inspect.signature(Hindsight.__init__)`
```
(self, base_url: str, api_key: str | None = None, timeout: float = 300.0, 
 user_agent: str | None = None, max_attempts: int = 3)
```

### `[m for m in dir(Hindsight) if not m.startswith('_')]` (relevant subset)
```
['arecall', 'aretain', 'aretain_batch', 'aretain_files',
 'recall', 'retain', 'retain_batch', 'retain_files', ...]
```

### `inspect.signature(Hindsight.recall)`
```
(self, bank_id: str, query: str, types: list[str] | None = None, 
 max_tokens: int = 4096, budget: str = 'mid', trace: bool = False,
 query_timestamp: str | None = None, include_entities: bool = False,
 max_entity_tokens: int = 500, include_chunks: bool = False,
 max_chunk_tokens: int = 8192, include_source_facts: bool = False,
 max_source_facts_tokens: int = 4096, tags: list[str] | None = None,
 tags_match: Literal['any', 'all', 'any_strict', 'all_strict', 'exact'] = 'any',
 tag_groups: list[dict[str, Any]] | None = None,
 prefer_observations: bool = False,
 min_scores: dict[str, float] | None = None,
 temporal_window: dict[str, Any] | None = None) -> RecallResponse
```

### `inspect.signature(Hindsight.retain)`
```
(self, bank_id: str, content: str | list[dict[str, Any]],
 timestamp: datetime | None = None, context: str | None = None,
 document_id: str | None = None, metadata: dict[str, str] | None = None,
 entities: list[dict[str, str]] | None = None,
 resolve_entities: bool | None = None, tags: list[str] | None = None,
 update_mode: str | None = None, retain_async: bool = False,
 operation_id: str | None = None) -> RetainResponse
```

---

## 3. Constructor Analysis

### Full `__init__` source (via `inspect.getsource`)

```python
def __init__(
    self,
    base_url: str,              # REQUIRED — positional, no default
    api_key: str | None = None, # optional
    timeout: float = 300.0,
    user_agent: str | None = None,
    max_attempts: int = 3,
):
    config = hindsight_client_api.Configuration(host=base_url, access_token=api_key)
    ...
    if api_key:
        self._api_client.set_default_header("Authorization", f"Bearer {api_key}")
```

### Does `api_key` auto-read from env?
**NO.** There is no `os.environ.get("HINDSIGHT_API_KEY")` anywhere in `__init__`. 
The api_key must be passed explicitly as a parameter.

---

## 4. Summary of Confirmed API Surface

| Property | Value |
|---|---|
| PyPI package | `hindsight-client` |
| Installed version | `0.10.1` |
| Import | `from hindsight_client import Hindsight` |
| Constructor | `Hindsight(base_url, api_key=None, timeout=300.0, ...)` |
| `base_url` required? | **YES — positional, no default, will raise TypeError if omitted** |
| `api_key` auto-env? | **NO — must be passed explicitly** |
| `recall()` required params | `bank_id: str`, `query: str` |
| `retain()` required params | `bank_id: str`, `content: str \| list[dict]` |

---

## ⚠️ CRITICAL BUG IN CURRENT PROJECT CODE

**File:** `platform/knowledge-engine/main.py:20`
```python
# CURRENT (BROKEN):
hindsight = Hindsight(api_key=os.getenv("HINDSIGHT_API_KEY", "fallback-key"))
# This will raise:
# TypeError: Hindsight.__init__() missing 1 required positional argument: 'base_url'
```

`Hindsight.__init__` requires `base_url` as the **first positional argument** — it has no default value. The current code omits it entirely and will crash at import time.

---

## 5. Correct Usage

```python
import os
from hindsight_client import Hindsight

hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL", "https://memory.hindsight.vectorize.io"),
    api_key=os.getenv("HINDSIGHT_API_KEY"),
)

# recall — search historical incidents
results = hindsight.recall(
    bank_id="incident-memory-bank",
    query="OOMKilled container in namespace production"
)
# results is a RecallResponse object
# Access results as: results[0].content, iterate with for r in results

# retain — store resolved incident
hindsight.retain(
    bank_id="incident-memory-bank",
    content="Incident INC-044 resolved by restarting pod nginx-5d7f8. Root cause: OOMKilled."
)
```

---

## 6. Required Project Fixes (DO NOT APPLY IN THIS PHASE)

The following must be fixed before the memory integration works at runtime:

1. **`platform/knowledge-engine/main.py:20`** — Add `base_url` positional arg to `Hindsight(...)` constructor call.
2. **`infra/k8s/base/secrets.yaml`** and **`infra/helm/hindsight/templates/manifest_32.yaml`** — Add `HINDSIGHT_BASE_URL` secret alongside existing `HINDSIGHT_API_KEY`.
3. **`platform/knowledge-engine/requirements.txt`** — `hindsight-client` already listed ✅.
