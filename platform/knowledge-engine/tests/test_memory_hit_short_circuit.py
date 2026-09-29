"""
test_memory_hit_short_circuit.py

Verifies /search response shape for the AI Orchestrator short-circuit path.
Uses httpx.AsyncClient + ASGITransport. Pure unit tests — no network calls.
"""
import os
import sys
import pytest
import httpx
from unittest.mock import MagicMock, patch

# conftest.py has already stubbed pkg.core.* and opentelemetry into sys.modules.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main as knowledge_engine_main  # noqa: E402


async def _post(path: str, json: dict):
    transport = httpx.ASGITransport(app=knowledge_engine_main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        return await c.post(path, json=json)


@pytest.mark.asyncio
async def test_high_confidence_hit_shape():
    """
    When recall() returns success_rate >= 0.8, the response shape must allow
    the orchestrator to read the score without KeyError.
    """
    fake_hit = {
        "incident_id": "INC-044",
        "resolution": "Restart Auth Service Pods",
        "success_rate": 0.95,
    }
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", True), \
         patch.object(knowledge_engine_main, "hindsight") as mock_client:
        mock_client.recall.return_value = [fake_hit]
        response = await _post("/search", {"root_cause": "cpu high on auth-service"})

    assert response.status_code == 200
    matches = response.json().get("historical_matches", [])
    assert len(matches) == 1
    assert matches[0]["success_rate"] >= 0.8


@pytest.mark.asyncio
async def test_low_confidence_hit_does_not_short_circuit():
    """
    Low-confidence result (< 0.8) is returned faithfully so the orchestrator
    falls through to the full pipeline.
    """
    fake_hit = {"incident_id": "INC-099", "resolution": "Unknown fix", "success_rate": 0.4}
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", True), \
         patch.object(knowledge_engine_main, "hindsight") as mock_client:
        mock_client.recall.return_value = [fake_hit]
        response = await _post("/search", {"root_cause": "disk full"})

    assert response.status_code == 200
    matches = response.json().get("historical_matches", [])
    assert matches[0]["success_rate"] < 0.8


@pytest.mark.asyncio
async def test_empty_recall_returns_empty_list():
    """
    Empty recall result → {"historical_matches": []} — no exception, no fake data.
    """
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", True), \
         patch.object(knowledge_engine_main, "hindsight") as mock_client:
        mock_client.recall.return_value = []
        response = await _post("/search", {"root_cause": "unknown error"})

    assert response.status_code == 200
    assert response.json() == {"historical_matches": []}


@pytest.mark.asyncio
async def test_recall_exception_returns_empty_list():
    """
    recall() raising an exception → {"historical_matches": []} not a 500.
    """
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", True), \
         patch.object(knowledge_engine_main, "hindsight") as mock_client:
        mock_client.recall.side_effect = RuntimeError("Hindsight API timeout")
        response = await _post("/search", {"root_cause": "any error"})

    assert response.status_code == 200
    assert response.json() == {"historical_matches": []}


@pytest.mark.asyncio
async def test_hindsight_disabled_returns_empty_list():
    """
    HINDSIGHT_ENABLED=False → {"historical_matches": []} — no fake data.
    """
    with patch.object(knowledge_engine_main, "HINDSIGHT_ENABLED", False):
        response = await _post("/search", {"root_cause": "any error"})

    assert response.status_code == 200
    assert response.json() == {"historical_matches": []}
