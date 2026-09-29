import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_KNOWLEDGE_ENGINE_URL = (
    "http://knowledge-engine.incident-agent-system.svc.cluster.local"
)


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/memory/bank")
async def get_memory_bank():
    """
    Proxy to knowledge-engine /memory/stats.
    Falls back to a safe static response if the upstream is unreachable
    (e.g., local dev / unit-test environment).
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{_KNOWLEDGE_ENGINE_URL}/memory/stats")
            res.raise_for_status()
            data = res.json()
            return {
                "bank_id": data.get("bank_id", "incident-memory-bank"),
                "total_memories": data.get("total_memories", -1),
                "memories": [],
            }
    except Exception:
        # Upstream unavailable — return safe fallback, never fake memories
        return {
            "bank_id": "incident-memory-bank",
            "total_memories": -1,
            "memories": [],
        }
