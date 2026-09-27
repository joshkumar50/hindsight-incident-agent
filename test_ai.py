import asyncio
import os
import sys

# Ensure backend is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(ROOT_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from shared.models import AnalysisRequest
from shared.database import hindsight_memory
from agent.agent_workflow import AgentWorkflow

async def main():
    print("--- Testing Hindsight Recall ---")
    query = "Why is the checkout service returning 500 errors?"
    try:
        # We seeded this exactly in seed_memory.py
        results = await hindsight_memory.recall(query, top_k=1)
        print(f"Hindsight Recall Results: {results}")
    except Exception as e:
        print(f"Hindsight Recall failed: {e}")

    print("\n--- Testing AgentWorkflow ---")
    req = AnalysisRequest(
        query="High CPU usage on search microservice.",
        target_service="search-service",
        target_namespace="production",
        lookback_minutes=60,
        source="test_script"
    )
    agent = AgentWorkflow()
    try:
        response = await agent.run(req)
        print("Agent Workflow Success!")
        print(f"Model used: {response.rca.llm_model_used}")
        print(f"Root Cause: {response.rca.root_cause_summary}")
        print(f"Confidence: {response.rca.confidence_score}")
    except Exception as e:
        print(f"Agent Workflow failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
