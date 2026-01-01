import pytest
import asyncio
from unittest.mock import MagicMock, patch
from ai_safety_radar.models.raw_document import RawDocument
from ai_safety_radar.models.threat_signature import ThreatSignature
from ai_safety_radar.utils.redis_client import RedisClient
from ai_safety_radar.orchestration.ingestion_graph import IngestionGraph
import json
import fakeredis.aioredis
from datetime import datetime

# Mock agents to avoid actual LLM calls
class MockIngestionGraph:
    async def invoke_graph(self, state):
        # Transform raw doc into threat sig directly
        doc = state["doc"]
        sig = ThreatSignature(
            title=f"Analyzed: {doc.title}",
            description="Mock analysis",
            severity=5,
            affected_models=["GPT-4"],
            attack_vector="Prompt Injection",
            technical_details="Details...",
            mitigation="Sanitize inputs",
            published_date=doc.published_date,
            url=doc.url,
            # Fill missing fields required by ThreatSignature
            relevance_score=1.0,
            attack_type="Jailbreak", 
            modality=["Text"],
            is_theoretical=False,
            summary_tldr="TLDR",
            source=doc.source
        )
        return {"threat_signature": sig}

@pytest.fixture
def mock_redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)

@pytest.mark.asyncio
async def test_end_to_end_pipeline_flow(mock_redis):
    # This test simulates the flow:
    # 1. Ingestion pushes to papers:pending
    # 2. Agent Core reads pending, processes, pushes to papers:analyzed
    
    # Setup Mocks
    # We need to patch RedisClient to use our mock_redis instance
    # Since RedisClient creates its own connection in connect(), we need to patch connect/client
    
    with patch("ai_safety_radar.utils.redis_client.redis.from_url", return_value=mock_redis):
        
        # 1. Ingestion Phase simulation
        redis_client = RedisClient()
        await redis_client.connect()
        
        doc = RawDocument(
            id="test:1",
            title="Test Paper",
            content="Abstract: Abstract...\nContent...",
            url="http://arxiv.org/1",
            source="test",
            published_date=datetime(2023, 1, 1),
            metadata={"authors": ["Alice"]}
        )
        
        # Manually push to pending (simulating ingestion_service)
        await redis_client.add_job("papers:pending", doc.model_dump())
        
        # Verify it's in pending
        pending = await redis_client.read_jobs("papers:pending", "group", "consumer", count=1)
        assert len(pending) == 1
        msg_id, payload = pending[0]
        assert payload["title"] == "Test Paper"
        
        # 2. Agent Core Phase simulation
        # We process the message
        # Convert payload back to doc
        doc_received = RawDocument(**payload)
        
        # Run Mock Graph
        # In real run_agent_core, we use IngestionGraph().workflow.invoke()
        # Here we just manually do what agent core does but with MockGraph logic
        
        # Mock logic
        sig = ThreatSignature(
            title=f"Analyzed: {doc_received.title}",
            description="Mock analysis",
            severity=5,
            affected_models=["GPT-4"],
            attack_vector="Prompt Injection",
            technical_details="Details...",
            mitigation="Sanitize inputs",
            published_date=doc_received.published_date,
            url=doc_received.url,
            # Fill missing fields
            relevance_score=1.0,
            attack_type="Jailbreak", 
            modality=["Text"],
            is_theoretical=False,
            summary_tldr="TLDR",
            source=doc_received.source
        )
        
        # Push to analyzed (simulating agent_core)
        await redis_client.add_job("papers:analyzed", sig.model_dump())
        
        # ACK pending
        await redis_client.ack_job("papers:pending", "group", msg_id)
        
        # 3. Verification
        analyzed = await redis_client.read_jobs("papers:analyzed", "group2", "consumer2", count=1)
        assert len(analyzed) == 1
        a_msg_id, a_payload = analyzed[0]
        assert a_payload["severity"] == 5
        assert a_payload["title"] == "Analyzed: Test Paper"
        
        await redis_client.close()
