# PHASE9_EVIDENCE.md

## Mandatory Check 1: grep -c "recall\|retain" README.md

```
7
```

✅ At least 1 match. recall/retain appear 7 times in README.md.

---

## Mandatory Check 2: ls submission_manifest.json

```
Name   : submission_manifest.json
Length : 2664
```

✅ File exists, 2664 bytes. NOT deleted.

---

## Compliance Checklist

| Requirement | Met? | Evidence |
|---|---|---|
| `recall\|retain` count >= 1 | ✅ | 7 matches |
| `submission_manifest.json` exists | ✅ | 2664 bytes |
| Video/article/social URLs unchanged | ✅ | Only structural content modified |
| Nothing deleted | ✅ | README lines only added/fixed |
| Only README.md modified | ✅ | No other files touched |

---

## What Changed

### 1. Fixed broken file reference — line 127
```diff
- kubectl apply -k infra/manifests
+ kubectl apply -k infra/k8s
```
`infra/manifests` does not exist. Verified: `Test-Path infra\manifests => False`.
Actual path `infra/k8s` verified: `Test-Path infra\k8s => True`.

### 2. Added "Hindsight Memory Integration" section (before the existing Vectorize Hindsight section)

New section covers:

| Item | Detail |
|---|---|
| `recall()` | Called before RCA in `platform/ai-orchestrator/main.py → coordinate_ai_workflow()`. Score >= 0.8 short-circuits the full LLM pipeline. |
| `retain()` | Called after fresh `RECOVERY_PLAN_READY` publish (miss path). Commits new playbook to bank. |
| `memory_hit` flag | Present in all `RECOVERY_PLAN_READY` payloads — `True` on cache hit, `False` on miss. |
| Env vars | `HINDSIGHT_API_KEY` (required), `HINDSIGHT_BASE_URL` (optional) |
| Knowledge Engine endpoints | `/search` (recall proxy), `/retain` (retain proxy), `/memory/stats` |

### All verified file references
| Path | Status |
|---|---|
| `docs/assets/architecture.png` | ✅ EXISTS |
| `ui/src/api/client.ts` | ✅ EXISTS |
| `ui/vite.config.ts` | ✅ EXISTS |
| `platform/dashboard-bff/main.py` | ✅ EXISTS |
| `pkg/eventbus/client.py` | ✅ EXISTS |
| `platform/dashboard-bff/Dockerfile` | ✅ EXISTS |
| `infra/k8s` (fixed from `infra/manifests`) | ✅ EXISTS |
| `scripts/` | ✅ EXISTS |
| `apps/` | ✅ EXISTS |
