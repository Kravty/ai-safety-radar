import asyncio
import logging
import os
from dotenv import load_dotenv

from ai_safety_radar.utils.redis_client import RedisClient
from ai_safety_radar.persistence.dataset_manager import DatasetManager
from ai_safety_radar.models.threat_signature import ThreatSignature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def publish_to_hf() -> None:
    """Read analyzed papers from Redis and push to Hugging Face."""
    load_dotenv()
    
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    redis_client = RedisClient(redis_url)
    await redis_client.connect()
    
    dataset_manager = DatasetManager()
    
    CONSUMER_GROUP = "publisher_group"
    CONSUMER_NAME = "publisher_1"
    
    logger.info("Reading 'papers:analyzed' to publish to manual sync...")
    
    batch = []
    ids = []
    
    while True:
        # We read all available
        jobs = await redis_client.read_jobs("papers:analyzed", CONSUMER_GROUP, CONSUMER_NAME, count=10, block=2000)
        
        if not jobs:
            break
            
        for msg_id, payload in jobs:
            try:
                threat = ThreatSignature(**payload)
                batch.append(threat)
                ids.append(msg_id)
            except Exception as e:
                logger.error(f"Invalid threat payload {msg_id}: {e}")
                # ack invalid
                await redis_client.ack_job("papers:analyzed", CONSUMER_GROUP, msg_id)
                
    if batch:
        logger.info(f"Pushing {len(batch)} threats to Hugging Face...")
        dataset_manager.save_threats(batch)
        
        # Ack all
        for msg_id in ids:
             await redis_client.ack_job("papers:analyzed", CONSUMER_GROUP, msg_id)
             
        logger.info("Publish complete.")
    else:
        logger.info("No new analyzed papers found.")
        
    await redis_client.close()

if __name__ == "__main__":
    asyncio.run(publish_to_hf())
