import asyncio
import logging
import os
from dotenv import load_dotenv

from ai_safety_radar.ingestion.arxiv import ArXivIngester
from ai_safety_radar.utils.redis_client import RedisClient
from ai_safety_radar.utils.logging import ForensicLogger
from ai_safety_radar.config import settings
from ai_safety_radar.agents.filter_agent import FilterAgent
from ai_safety_radar.utils.llm_client import LLMClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FilterAgent with LLM client
_filter_agent = None

def get_filter_agent():
    """Lazy initialization of FilterAgent."""
    global _filter_agent
    if _filter_agent is None:
        llm_client = LLMClient()  # Uses instructor + litellm with env vars
        _filter_agent = FilterAgent(llm_client)
        logger.info("✅ FilterAgent initialized with LLM")
    return _filter_agent

async def run_ingestion_cycle(redis_client, forensic, days_back=30):
    """Single execution of the ingestion process using FilterAgent LLM."""
    arxiv_ingester = ArXivIngester()
    filter_agent = get_filter_agent()
    accepted_count = 0
    rejected_count = 0
    
    try:
        logger.info(f"📡 Fetching recent papers from ArXiv (last {days_back} days)...")
        
        papers = []
        async for doc in arxiv_ingester.fetch_recent(days_back=days_back, max_results=settings.arxiv_max_results):
            papers.append(doc)
        
        logger.info(f"📊 Retrieved {len(papers)} papers from ArXiv")
        
        for i, doc in enumerate(papers, 1):
            logger.info(f"📄 Paper {i}/{len(papers)}: {doc.title[:70]}...")
            
            # USE FILTERAGENT LLM (not keyword matching!)
            try:
                filter_result = await filter_agent.analyze(doc.title, doc.content)
                
                if filter_result.is_relevant:
                    # Publish to Redis
                    payload = doc.model_dump()
                    if hasattr(payload.get('published_date'), 'isoformat'):
                        payload['published_date'] = payload['published_date'].isoformat()
                    
                    await redis_client.add_job("papers:pending", payload)
                    accepted_count += 1
                    logger.info(f"  ✅ ACCEPTED (confidence: {filter_result.confidence_score:.2f})")
                    logger.info(f"     Reasoning: {filter_result.reasoning[:100]}...")
                    
                    forensic.log_event("JOB_PUBLISHED", "INFO", details={"doc_id": doc.id, "title": doc.title})
                else:
                    rejected_count += 1
                    logger.warning(f"  ❌ REJECTED (confidence: {filter_result.confidence_score:.2f})")
                    logger.warning(f"     Reasoning: {filter_result.reasoning[:100]}...")
                    
            except Exception as e:
                logger.error(f"  ❌ FilterAgent error: {e}")
                # Fail-safe: Accept on error
                payload = doc.model_dump()
                if hasattr(payload.get('published_date'), 'isoformat'):
                    payload['published_date'] = payload['published_date'].isoformat()
                await redis_client.add_job("papers:pending", payload)
                accepted_count += 1
                logger.info(f"  ⚠️ Accepted due to error (fail-safe)")
            
        logger.info(f"📊 Ingestion Summary: {accepted_count} accepted, {rejected_count} rejected")
        forensic.log_event("INGESTION_COMPLETE", "INFO", details={"queued_count": accepted_count})
        
    except Exception as e:
        forensic.log_event("INGESTION_ERROR", "CRITICAL", details={"error": str(e)})
        logger.error(f"Ingestion failed: {e}")

async def listen_for_triggers(redis_client, trigger_callback):
    """Listens for manual triggers."""
    pubsub = redis_client.client.pubsub()
    await pubsub.subscribe("agent:trigger")
    logger.info("Listening for manual triggers on 'agent:trigger'...")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            
            if data == "ingest":
                logger.info("⚡ Manual ingestion trigger received!")
                await trigger_callback()

async def run_ingestion_service() -> None:
    load_dotenv()
    
    forensic = ForensicLogger("ingestion_service")
    forensic.log_event("SYSTEM_START", "INFO", details={"msg": "Starting Ingestion Service"})
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # We need two clients: one for operations, one blocking for pubsub? 
    # RedisClient wrapper usually handles one connection. 
    # PubSub in async redis usually requires its own connection or careful management if blocking.
    # Let's use separate client for pubsub if needed, or just share if safe. 
    # Ideally, we run listener in background task.
    
    redis_client = RedisClient(redis_url)
    await redis_client.connect()
    
    # Callback for trigger
    async def trigger_handler():
        await run_ingestion_cycle(redis_client, forensic)
    
    # Start listener
    asyncio.create_task(listen_for_triggers(redis_client, trigger_handler))
    
    # Main Loop (Scheduler)
    SCHEDULE_INTERVAL = 6 * 3600 # 6 hours
    
    # Run once on startup
    await run_ingestion_cycle(redis_client, forensic)
    
    logger.info(f"Entering schedule loop (Interval: {SCHEDULE_INTERVAL}s)")
    
    while True:
        await asyncio.sleep(SCHEDULE_INTERVAL)
        logger.info("⏰ Scheduled ingestion starting...")
        await run_ingestion_cycle(redis_client, forensic)

    await redis_client.close()
    forensic.log_event("SYSTEM_STOP", "INFO")

if __name__ == "__main__":
    asyncio.run(run_ingestion_service())
