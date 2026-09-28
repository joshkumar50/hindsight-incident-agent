from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.database import get_all_memories

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/memory/bank")
async def get_memory_bank():
    memories = get_all_memories()
    return {
        "bank_id": "hindsight-incident-agent",
        "total_memories": len(memories),
        "memories": memories
    }
