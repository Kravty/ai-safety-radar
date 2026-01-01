import asyncio
import logging
import os
from dotenv import load_dotenv

from ai_safety_radar.ingestion.arxiv import ArXivIngester
from ai_safety_radar.utils.redis_client import RedisClient
from ai_safety_radar.utils.logging import ForensicLogger
from ai_safety_radar.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_ingestion_service() -> None:
    load_dotenv()
    
    forensic = ForensicLogger("ingestion_service")
    forensic.log_event("SYSTEM_START", "INFO", details={"msg": "Starting Ingestion Service"})
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = RedisClient(redis_url)
    await redis_client.connect()
    
    arxiv_ingester = ArXivIngester()
    
    logger.info("Fetching recent papers from ArXiv...")
    count = 0
    try:
        async for doc in arxiv_ingester.fetch_recent(days_back=1, max_results=settings.arxiv_max_results):
            # Publish to Redis
            payload = doc.model_dump()
            # Pydantic date serialization might be needed if not handled by json dumps inside redis client
            # But json.dumps handles strings. RawDocument fields are mostly strings/ints.
            # datetime needs isoformat.
            if hasattr(payload.get('published_date'), 'isoformat'):
                payload['published_date'] = payload['published_date'].isoformat()
            
            await redis_client.add_job("papers:pending", payload)
            
            forensic.log_event("JOB_PUBLISHED", "INFO", details={"doc_id": doc.id, "title": doc.title})
            logger.info(f"Queued paper: {doc.title}")
            count += 1
            
    except Exception as e:
        forensic.log_event("INGESTION_ERROR", "CRITICAL", details={"error": str(e)})
        logger.error(f"Ingestion failed: {e}")
    finally:
        await redis_client.close()
        logger.info(f"Ingestion complete. Queued {count} papers.")
        forensic.log_event("SYSTEM_STOP", "INFO", details={"queued_count": count})

if __name__ == "__main__":
    asyncio.run(run_ingestion_service())
