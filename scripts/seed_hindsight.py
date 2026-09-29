"""
Seed the Hindsight memory bank with realistic past incidents.
Run this ONCE before the demo so the first recall returns a real hit.

Usage:
    $env:HINDSIGHT_API_KEY = "hsk_..."
    python scripts/seed_hindsight.py
"""
import os
from hindsight_client import Hindsight

API_KEY = os.environ.get("HINDSIGHT_API_KEY")
if not API_KEY:
    raise SystemExit("ERROR: set HINDSIGHT_API_KEY env var first")

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_BASE_URL", "https://memory.hindsight.vectorize.io"),
    api_key=API_KEY,
)

BANK_ID = "incident-memory-bank"

SEEDS = [
    {
        "document_id": "INC-044",
        "content": (
            "Incident INC-044: auth-service pod OOMKilled in hindsight-agent-apps "
            "namespace. Symptoms: pod restart loop, 502 errors on /auth/validate, "
            "latency spike to 5000ms. Root cause: memory limit 128Mi too low for "
            "peak login traffic. Resolution: restart deployment and raise memory "
            "limit to 512Mi. Success rate: 0.95"
        ),
    },
    {
        "document_id": "INC-045",
        "content": (
            "Incident INC-045: payment-service timeout calling auth-service. "
            "Symptoms: 504 UPSTREAM_TIMEOUT on /payment/process, cascading to "
            "order-service. Root cause: auth-service latency exceeded payment "
            "service 3s timeout. Resolution: scale auth-service replicas from 1 to 3. "
            "Success rate: 0.92"
        ),
    },
    {
        "document_id": "INC-046",
        "content": (
            "Incident INC-046: order-service returning 500 errors after a "
            "deployment. Symptoms: 100% error rate on /order/place, "
            "inventory-service calls failing. Root cause: bad release v1.2.4 "
            "with broken DB migration. Resolution: rollback deployment to v1.2.3. "
            "Success rate: 0.88"
        ),
    },
    {
        "document_id": "INC-047",
        "content": (
            "Incident INC-047: inventory-service memory pressure and GC pauses. "
            "Symptoms: response latency 800ms+, intermittent 503s. Root cause: "
            "memory limit 256Mi insufficient after data growth. Resolution: raise "
            "memory limit to 512Mi and restart. Success rate: 0.90"
        ),
    },
    {
        "document_id": "INC-048",
        "content": (
            "Incident INC-048: notification-service queue backlog. Symptoms: "
            "order_events stream consumer lag growing, emails delayed. Root cause: "
            "consumer crashed mid-batch leaving unacknowledged messages. Resolution: "
            "restart notification-service consumer group. Success rate: 0.85"
        ),
    },
]

print(f"Seeding {len(SEEDS)} incidents into bank '{BANK_ID}'...")
for seed in SEEDS:
    try:
        client.retain(
            bank_id=BANK_ID,
            content=seed["content"],
            document_id=seed["document_id"],
        )
        print(f"  [OK] {seed['document_id']} retained")
    except Exception as e:
        print(f"  [FAIL] {seed['document_id']}: {e}")

print("\nDone. Verify in the Hindsight UI or via recall().")
