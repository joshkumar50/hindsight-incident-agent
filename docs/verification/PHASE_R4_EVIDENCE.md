# PHASE_R4_EVIDENCE.md

## Syntax Check
```
ke syntax ok
ai syntax ok
```

## Grep `scores.get` 
(Both return NO occurrences)
```
--- KE Grep ---
--- AI Grep ---
```

## platform/knowledge-engine/main.py (lines 70-120)
```python
    logger.info("searching_knowledge_base", query=query.root_cause)

    if not HINDSIGHT_ENABLED:
        logger.warning("hindsight_not_enabled_search_skipped")
        return {"historical_matches": []}

    try:
        results = hindsight.recall(
            bank_id=_HINDSIGHT_BANK_ID,
            query=query.root_cause,
        )
        def _extract_score(s) -> float:
            if s is None:
                return 0.0
            if isinstance(s, dict):
                return float(s.get("final") or s.get("similarity") or 0.0)
            return float(getattr(s, "final", 0.0) or 0.0)

        matches = []
        for item in results.results:
            score = _extract_score(item.scores)
            matches.append({
                "document_id": getattr(item, "document_id", None),
                "text": item.text,
                "score": score,
                "metadata": item.metadata or {},
            })
        return {"historical_matches": matches}
    except Exception as e:
        logger.error("hindsight_recall_failed", error=str(e))
        return {"historical_matches": []}


@app.post("/retain")
async def retain_history(data: RetainQuery):
    """
    Store new incident resolution into Hindsight memory using retain().
    """
    logger.info("retaining_knowledge_base", incident_id=data.incident_id)

    if not HINDSIGHT_ENABLED:
        logger.warning("hindsight_not_enabled_retain_skipped")
        return {"status": "skipped", "reason": "HINDSIGHT_API_KEY not configured"}

    try:
        hindsight.retain(
            bank_id=_HINDSIGHT_BANK_ID,
            content=f"Incident {data.incident_id} was resolved by: {data.resolution}",
        )
    except Exception as e:
        logger.error("hindsight_retain_failed", error=str(e))
```

## platform/ai-orchestrator/main.py (lines 70-130)
```python
        # AI pipeline and replay the historical playbook immediately.
        # -----------------------------------------------------------------------
        if HINDSIGHT_ENABLED:
            try:
                memory_results = hindsight.recall(
                    bank_id=_HINDSIGHT_BANK_ID,
                    query=incident_description,
                )
                
                def _extract_score(s) -> float:
                    if s is None:
                        return 0.0
                    if isinstance(s, dict):
                        return float(s.get("final") or s.get("similarity") or 0.0)
                    return float(getattr(s, "final", 0.0) or 0.0)

                top_score = 0.0
                top_item = None
                if memory_results.results:
                    top_item = memory_results.results[0]
                    top_score = _extract_score(top_item.scores)

                if top_item is not None and top_score >= _MEMORY_HIT_THRESHOLD:
                    # High-confidence memory hit — short-circuit full pipeline
                    logger.info(
                        "memory_hit_short_circuit",
                        incident_id=incident_id,
                        score=top_score,
                    )
                    
                    await event_bus.publish(
                        "ai_stream",
                        "RECOVERY_PLAN_READY",
                        {
                            "incident_id": incident_id,
                            "memory_hit": True,
                            "rca": top_item.text,
                            "plan": top_item.text,
                        },
                    )
                    await event_bus.publish(
                        "audit_events",
                        "AUTONOMOUS_DECISION",
                        {
                            "incident_id": incident_id,
                            "event_type": "AUTONOMOUS_DECISION",
                            "decision": "MEMORY_RECALL",
                            "confidence_score": top_score,
                            "human_approved": False,
                            "model_name": "hindsight",
                            "rca": top_item.text,
                        },
                    )
                    logger.info(
                        "orchestration_complete_via_memory",
                        incident_id=incident_id,
                    )
                    return  # <-- short-circuit: no LLM pipeline needed
            except Exception as _recall_err:
                # Recall failure must NOT block the normal pipeline
                logger.warning(
```
