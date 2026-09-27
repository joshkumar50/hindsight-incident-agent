# -*- coding: utf-8 -*-
"""
backend/seed_memory.py
======================
Seed the Hindsight memory bank with realistic past incidents so demo
queries hit recall on the first try.

Usage:
    python -m backend.seed_memory          (from repo root)
    python backend/seed_memory.py          (from repo root directly)

Requires:
    - HINDSIGHT_API_KEY env var set to a valid Hindsight Cloud key
    - hindsight-client package installed (pip install hindsight-client)
"""

import asyncio
import os
import sys

# Force UTF-8 stdout so unicode chars render on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# -- Path injection so this runs from repo root ----------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND   = os.path.join(_REPO_ROOT, "backend")
for _p in [_REPO_ROOT, _BACKEND]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# -- Guard: check for API key before importing anything else ---------------
if not os.getenv("HINDSIGHT_API_KEY", "").strip():
    print("WARNING: HINDSIGHT_API_KEY is not set or empty.")
    print("   Set it in your environment and re-run:")
    print("       $env:HINDSIGHT_API_KEY='hsk_...'   (PowerShell)")
    print("       export HINDSIGHT_API_KEY='hsk_...' (Bash)")
    # removed sys.exit(0) so we can import it in the API

try:
    from shared.database import hindsight_memory
except ImportError as exc:
    print(f"[FAIL] ImportError: {exc}")
    print("   Ensure hindsight-client is installed:  pip install hindsight-client")


# -- Incident catalogue ----------------------------------------------------

INCIDENTS = [
    dict(
        incident_id="INC-1001",
        symptoms="order-service returning 500 errors latency spike above 2000ms",
        root_cause="Database connection pool exhaustion under burst traffic",
        playbook=[
            "Increase connection pool size to 50",
            "Add 5s connection timeout to Postgres client",
            "kubectl rollout restart deployment/order-service -n hindsight-agent-apps",
        ],
        human_approved=True,
        outcome="success",
    ),
    dict(
        incident_id="INC-1002",
        symptoms="auth-service pods crashing with OOMKilled status",
        root_cause="Memory limit of 256Mi too low for new token cache",
        playbook=[
            "Raise memory limit to 512Mi in deployment spec",
            "Add HPA targeting 70% memory utilization",
            "kubectl rollout restart deployment/auth-service",
        ],
        human_approved=True,
        outcome="success",
    ),
    dict(
        incident_id="INC-1003",
        symptoms="payment-service timeout calling upstream auth after 3s",
        root_cause="Upstream auth-service latency breach of 3s SLO",
        playbook=[
            "Add circuit breaker on auth-service client call",
            "Increase client timeout to 5s temporarily",
            "Page SRE if auth P99 > 2s for 5 minutes",
        ],
        human_approved=True,
        outcome="success",
    ),
    dict(
        incident_id="INC-1004",
        symptoms="checkout service returning 500 errors",
        root_cause="DB connection saturation on checkout path",
        playbook=[
            "Scale pgBouncer pool to 100 connections",
            "Rollout restart checkout deployment",
            "Add connection pool metrics alert at 80% utilization",
        ],
        human_approved=True,
        outcome="success",
    ),
    dict(
        incident_id="INC-1005",
        symptoms="inventory-service pod failing readiness probe",
        root_cause="Readiness probe initialDelaySeconds too aggressive during warmup",
        playbook=[
            "Bump initialDelaySeconds to 30 on readiness probe",
            "Add startupProbe with failureThreshold 15",
            "Rollout restart inventory-service",
        ],
        human_approved=True,
        outcome="success",
    ),
]

# -- Verification queries --------------------------------------------------

VERIFY_QUERIES = [
    "Why is order-service returning 500 errors?",
    "checkout 500 errors after deploy",
    "auth pods OOMKilled after traffic spike",
]


# -- seed() ----------------------------------------------------------------

async def seed():
    print()
    print("=" * 51)
    print("  PHASE 1 -- Seeding Hindsight memory bank")
    print("=" * 51)

    # Ensure the bank exists before writing to it
    await hindsight_memory.init_bank()

    for inc in INCIDENTS:
        try:
            await hindsight_memory.retain(
                incident_id=inc["incident_id"],
                symptoms=inc["symptoms"],
                root_cause=inc["root_cause"],
                playbook=inc["playbook"],
                human_approved=inc["human_approved"],
                outcome=inc["outcome"],
            )
            print(f"  [OK]  Retained  {inc['incident_id']}  -- {inc['symptoms'][:60]}")
        except Exception as exc:
            print(f"  [FAIL] Failed   {inc['incident_id']}  -- {exc}")


# -- verify() --------------------------------------------------------------

async def verify():
    print()
    print("=" * 51)
    print("  PHASE 2 -- Recall verification")
    print("=" * 51)

    for query in VERIFY_QUERIES:
        print(f"\n  Query : \"{query}\"")
        try:
            results = await hindsight_memory.recall(query, k=3)
            if results:
                top = results[0]
                print(f"  [HIT]  incident_id  : {top.get('incident_id')}")
                print(f"         resolution   : {top.get('resolution', '')[:100]}")
                print(f"         success_rate : {top.get('success_rate')}")
                playbook = top.get("playbook", [])
                if isinstance(playbook, list):
                    print(f"         playbook[0]  : {playbook[0] if playbook else '--'}")
                else:
                    print(f"         playbook     : {str(playbook)[:100]}")
            else:
                print("  [MISS] No results returned (cache miss or bank empty)")
        except Exception as exc:
            print(f"  [ERR]  Error during recall: {exc}")


# -- main() ----------------------------------------------------------------

async def main():
    print()
    print("Hindsight Seed & Verify")
    print(f"  Bank ID  : {hindsight_memory.bank_id}")
    print(f"  Base URL : {hindsight_memory.base_url}")
    await seed()
    await verify()
    print()
    print("=" * 51)
    print("  Done. Memory bank is now populated.")
    print("=" * 51)
    print()


if __name__ == "__main__":
    asyncio.run(main())
