import asyncio
import logging
import os
import json
from dotenv import load_dotenv

from ai_safety_radar.utils.redis_client import RedisClient
from ai_safety_radar.utils.logging import ForensicLogger
from ai_safety_radar.orchestration.ingestion_graph import IngestionGraph
from ai_safety_radar.models.raw_document import RawDocument
from ai_safety_radar.models.threat_signature import ThreatSignature

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_curator_workflow(redis_client):
    """Generate threat landscape summary from analyzed papers."""
    logger.info("Running CuratorAgent to synthesize threat intelligence...")
    
    # Read last 20 analyzed papers from Redis
    messages = await redis_client.client.xrevrange("papers:analyzed", count=20)
    
    if not messages:
        logger.warning("No analyzed papers found for Curator")
        return
    
    # Extract threat data
    threat_list = []
    for msg_id, data in messages:
        try:
             # RedisClient stores data as {"data": json_string}
             if "data" in data and isinstance(data["data"], str):
                 payload = json.loads(data["data"])
             else:
                 payload = data

             # Redis returns data as dict, need to convert to ThreatSignature
             # Adjust published_date if string
             ts = ThreatSignature(**payload)
             threat_list.append(ts)
        except Exception as e:
             logger.warning(f"Skipping malformed threat data {msg_id}: {e}")
    
    logger.info(f"Curator processing {len(threat_list)} analyzed papers")
    
    logger.info(f"Curator processing {len(threat_list)} analyzed papers")
    
    # Run Editorial/Curator Workflow
    try:
        from ai_safety_radar.orchestration.editorial_graph import EditorialGraph
        editorial = EditorialGraph()
        
        # EditorialGraph.run() calls the workflow internally
        # It handles the creation of initial state
        briefing = await editorial.run(threats=threat_list, previous_summary="")
        
        if briefing:
            summary = briefing.summary_markdown
            logger.info("✅ Curator briefing generated successfully")
        else:
            summary = "No briefing generated (Workflow returned None)"
            logger.warning("Curator workflow returned no output")
            
        # Save summary to Redis for dashboard
        await redis_client.client.set("curator:latest_summary", summary)
        logger.info("✅ Curator summary saved to Redis")
        
    except Exception as e:
        logger.error(f"Failed to run Curator/Editorial workflow: {e}")
        # Build a safe fallback so dashboard doesn't crash
        await redis_client.client.set("curator:latest_summary", f"Error generating summary: {e}")

async def listen_for_triggers(redis_client, process_callback):
    """Listens for manual processing triggers via Redis PubSub."""
    pubsub = redis_client.client.pubsub()
    await pubsub.subscribe("agent:trigger")
    logger.info("Listening for manual triggers on 'agent:trigger'...")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            logger.info(f"⚡ Manual trigger received: {data}")
            
            try:
                if data == "process_with_curator":
                    await process_callback(manual=True, run_curator=True)
                else:
                    await process_callback(manual=True)
            except Exception as e:
                logger.error(f"Manual trigger processing failed: {e}")



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
    
    analyzed_count_ref = {"count": 0}

    # Define processing logic to be reusable
    async def process_batch(manual=False, run_curator=False):
        try:
             if run_curator:
                 await run_curator_workflow(redis_client)
                 return

             # Block less usage if manual
             block_time = 1000 if manual else 5000
             jobs = await redis_client.read_jobs("papers:pending", CONSUMER_GROUP, CONSUMER_NAME, count=1, block=block_time)
             
             if not jobs and not manual:
                 # Just return, outer loop continues
                 return

             for msg_id, payload in jobs:
                try:
                    forensic.log_event("JOB_RECEIVED", "INFO", details={"msg_id": msg_id})
                    
                    # Parse document
                    doc = RawDocument(**payload)
                    
                    # Run Analysis Workflow (Phase 2 logic)
                    forensic.log_event("ANALYSIS_START", "INFO", input_text=doc.content[:100], details={"doc_id": doc.id})
                    
                    # FIX: Use ainvoke for async graph execution
                    initial_state = {"doc": doc, "is_relevant": False, "threat_signature": None}
                    final_state = await ingestion_graph.workflow.ainvoke(initial_state)
                    
                    threat_sig = final_state.get("threat_signature")
                    
                    if threat_sig:
                        # Success - Push to 'papers:analyzed'
                        result_payload = threat_sig.model_dump()
                        if hasattr(result_payload.get('published_date'), 'isoformat'):
                             result_payload['published_date'] = result_payload['published_date'].isoformat()
                             
                        await redis_client.add_job("papers:analyzed", result_payload)
                        forensic.log_event("THREAT_DETECTED", "WARN", details={"threat_id": threat_sig.title, "severity": threat_sig.severity})
                        logger.info(f"✅ Threat detected: {threat_sig.title}")
                    else:
                        forensic.log_event("ANALYSIS_COMPLETE", "INFO", details={"result": "No threat or Irrelevant"})
                        logger.info(f"Analysis complete (Irrelevant): {doc.id}")

                    # Increment analyzed count for auto-curation
                    analyzed_count_ref["count"] += 1
                    if analyzed_count_ref["count"] % 5 == 0:
                        await run_curator_workflow(redis_client)
                        
                    # Ack
                    await redis_client.client.xack("papers:pending", CONSUMER_GROUP, msg_id)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing job {msg_id}: {e}")
                    forensic.log_event("JOB_ERROR", "ERROR", details={"error": str(e), "msg_id": msg_id})
                    # We ack even on error to avoid poison pill loop since we don't have DLQ
                    await redis_client.client.xack("papers:pending", CONSUMER_GROUP, msg_id)
        except Exception as e:
             if manual: raise e # Propagate if manual
             # Otherwise log and continue
             logger.error(f"Batch processing error: {e}")

    # Start PubSub listener in background
    asyncio.create_task(listen_for_triggers(redis_client, process_batch))

    while True:
        try:
            await process_batch()
            # Small sleep to prevent tight loop if not blocking or if error
            await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"⚠️ Redis loop error: {e}")
            await asyncio.sleep(5) # Backoff
            
    await redis_client.close()
    forensic.log_event("SYSTEM_STOP", "INFO")

if __name__ == "__main__":
    asyncio.run(run_agent_core())
