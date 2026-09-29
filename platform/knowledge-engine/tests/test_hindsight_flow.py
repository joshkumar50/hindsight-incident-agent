"""
test_hindsight_flow.py

Tests /search and /retain endpoints of the knowledge-engine using
httpx.AsyncClient + ASGITransport (the correct async approach for
httpx>=0.23 with FastAPI/ASGI apps).

Unit tests always run. Live round-trip test skips without HINDSIGHT_API_KEY.
"""
import os
import sys
import pytest
import httpx
from unittest.mock import MagicMock, patch

# conftest.py has already stubbed pkg.core.* and opentelemetry into sys.modules.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as knowledge_engine_main  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests — use pytest.mark.asyncio + httpx.AsyncClient
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_returns_historical_matches_shape():
    """
    /search must always return {"historical_matches": <list>}.
    When HINDSIGHT_ENABLED=False (no env key) returns empty list — no fake data.
    """
    transport = httpx.ASGITransport(app=knowledge_engine_main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.post("/search", json={"root_cause": "OOMKilled nginx"})
    assert response.status_code == 200
    data = response.json()
    assert "historical_matches" in data
    assert isinstance(data["historical_matches"], list)


@pytest.mark.asyncio
async def test_search_with_mocked_recall():
    """
    When HINDSIGHT_ENABLED=True and recall() is mocked, /search must pass
    the mock return value through unchanged.
    """
    fake_results = [{"incident_id": "INC-001", "resolution": "Restarted pod"}]
    transport = httpx.ASGITransport(app=knowledge_engine_main.app)
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", True), \
         patch.object(knowledge_engine_main, "hindsight") as mock_client:
        mock_client.recall.return_value = fake_results
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            response = await c.post("/search", json={"root_cause": "High CPU on auth-service"})

    assert response.status_code == 200
    data = response.json()
    assert data["historical_matches"] == fake_results
    mock_client.recall.assert_called_once_with(
        bank_id="incident-memory-bank",
        query="High CPU on auth-service",
    )


@pytest.mark.asyncio
async def test_retain_with_mocked_client():
    """
    /retain must call hindsight.retain() with correct bank_id and content.
    """
    transport = httpx.ASGITransport(app=knowledge_engine_main.app)
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", True), \
         patch.object(knowledge_engine_main, "hindsight") as mock_client:
        mock_client.retain.return_value = MagicMock()
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            response = await c.post(
                "/retain",
                json={"incident_id": "INC-123", "resolution": "Scaled pods to 5"},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_client.retain.assert_called_once()
    call_kwargs = mock_client.retain.call_args
    assert call_kwargs.kwargs["bank_id"] == "incident-memory-bank"
    assert "INC-123" in call_kwargs.kwargs["content"]


@pytest.mark.asyncio
async def test_memory_stats_endpoint():
    """
    /memory/stats must return bank_id and total_memories keys.
    """
    transport = httpx.ASGITransport(app=knowledge_engine_main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        response = await c.get("/memory/stats")
    assert response.status_code == 200
    data = response.json()
    assert "bank_id" in data
    assert "total_memories" in data


# ---------------------------------------------------------------------------
# Integration test — skips when HINDSIGHT_API_KEY not set
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.getenv("HINDSIGHT_API_KEY"),
    reason="HINDSIGHT_API_KEY not set — skipping live SDK round-trip",
)
@pytest.mark.asyncio
async def test_recall_retain_roundtrip():
    """
    Live round-trip: retain a test incident then recall it.
    Only runs when HINDSIGHT_API_KEY is present in the environment.
    """
    from hindsight_client import Hindsight  # type: ignore

    client_live = Hindsight(
        os.getenv("HINDSIGHT_BASE_URL", "https://memory.hindsight.vectorize.io"),
        api_key=os.getenv("HINDSIGHT_API_KEY"),
    )
    bank_id = "incident-memory-bank"
    test_content = "TEST-ROUNDTRIP: OOMKilled pod resolved by increasing memory limit."

    client_live.retain(bank_id=bank_id, content=test_content)
    results = client_live.recall(bank_id=bank_id, query="OOMKilled pod memory limit")
    assert results is not None
