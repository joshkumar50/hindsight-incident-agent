# Hindsight Incident Agent — Pre-Submission Audit

## Executive Summary
This project is an ambitious, visually impressive demonstration of a Kubernetes SRE platform. However, it is currently **un-submittable for a judging criteria heavily focused on Hindsight Memory**. The platform's core value proposition—autonomous learning via memory—is completely mocked. There are also critical infrastructure naming mismatches that will cause deployment failures if rebuilt from scratch. The biggest risk is scoring a 0/25 on the "Use of Hindsight Memory" category because the integration is entirely fake.

## 1. Blocking Issues

| Issue | File | Line | Severity | Fix |
|-------|------|------|----------|-----|
| **Naming Mismatch: ConfigMaps** | `apps/traffic-generator/k8s/deployment.yaml` | 33 | BLOCKER | Deployment expects `hindsight-agent-global-config`, Helm hardcodes `hindsight-agent-global-config`. Unify naming conventions (prefer `hindsight-agent-*`). |
| **Naming Mismatch: Secrets** | `infra/k8s/base/secrets.yaml` | 4 | BLOCKER | Defines `hindsight-agent-secrets` but Helm manifests look for `hindsight-agent-secrets`. Pods will stay in `ContainerCreating`. |
| **Naming Mismatch: Docker Images** | `start.ps1` | 46-63 | BLOCKER | Script builds `hindsight-agent/<service>:latest`, but K8s deployments pull `hindsight-agent-<service>:latest`. Images will pull ErrImagePull. |
| **Stubbed Database Logic** | `shared/database.py` | 1-51 | HIGH | `get_all_memories()` returns a hardcoded python dictionary (`_fallback_memory`). |

## 2. Hindsight Memory Integration Verdict
**Verdict: NO (Completely Fake)**

- **Evidence:** The strings `recall(` and `retain(` appear **only** in `submission_manifest.json`. They are not implemented in any Python code.
- **Evidence:** The string `vectorize` only appears in markdown docs (`PROJECT_PITCH.md`, `README.md`).
- **Evidence:** `requirements.txt` does not contain the `vectorize-python` SDK.
- **Evidence:** `platform/knowledge-engine/main.py` (Line 30) returns hardcoded JSON: `{"historical_matches": [{"past_incident_id": "INC-044", "resolution": "Restart Auth Service Pods", "success_rate": 0.95}]}`.
- **Evidence:** `ai-orchestrator` never initiates a memory check before RCA, nor does it retain knowledge after recovery. 
- **Summary:** The 25% hackathon criteria is not met. The platform does not use Hindsight for memory; it uses static mock responses.

## 3. Event Flow Map

| Publisher | Event Type | Consumer | Status |
|-----------|------------|----------|--------|
| Unknown (Anomalies) | `BLAST_RADIUS_MAPPED` | `incident-engine` | Active |
| `incident-engine` | `INCIDENT_DECLARED` | `ai-orchestrator` | Active |
| `ai-orchestrator` | `RECOVERY_PLAN_READY` | `execution-engine` | Active |
| `ai-orchestrator` | `AUTONOMOUS_DECISION` | `audit-engine` | Active |
| `execution-engine` | `RECOVERY_COMPLETED` | `incident-engine` | **FAKE** (Catches K8s failure and simulates success: `execution-engine/main.py:62-95`) |

## 4. Test Coverage Reality
**Count:** 14 test directories found.
**Real Tests:** 0
**Fake Tests:** 14 
**Evidence:** Every `test_*.py` file contains the exact same fake test:
```python
import pytest
@pytest.mark.asyncio
async def test_metrics_endpoint():
    assert True
```
There are **zero** integration tests for the Hindsight memory workflow or the Redis event flow.

## 5. Infrastructure Consistency
- **Source of Truth Conflict:** The repo contains both `infra/k8s/` and `infra/helm/hindsight/`.
- **Decorative Helm:** The Helm chart (`infra/helm/hindsight/templates/manifest_*.yaml`) is completely hardcoded. It does not use Go templating (`{{ .Values.* }}`) for variables.
- **Decorative Values:** `infra/helm/hindsight/values.yaml` defines `replicaCount: 1` and `image.repository`, but these values are never referenced in the templates.

## 6. Docs vs Reality

| Claim | Status | Evidence |
|-------|--------|----------|
| "17 microservices on Kubernetes" | PARTIALLY TRUE | 13 backend services + 1 UI + Postgres + Redis. |
| "Immutable audit trail" | PARTIALLY TRUE | `audit-engine/main.py` writes to PostgreSQL, but relies on a hardcoded password in plaintext (`postgresql://hindsight_user:incident_agent_secret@postgres-db...`). |
| "Calls recall() ... returns cached playbook" | **FALSE** | No `recall()` or `retain()` function exists in the codebase. Mocked in `knowledge-engine/main.py:30`. |
| "Zero LLM tokens used on hit" | **FALSE** | The system does not actually query a vector database for semantic similarity. |

## 7. Judging Criteria Scores

1. **Innovation (30%) — Score: 7/10** 
   *Good architectural pattern (EventBus + Orchestrator), but lacks depth in execution.*
2. **Use of Hindsight Memory (25%) — Score: 0/10**
   *Total failure. No SDK installed, no API keys used, entirely mocked.*
3. **Technical Implementation (20%) — Score: 4/10**
   *Helm is hardcoded, tests are fake, Docker tags don't match K8s manifests, execution engine fakes success.*
4. **User Experience (15%) — Score: 8/10**
   *UI is responsive and visually sells the concept well.*
5. **Real-world Impact (10%) — Score: 2/10**
   *Cannot be deployed to a real cluster due to hardcoded mocks and fake Kubernetes mutations.*

**Weighted Total:** 4.3 / 10

## 8. Top 5 Fixes

1. **Implement Actual Hindsight API (Blocker for 25% Criteria)**
   - *Change:* Update `knowledge-engine/main.py` and `ai-orchestrator/main.py` to install the Vectorize SDK, initialize `HINDSIGHT_API_KEY`, and perform a real `recall()` / `retain()`. 
   - *Effort:* 2-3 hours.
2. **Fix Image Tagging & Naming (Blocker)**
   - *Change:* Update `start.ps1` to build images using `hindsight-agent-<name>:latest` instead of `hindsight-agent/`. Ensure all ConfigMaps and Secrets use `hindsight-agent-*`.
   - *Effort:* 0.5 hours.
3. **Remove `try/except` Demo Faking in Execution Engine**
   - *Change:* `platform/execution-engine/main.py:62`. Actually fail the pipeline if Kubernetes refuses the mutation, instead of printing "simulating success for demo".
   - *Effort:* 0.5 hours.
4. **Parameterize Helm Charts (Improvement)**
   - *Change:* Convert hardcoded manifests in `infra/helm/hindsight/templates/` to use `{{ .Values.image.repository }}` so the Helm chart is actually valid.
   - *Effort:* 1 hour.
5. **Write 1 Real End-to-End Test (Improvement)**
   - *Change:* Add a test that injects an incident into the Redis stream and verifies the `RECOVERY_COMPLETED` event is emitted.
   - *Effort:* 1 hour.

## 9. Raw Evidence Appendix

**Missing SDK:**
```bash
> grep -i 'hindsight' requirements.txt
[No matches found]
```

**Fake Tests:**
```bash
> cat platform/incident-engine/tests/test_main.py
import pytest
@pytest.mark.asyncio
async def test_metrics_endpoint():
    assert True
```

**Execution Engine Faking Success:**
```python
# platform/execution-engine/main.py:61
except Exception as e:
    logger.warning("K8s API patch failed locally, simulating success for demo", incident_id=incident_id, error=str(e))
    # ... publishes RECOVERY_COMPLETED anyway
```

**Hardcoded Knowledge Engine:**
```python
# platform/knowledge-engine/main.py:30
return {
    "historical_matches": [
        {
            "past_incident_id": "INC-044",
            "resolution": "Restart Auth Service Pods",
            "success_rate": 0.95,
        }
    ]
}
```
