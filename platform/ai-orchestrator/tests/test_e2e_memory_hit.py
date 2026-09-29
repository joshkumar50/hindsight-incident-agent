import pytest
from unittest.mock import AsyncMock, patch
import main

@pytest.mark.asyncio
async def test_e2e_memory_hit():
    # Mock event_bus.publish
    with patch.object(main.event_bus, 'publish', new_callable=AsyncMock) as mock_publish:
        # We also mock httpx.AsyncClient.post just in case it falls through,
        # so we can assert it was NOT called.
        with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
            payload = {
                "incident_id": "TEST-123",
                "description": "auth-service OOMKilled pod restart loop"
            }
            
            await main.coordinate_ai_workflow('INCIDENT_DECLARED', payload, 'msg-1')
            
            # Assert RCA was NOT called
            mock_post.assert_not_called()
            
            # Assert RECOVERY_PLAN_READY was published with memory_hit=True
            found_ready = False
            for call in mock_publish.call_args_list:
                args, kwargs = call
                if args and len(args) > 1 and args[1] == "RECOVERY_PLAN_READY":
                    found_ready = True
                    assert args[2]["memory_hit"] is True, "memory_hit should be True"
                    
            assert found_ready, "RECOVERY_PLAN_READY was not published"
