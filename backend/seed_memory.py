import asyncio
import uuid
import sys
import os

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from shared.database import hindsight_memory, init_db

async def seed_memory():
    # Initialize the hindsight bank if not exists
    await hindsight_memory.init_bank()
    
    incidents = [
        {
            "id": str(uuid.uuid4()),
            "symptoms": "Why is the checkout service returning 500 errors?",
            "root_cause": "Database connection pool exhaustion.",
            "playbook": ["Increase max_connections", "Restart pod"],
            "human_approved": True,
            "outcome": "success"
        },
        {
            "id": str(uuid.uuid4()),
            "symptoms": "Payment gateway timeouts and P99 latency spikes.",
            "root_cause": "Third-party payment provider rate limiting.",
            "playbook": ["Enable circuit breaker fallback", "Contact vendor"],
            "human_approved": True,
            "outcome": "success"
        },
        {
            "id": str(uuid.uuid4()),
            "symptoms": "Redis OOMKilled in auth namespace.",
            "root_cause": "Stale session tokens accumulating without TTL.",
            "playbook": ["Flush stale keys", "Set correct TTL policy in config map"],
            "human_approved": True,
            "outcome": "success"
        },
        {
            "id": str(uuid.uuid4()),
            "symptoms": "Frontend pods stuck in CrashLoopBackOff.",
            "root_cause": "Missing env config for API_GATEWAY_URL.",
            "playbook": ["Rollback deployment to previous revision", "Add missing env var"],
            "human_approved": True,
            "outcome": "success"
        },
        {
            "id": str(uuid.uuid4()),
            "symptoms": "High CPU usage on search microservice.",
            "root_cause": "Unindexed query causing full table scan.",
            "playbook": ["Scale up replicas temporarily", "Deploy hotfix adding DB index"],
            "human_approved": True,
            "outcome": "success"
        }
    ]

    print(f"Seeding {len(incidents)} incidents into Hindsight Memory (Bank: {hindsight_memory.bank_id})...")
    
    for inc in incidents:
        print(f"Retaining: {inc['symptoms']}")
        await hindsight_memory.retain(
            incident_id=inc["id"],
            symptoms=inc["symptoms"],
            root_cause=inc["root_cause"],
            playbook=inc["playbook"],
            human_approved=inc["human_approved"],
            outcome=inc["outcome"]
        )
    
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_memory())
