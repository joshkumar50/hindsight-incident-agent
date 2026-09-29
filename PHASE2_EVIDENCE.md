# PHASE2_EVIDENCE.md

## Mandatory Check 1: grep -n "recall\|retain\|HINDSIGHT\|hindsight"

```
LineNumber Line
---------- ----
        25 # Hindsight SDK initialisation
        26 # Signatures verified in PHASE1_SDK.md from hindsight-client==0.10.1:
        27 #   Hindsight(base_url: str, api_key: str | None = None, ...)
        28 #   recall(bank_id: str, query: str, ...) -> RecallResponse
        29 #   retain(bank_id: str, content: str | list[dict], ...) -> RetainResponse
        31 _HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
        32 _HINDSIGHT_BASE_URL = os.getenv(
        33     "HINDSIGHT_BASE_URL", "https://memory.hindsight.vectorize.io"
        36 HINDSIGHT_ENABLED: bool = False
        37 hindsight = None
        39 if not _HINDSIGHT_API_KEY:
        41         "hindsight_disabled",
        42         reason="HINDSIGHT_API_KEY env var not set - memory recall/retain will be skipped",
        46         from hindsight_client import Hindsight  # noqa: E402 - conditional import
        48         hindsight = Hindsight(
        49             _HINDSIGHT_BASE_URL,          # base_url: str  (required positional)
        50             api_key=_HINDSIGHT_API_KEY,   # api_key: str | None
        52         HINDSIGHT_ENABLED = True
        53         logger.info("hindsight_enabled", base_url=_HINDSIGHT_BASE_URL)
        55         logger.warning("hindsight_init_failed", error=str(_e))
        57 _HINDSIGHT_BANK_ID = "incident-memory-bank"
        69         # If Hindsight returns a high-confidence hit (>= 0.8), skip the full
        72         if HINDSIGHT_ENABLED:
        74                 memory_results = hindsight.recall(
        75                     bank_id=_HINDSIGHT_BANK_ID,
       109                                 "model_name": "hindsight",
       121                     "hindsight_recall_failed",
       191                 if HINDSIGHT_ENABLED:
       193                         hindsight.retain(
       194                             bank_id=_HINDSIGHT_BANK_ID,
       201                         logger.info("hindsight_retained", incident_id=incident_id)
       204                             "hindsight_retain_failed",
```

## Mandatory Check 2: memory_hit presence

```
LineNumber Line
---------- ----
        58 _MEMORY_HIT_THRESHOLD = 0.8
        81                     if top_score >= _MEMORY_HIT_THRESHOLD:
        84                             "memory_hit_short_circuit",
        95                                 "memory_hit": True,
       159                 # 5. Output Final Package (memory miss path - memory_hit=False)
       165                         "memory_hit": False,
```

## Mandatory Check 3: Syntax

```
syntax ok
```

---

## Compliance Checklist

| Requirement | Met? | Evidence |
|---|---|---|
| ≥1 line with HINDSIGHT_API_KEY | ✅ | Line 31 |
| ≥1 line calling recall( | ✅ | Line 74: `memory_results = hindsight.recall(` |
| ≥1 line calling retain( | ✅ | Line 193: `hindsight.retain(` |
| ≥1 line with memory_hit | ✅ | Lines 95, 165 |
| Syntax valid (ast.parse) | ✅ | `syntax ok` |
| Only platform/ai-orchestrator/main.py modified | ✅ | No other files touched |
| Signatures match PHASE1_SDK.md exactly | ✅ | `Hindsight(base_url, api_key=...)`, `recall(bank_id, query)`, `retain(bank_id, content)` |

---

## What Was Implemented

### Module-level initialisation (Lines 25–57)
- Reads `HINDSIGHT_API_KEY` from env
- If missing: logs warning once, sets `HINDSIGHT_ENABLED = False`
- If present: instantiates `Hindsight(base_url, api_key=...)` using **exact** PHASE1_SDK.md signatures (`base_url` is required positional — not an env-auto-read field)
- Any init exception sets `HINDSIGHT_ENABLED = False` — does not crash startup

### Memory recall short-circuit (Lines 72–122)
- Executed BEFORE the RCA call
- Calls `hindsight.recall(bank_id=..., query=incident_description)`
- If `top.score >= 0.8`: publishes `RECOVERY_PLAN_READY` with `memory_hit=True` + `AUTONOMOUS_DECISION` with `model_name="hindsight"`, then **returns immediately** (no LLM pipeline)
- Recall failure caught and logged — does NOT block the full pipeline

### Memory miss path (Lines 159–168)
- `RECOVERY_PLAN_READY` payload now includes `"memory_hit": False`

### Memory retain (Lines 191–207)
- Called AFTER `RECOVERY_PLAN_READY` is published on the miss path
- Calls `hindsight.retain(bank_id=..., content=...)` using exact signature
- Wrapped in `try/except` — retain failure does NOT crash the pipeline
