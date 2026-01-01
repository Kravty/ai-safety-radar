import asyncio
import logging
import os
from dotenv import load_dotenv

from ai_safety_radar.utils.redis_client import RedisClient
from ai_safety_radar.utils.logging import ForensicLogger
from ai_safety_radar.orchestration.ingestion_graph import IngestionGraph
from ai_safety_radar.models.raw_document import RawDocument

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_agent_core() -> None:
    load_dotenv()
    
    forensic = ForensicLogger("agent_core")
    forensic.log_event("SYSTEM_START", "INFO", details={"msg": "Starting Agent Core Service (Air-Gapped)"})
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = RedisClient(redis_url)
    await redis_client.connect()
    
    # Initialize the Workflow (Graph) from Phase 2
    ingestion_graph = IngestionGraph()
    
    CONSUMER_GROUP = "agent_group"
    CONSUMER_NAME = "agent_worker_1"
    
    logger.info(f"Listening for jobs in 'papers:pending' as {CONSUMER_GROUP}...")
    
    while True:
        try:
            # Read new jobs
            jobs = await redis_client.read_jobs("papers:pending", CONSUMER_GROUP, CONSUMER_NAME, count=1, block=5000)
            
            for msg_id, payload in jobs:
                try:
                    forensic.log_event("JOB_RECEIVED", "INFO", details={"msg_id": msg_id})
                    
                    # Parse document
                    doc = RawDocument(**payload)
                    
                    # Run Analysis Workflow (Phase 2 logic)
                    forensic.log_event("ANALYSIS_START", "INFO", input_text=doc.content[:100], details={"doc_id": doc.id})
                    
                    # IngestionGraph.run() sets state but doesn't return the signature directly.
                    # We need to modify IngestionGraph to allow retrieving the result or getting it from state.
                    # Actually IngestionGraph.run() is simpler. Let's look at IngestionGraph implementation.
                    # It calls self.workflow.invoke(initial_state).
                    # Invocation returns the final state.
                    # So we should modify IngestionGraph.run to return the state OR use invoke directly here.
                    # Let's use invoke directly to access the result.
                    
                    initial_state = {"doc": doc, "is_relevant": False, "threat_signature": None}
                    final_state = await ingestion_graph.workflow.invoke(initial_state)
                    
                    threat_sig = final_state.get("threat_signature")
                    
                    if threat_sig:
                        # Success - Push to 'papers:analyzed'
                        result_payload = threat_sig.model_dump()
                        if hasattr(result_payload.get('published_date'), 'isoformat'):
                             result_payload['published_date'] = result_payload['published_date'].isoformat()
                             
                        await redis_client.add_job("papers:analyzed", result_payload)
                        forensic.log_event("THREAT_DETECTED", "WARN", details={"threat_id": threat_sig.title, "severity": threat_sig.severity})
                        logger.info(f"Threat detected: {threat_sig.title}")
                    else:
                        forensic.log_event("ANALYSIS_COMPLETE", "INFO", details={"result": "No threat or Irrelevant"})
                        
                    # Ack
                    await redis_client.ack_job("papers:pending", CONSUMER_GROUP, msg_id)
                    
                except Exception as e:
                    logger.error(f"Error processing job {msg_id}: {e}")
                    forensic.log_event("JOB_ERROR", "ERROR", details={"error": str(e), "msg_id": msg_id})
                    # We ack even on error to avoid poison pill loop since we don't have DLQ
                    await redis_client.ack_job("papers:pending", CONSUMER_GROUP, msg_id)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Redis loop error: {e}")
            await asyncio.sleep(5) # Backoff
            
    await redis_client.close()
    forensic.log_event("SYSTEM_STOP", "INFO")

if __name__ == "__main__":
    asyncio.run(run_agent_core())
