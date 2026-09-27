# ⚡ Hindsight Incident Agent — Autonomous Kubernetes SRE & Root Cause Intelligence Platform

> **HackwithHyderabad 3.0 Official Submission**
> **Track:** AI Agents That Learn Using Hindsight (Engineering & DevOps)
> **Team:** Team Durjay
> 
> **Team Members (6/6):**
> *   **Josh Kumar** (Team Leader) - `chittetijoshkumar@gmail.com`
> *   **Kondaveeti Sai Sri** - `saisrikondaveeti@gmail.com`
> *   **Hema Sankar Reddy Gade** - `hemashankareddy@gmail.com`
> *   **Tanu Sri** - `sritanu354@gmail.com`
> *   **Ramyasri Gade** - `ramyasrigade1432@gmail.com`
> *   **Jhansi Annapureddy** - `annapureddyjhansi2@gmail.com`

---

> AI-powered SRE Diagnostics Agent for EKS Kubernetes Clusters.  
> Automatically diagnoses incidents by querying Prometheus metrics, Elasticsearch logs, and Jaeger traces using a ReAct reasoning LLM agent.

---

## 🌍 Domain & Problem Statement

**Hackathon Challenge:** AI Agents That Learn Using Hindsight (Engineering & DevOps)
**Use Case:** Incident Response Agent

**The Real Business Problem:** 
When production is down, every minute of downtime costs enterprises thousands of dollars. Kubernetes clusters are highly complex, and SRE teams must scramble to manually correlate metrics, logs, and traces across disjointed dashboards to find the root cause. 
The biggest bottleneck? **Stateless troubleshooting.** Once an incident is resolved, the knowledge of *how* it was fixed is often lost in chat logs. When the same issue strikes a month later, engineers waste hours reinventing the wheel because traditional diagnostic tools have no memory of past outages.

**The Solution (Hindsight Incident Agent):** 
Hindsight Incident Agent is a Level-3 Autonomous AI Incident Response Agent that makes **persistent memory the star**. Using a complex ReAct (Reasoning & Acting) loop, it autonomously queries telemetry systems (Prometheus, Elasticsearch) to diagnose root causes. 
More importantly, Hindsight Incident Agent integrates **Vectorize Hindsight Persistent Memory** to learn from past incidents. When an outage is resolved, Hindsight Incident Agent saves the diagnostic fingerprint and playbook. If a semantically similar issue happens again, Hindsight Incident Agent recalls the exact resolution instantly—demonstrating a clear learning curve where the agent gets noticeably faster and smarter over time, dropping MTTR (Mean Time To Resolution) from hours to under 1 second.

---

## 📂 Project Structure

```
hindsight-incident-agent/
│
├── frontend/                     # ⚛️ React.js Frontend (Vite + Nginx)
│   ├── src/
│   │   ├── App.jsx               # Main dashboard component
│   │   ├── main.jsx              # React entry point
│   │   ├── index.css             # Global dark-mode design system
│   │   └── services/
│   │       └── api.js            # ← CONNECTS to backend /query endpoint
│   ├── nginx.conf                # Production reverse proxy config
│   ├── Dockerfile                # Multi-stage build (Node → Nginx)
│   ├── package.json              # React/Vite dependencies
│   ├── vite.config.js            # Dev proxy: /api → localhost:8000
│   └── index.html                # HTML entry point
│
├── agent/                        # 🤖 Custom SRE Agent (ReAct Loop)
│   ├── agent_workflow.py         # ReAct reasoning loop with tool calling
│   ├── llm_client.py             # Unified LLM client (Bedrock/OpenAI/Anthropic)
│   └── __init__.py
│
├── config/
│   └── config.yaml               # ← Central API keys & Hindsight credentials
│
├── lambda_/                      # ☁️ AWS Lambda Package
│   ├── lambda_handler.py         # Serverless entry point
│   ├── ai/
│   │   ├── bedrock_client.py     # Direct AWS Bedrock model invocation
│   │   └── rca_analyzer.py       # Fail-safe single-turn analyzer
│   ├── collectors/
│   │   ├── prometheus_collector.py   # Metrics scraper
│   │   ├── elasticsearch_collector.py # Log scraper
│   │   └── jaeger_collector.py       # Trace scraper
│   └── integrations/
│       └── remediation.py        # Auto-healing actions (Slack, Jira, K8s)
│
├── shared/                       # 📦 Shared Python Modules
│   ├── config.py                 # Reads config.yaml → exposes `config` object
│   ├── models.py                 # Pydantic data models (request/response schemas)
│   └── database.py               # ← Hindsight memory client (retain/recall)
│
├── infrastructure/
│   ├── terraform/                # Terraform IaC for Lambda + IAM
│   │   ├── main.tf
│   │   └── iam.tf
│   └── k8s/                      # Kubernetes manifests for EKS deployment
│       ├── backend-deployment.yaml
│       ├── frontend-deployment.yaml
│       └── db-secret.yaml
│
├── main.py                       # 🐍 FastAPI backend server (port 8000)
├── Dockerfile.backend            # Backend container image
├── docker-compose.yml            # Local orchestration (Hindsight + Backend + Frontend)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 🔗 How the Microservices Connect

```
┌──────────────────┐       POST /api/query       ┌───────────────────┐
│                  │ ──────────────────────────▶  │                   │
│  React Frontend  │                              │  FastAPI Backend  │
│  (Port 3000)     │ ◀──────────────────────────  │  (Port 8000)      │
│                  │       JSON RCA Response       │                   │
└──────────────────┘                              └────────┬──────────┘
                                                           │
                                                           │ Hindsight SDK
                                                           ▼
                                                  ┌───────────────────┐
                                                  │  Hindsight Cloud  │
                                                  │ (Vectorize.io API)│
                                                  └───────────────────┘
```

### Connection Points in Code:

| From | To | File | Code |
|---|---|---|---|
| **App.jsx** → Backend | POST /query | `frontend/src/services/api.js` | `client.post('/query', payload)` |
| **Vite Dev Proxy** | localhost:8000 | `frontend/vite.config.js` | `proxy: { '/api': { target: 'http://localhost:8000' } }` |
| **Nginx Prod Proxy** | backend:8000 | `frontend/nginx.conf` | `proxy_pass http://backend:8000/;` |
| **Backend** → Hindsight | Memory API | `shared/database.py` | `hindsight.retain()`, `hindsight.recall()` |
| **Backend** → Config | Reads credentials | `shared/config.py` → `config/config.yaml` | `config.hindsight.api_key` |

---

## 🚀 Quick Start (Local & Docker)

### Option 1: Docker Compose (Recommended)

This runs the Frontend and Backend microservices with a single command:

```bash
# 1. Clone and navigate
cd hindsight-incident-agent

# 2. Add your Hindsight Promo Code Credit Key to config/config.yaml
#    hindsight:
#      api_key: "hsk_..."

# 3. Start all services
docker-compose up --build

# 4. Access the dashboard
#    Frontend: http://localhost:3000
#    Backend API: http://localhost:8000/docs
```

### Option 2: Run Locally (Without Docker)

#### Backend
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Configure your Vectorize Hindsight key in config/config.yaml:
#    hindsight:
#      api_key: "hsk_..."

# 3. Configure your LLM API key in config/config.yaml:
#    bedrock:
#      aws_access_key_id: "AKIA..."
#      aws_secret_access_key: "..."

# 4. Start the backend
python main.py
# Backend runs at http://localhost:8000
```

#### Frontend
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install Node dependencies
npm install

# 3. Start Vite dev server (auto-proxies /api to backend)
npm run dev
# Frontend runs at http://localhost:3000
```

---

## 🧠 Hindsight Persistent Memory Integration

This project relies entirely on **Vectorize Hindsight** for persistent memory, eliminating the need for legacy relational databases like MySQL. 

### How the Backend Connects to Hindsight
The agent uses the official `hindsight-client` SDK (`shared/database.py`) to connect to Hindsight Cloud. 
*   **Recall Phase**: Before analyzing logs, Hindsight Incident Agent queries Hindsight for past similar outages to instantly suggest proven runbooks without burning LLM tokens.
*   **Retain Phase**: When an incident is solved, Hindsight Incident Agent commits the learning to the Hindsight bank.

To get your API key, sign up at [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io) and apply the hackathon promo code (`MEMHACK99`).

---

## 🔧 Configuration Reference

### config/config.yaml

| Section | Key | Purpose |
|---|---|---|
| `hindsight.api_key` | `hsk_...` | **Required.** Authentication for persistent memory |
| `default_llm_provider` | `bedrock` / `openai` / `anthropic` | Which LLM to use |
| `bedrock.aws_access_key_id` | AWS key | Bedrock authentication |
| `bedrock.model_id` | Model name | e.g. `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `openai.api_key` | OpenAI key | Alternative LLM provider |
| `anthropic.api_key` | Anthropic key | Alternative LLM provider |
| `agent.max_iterations` | `8` | Max ReAct reasoning loops (cost safety) |
| `agent.temperature` | `0.1` | LLM creativity (low = factual) |
---

## 📡 API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | System info (active LLM, tools) |
| `GET` | `/health` | Health check for K8s probes |
| `POST` | `/query` | Run SRE diagnostic analysis |
| `GET` | `/query?q=...` | Quick browser test endpoint |
| `GET` | `/docs` | Interactive Swagger API docs |

### Example POST /query Request
```json
{
  "query": "Why is the checkout service returning 500 errors?",
  "target_service": "checkout-svc",
  "target_namespace": "production",
  "lookback_minutes": 60
}
```

### Example Response
```json
{
  "request_id": "abc-123",
  "rca": {
    "severity": "high",
    "root_cause_summary": "Database connection pool exhaustion causing 500 errors",
    "detailed_analysis": "The checkout service is experiencing...",
    "recommended_actions": [
      "Increase database connection pool size to 50",
      "Add connection timeout of 5 seconds",
      "Restart checkout-svc pods"
    ],
    "affected_components": ["checkout-svc", "postgres-primary"],
    "confidence_score": 0.87,
    "llm_model_used": "anthropic.claude-3-5-sonnet-20241022-v2:0"
  }
}
```

---

## 🧠 Hindsight Persistent Memory

The platform uses **Hindsight by Vectorize** for intelligent semantic memory. Instead of a dumb cache, Hindsight Incident Agent learns from every incident:
- **Recall Phase**: Before analyzing logs, Hindsight Incident Agent queries Hindsight for past similar outages to instantly suggest proven runbooks.
- **Retain Phase**: When an incident is solved or human feedback is given, Hindsight Incident Agent commits the learning to Hindsight.

This gives Hindsight Incident Agent the experience of a senior SRE, drastically reducing MTTR for recurring infrastructure patterns.

---

## 🔑 Environment Variables (Phase 0–4 Additions)

| Variable | Service | Default | Purpose |
|---|---|---|---|
| `HINDSIGHT_API_KEY` | backend | — | **Required.** Vectorize Hindsight SDK authentication |
| `AUTONOMOUS_MODE` | execution-engine | `assist` | `assist` / `full` / `off` — controls autonomous execution gate |
| `SLACK_WEBHOOK_URL` | notification-service | — | Incoming Slack webhook for incident alerts |
| `SLACK_INTERACTIVE_URL` | notification-service | — | Public URL for Slack button callbacks (`POST /slack/interactive`) |
| `REACT_MAX_SECONDS` | backend | `120` | Wall-clock budget (seconds) for the ReAct reasoning loop |
| `DEMO_DELAY_SECONDS` | execution-engine | `3` | Delay before applying fix (for live demo pacing) |
| `GEMINI_API_KEY` | ai-copilot | — | Google Gemini API key for AI explanations and postmortems |

---

## 📡 New API Endpoints (Phase 0–4)

### Backend (ReAct Agent — port 8000)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/query` | Run SRE diagnostic analysis |
| `POST` | `/feedback` | Submit operator verdict (accept/reject/modify) on AI runbook |
| `GET`  | `/health` | K8s health probe |

### Dashboard BFF (port varies)
| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/stream/pilot` | **SSE** — live pilot lifecycle events (DIAGNOSING→STABILIZED) |
| `GET`  | `/api/stream/metrics` | **SSE** — live monitoring-engine metrics pushed every 1s |
| `GET`  | `/api/metrics/history?service=<name>` | Last 60 sparkline data points per service |
| `POST` | `/api/feedback` | Proxy to backend `/feedback` |
| `POST` | `/api/ai/postmortem` | Proxy to ai-copilot `/postmortem` |
| `GET`  | `/api/export/csv` | Download audit trail as CSV |
| `GET`  | `/api/export/json` | Download audit trail as JSON |

### Notification Service (port 8000)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/slack/interactive` | Slack button webhook — approve_fix / enable_auto |
| `GET`  | `/slack/status` | Slack integration status |

### AI Copilot (port 8000)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/explain` | AI incident explanation |
| `POST` | `/postmortem` | Gemini-powered markdown postmortem |

### Audit Engine (port 8000)
| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/internal/logs` | Internal audit log reader |
| `GET`  | `/api/export?format=csv|json` | Export audit logs (up to 5000 rows) |

---

## 🔧 Install Commands (Human Must Run)

```bash
# Phase 0: Hindsight memory SDK
pip install hindsight-client

# Phase 2: BFF SSE dependencies (already in dashboard-bff/requirements.txt)
pip install "sse-starlette>=2.0.0" "redis>=5.0.0"

# Phase 3: Slack ChatOps (httpx already in requirements)
# No additional installs needed

# UI: lucide-react icons (if not already installed)
cd ui && npm install lucide-react
```

---

## 🚀 Verification Curls (port-forwarded API Gateway on :58663)

```bash
# Phase 0: Hindsight recall hit test
curl -X POST http://localhost:58663/query \
  -H "Content-Type: application/json" \
  -d '{"query":"checkout service returning 500 errors","target_service":"order-service"}'

# Phase 0: Human feedback
curl -X POST http://localhost:58663/feedback \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"test-001","verdict":"accept","user":"sre-operator"}'

# Phase 1: Check SSE pilot stream
curl -N http://localhost:58663/api/stream/pilot

# Phase 2: Check SSE metrics stream  
curl -N http://localhost:58663/api/stream/metrics

# Phase 3: Slack status
curl http://localhost:58663/slack/status

# Phase 4: Generate postmortem
curl -X POST http://localhost:58663/api/ai/postmortem \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"test-001"}'

# Phase 4: Export audit logs
curl http://localhost:58663/api/export/csv -o audit_logs.csv
```
