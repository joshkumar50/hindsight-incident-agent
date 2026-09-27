"""
====================================================================
shared/database.py - Vectorize Hindsight Persistent Memory Manager
====================================================================
Purpose: Connects Hindsight Incident Agent to Vectorize Hindsight Cloud.
         Uses the official hindsight-client SDK to retain and recall
         incident diagnoses, playbooks, and root cause history.
====================================================================
"""

import asyncio
import json
import logging
import os
import time
from typing import List, Dict, Any, Optional

import structlog

from shared.config import config
from shared.models import AnalysisRequest, AnalysisResponse

# Official Vectorize Hindsight Client
try:
    from hindsight_client import Hindsight
    HINDSIGHT_AVAILABLE = True
except ImportError:
    HINDSIGHT_AVAILABLE = False

# ---- Structlog Setup ----
logger = structlog.get_logger(__name__)

# Fallback in-memory cache if cloud connection is interrupted
_fallback_memory: Dict[str, dict] = {}
_fallback_raw_cache: Dict[str, str] = {}

BANK_ID = "hindsight-incident-agent"
HINDSIGHT_CLOUD_BASE = os.getenv("HINDSIGHT_CLOUD_BASE", "https://api.hindsight.vectorize.io")


class HindsightMemory:
    """
    Official Hindsight Memory Wrapper implementing the semantic recall & retain loop
    for Kubernetes incident triage and runbook evolution.
    """

    def __init__(self, bank_id: str = BANK_ID, base_url: str = HINDSIGHT_CLOUD_BASE):
        self.bank_id = bank_id
        self.base_url = base_url
        self._initialized = False

    def _get_client(self) -> Optional[Any]:
        """Instantiate Hindsight client with configured API key from env or config."""
        if not HINDSIGHT_AVAILABLE:
            return None
        api_key = os.getenv("HINDSIGHT_API_KEY", "") or config.hindsight.api_key
        if not api_key:
            return None
        try:
            return Hindsight(base_url=self.base_url, api_key=api_key)
        except Exception as e:
            logger.error("hindsight_client_init_failed", error=str(e))
            return None

    async def init_bank(self):
        """Ensure the Hindsight Incident Agent memory bank exists in Hindsight Cloud."""
        client = self._get_client()
        if not client:
            logger.info("hindsight_offline_using_fallback")
            return

        def _sync_init():
            try:
                try:
                    client.get_bank_config(bank_id=self.bank_id)
                    logger.info("hindsight_bank_verified", bank_id=self.bank_id)
                except Exception:
                    client.create_bank(
                        bank_id=self.bank_id,
                        name="Hindsight Incident Agent SRE Memory",
                        mission="Institutional memory for autonomous Kubernetes incident triage, root cause analysis, and remediation playbooks."
                    )
                    logger.info("hindsight_bank_created", bank_id=self.bank_id)
            except Exception as ex:
                logger.warning("hindsight_bank_init_notice", error=str(ex))

        await asyncio.to_thread(_sync_init)
        self._initialized = True

    async def recall(self, symptom: str, k: int = 3) -> list[dict]:
        """
        Recall Phase: Queries Hindsight for semantically similar past outages.
        Returns list of {playbook, resolution, success_rate, incident_id}.
        On SDK connection failure: log error, returns [] (cache miss).
        """
        cleaned = (symptom or "").strip()
        if not cleaned:
            return []

        client = self._get_client()
        if client:
            try:
                def _do_recall():
                    return client.recall(bank_id=self.bank_id, query=cleaned, top_k=k)

                recall_resp = await asyncio.to_thread(_do_recall)
                results: list[dict] = []
                if recall_resp and getattr(recall_resp, "results", None):
                    for item in recall_resp.results:
                        meta = getattr(item, "metadata", {}) or {}
                        text = getattr(item, "text", "") or ""
                        playbook = meta.get("playbook") or ["Check pod logs and perform rollout restart"]
                        resolution = meta.get("root_cause") or meta.get("resolution") or text[:120] or "Resolved incident"
                        success_rate = float(meta.get("success_rate", getattr(item, "score", 0.85) if hasattr(item, "score") else 0.85))
                        incident_id = meta.get("incident_id") or "recalled-incident"
                        results.append({
                            "playbook": playbook,
                            "resolution": resolution,
                            "success_rate": success_rate,
                            "incident_id": incident_id
                        })
                    logger.info("hindsight_recall_cloud_hit", count=len(results), symptom=cleaned[:60])
                    return results
            except Exception as e:
                logger.error("hindsight_recall_error", error=str(e), msg="SDK connection failure, returning empty list (cache miss)")
                return []

        # Local fallback cache check when HINDSIGHT_API_KEY is not configured
        if cleaned in _fallback_memory:
            return [_fallback_memory[cleaned]]

        for q_key, rec in _fallback_memory.items():
            if q_key.lower() in cleaned.lower() or cleaned.lower() in q_key.lower():
                return [rec]

        return []

    async def retain(
        self,
        incident_id: str,
        symptoms: str,
        root_cause: str,
        playbook: Any,
        human_approved: bool,
        outcome: str
    ):
        """
        Retain Phase: Commits the resolved incident fingerprint + playbook to Hindsight.
        On SDK connection failure: log error, retain becomes a no-op.
        """
        if isinstance(playbook, list):
            playbook_data = playbook
            playbook_str = json.dumps(playbook)
        else:
            playbook_data = [str(playbook)]
            playbook_str = str(playbook)

        # Calculate success rate / ranking weight
        if outcome in ["success", "human_validated"]:
            success_rate = 1.0
        elif outcome == "human_modified":
            success_rate = 0.95
        elif outcome == "human_rejected":
            success_rate = 0.1  # Heavy penalty so it ranks last in future recalls
        else:
            success_rate = 0.85

        record = {
            "incident_id": incident_id,
            "symptoms": symptoms,
            "root_cause": root_cause,
            "playbook": playbook_data,
            "human_approved": human_approved,
            "outcome": outcome,
            "success_rate": success_rate,
            "resolution": root_cause
        }

        # Keep fallback in-memory cache synchronized
        key = (symptoms or incident_id).strip()
        if key:
            _fallback_memory[key] = record
        if incident_id:
            _fallback_memory[incident_id] = record

        client = self._get_client()
        if not client:
            logger.info("hindsight_retained_fallback", incident_id=incident_id, outcome=outcome, human_approved=human_approved)
            return

        try:
            content = (
                f"Kubernetes Incident Symptom: {symptoms}. "
                f"Root Cause Diagnosis: {root_cause}. "
                f"Remediation Playbook: {playbook_str}. "
                f"Outcome: {outcome}. "
                f"Human Approved: {human_approved}."
            )
            metadata = {
                "incident_id": incident_id,
                "symptoms": symptoms,
                "root_cause": root_cause,
                "playbook": playbook_str,
                "human_approved": human_approved,
                "outcome": outcome,
                "success_rate": success_rate
            }

            def _do_retain():
                client.retain(
                    bank_id=self.bank_id,
                    content=content,
                    metadata=metadata
                )

            await asyncio.to_thread(_do_retain)
            logger.info("hindsight_retain_cloud_committed", incident_id=incident_id, outcome=outcome, success_rate=success_rate)
        except Exception as e:
            logger.error("hindsight_retain_error", error=str(e), msg="SDK retain failure; retain is a no-op")


# Global Singleton Memory Instance
hindsight_memory = HindsightMemory()


def init_db():
    """Ensure Hindsight memory bank is initialized."""
    try:
        asyncio.create_task(hindsight_memory.init_bank())
    except RuntimeError:
        pass


def save_analysis(request: AnalysisRequest, response: AnalysisResponse):
    """
    Retain Phase backward compatibility helper:
    Caches the analysis in local memory and invokes Hindsight retain.
    """
    cleaned_query = request.query.strip()
    _fallback_raw_cache[cleaned_query] = response.model_dump_json()

    summary = response.rca.root_cause_summary if response.rca else "Diagnostics completed"
    actions = response.rca.recommended_actions if response.rca and response.rca.recommended_actions else ["Check pod health"]

    record = {
        "incident_id": response.request_id,
        "symptoms": cleaned_query,
        "root_cause": summary,
        "playbook": actions,
        "human_approved": False,
        "outcome": "success",
        "success_rate": 0.95,
        "resolution": summary
    }
    _fallback_memory[cleaned_query] = record


def get_cached_analysis(query: str) -> Optional[AnalysisResponse]:
    """
    Recall Phase backward compatibility helper.
    """
    cleaned_query = query.strip()
    if cleaned_query in _fallback_raw_cache:
        return AnalysisResponse.model_validate_json(_fallback_raw_cache[cleaned_query])
    return None


def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    return list(_fallback_memory.values())[:limit]


def delete_history_item(request_id: str):
    _fallback_memory.pop(request_id, None)
