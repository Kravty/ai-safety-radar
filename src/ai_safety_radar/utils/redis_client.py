import redis.asyncio as redis
from typing import Any, Dict, List, Optional, Tuple, cast
import logging
import json

logger = logging.getLogger(__name__)

class RedisClient:
    """Wrapper for Async Redis Streams."""
    
    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        
    async def connect(self) -> None:
        self.client = redis.from_url(self.redis_url, decode_responses=True) # type: ignore[no-untyped-call]
        logger.info(f"Connected to Redis at {self.redis_url}")
        
    async def close(self) -> None:
        if self.client:
            await self.client.aclose()
            
    async def add_job(self, queue_name: str, payload: Dict[str, Any]) -> str:
        """Add a job to a stream."""
        if not self.client:
            await self.connect()
            
        # Wrap payload in 'data' field as JSON string
        data_str = json.dumps(payload)
        
        # Redis client type hint is incomplete for xadd, ignore it or cast
        cl = cast(redis.Redis, self.client)
        msg_id = await cl.xadd(queue_name, {"data": data_str})
        return str(msg_id)
        
    async def read_jobs(self, queue_name: str, consumer_group: str, consumer_name: str, count: int = 1, block: int = 0) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Read jobs via Consumer Group.
        Returns list of (msg_id, payload).
        """
        if not self.client:
            await self.connect()
            
        cl = cast(redis.Redis, self.client)
            
        # Ensure group exists
        try:
            await cl.xgroup_create(queue_name, consumer_group, mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
                
        # XREADGROUP
        streams: Any = {queue_name: ">"}
        messages = await cl.xreadgroup(consumer_group, consumer_name, streams=streams, count=count, block=block)
        
        results = []
        if messages:
            # messages format: [['stream_name', [('msg_id', {'data': '...'})]]]
            for stream, msgs in messages:
                for msg_id, data in msgs:
                    try:
                        payload = json.loads(data['data'])
                        results.append((msg_id, payload))
                    except Exception as e:
                        logger.error(f"Failed to unserialize Redis message {msg_id}: {e}")
                        
        return results
        
    async def ack_job(self, queue_name: str, consumer_group: str, msg_id: str) -> None:
        if not self.client:
            await self.connect()
        
        cl = cast(redis.Redis, self.client)
        await cl.xack(queue_name, consumer_group, msg_id)
