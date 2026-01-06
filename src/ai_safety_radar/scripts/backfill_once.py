#!/usr/bin/env python3
"""
One-shot backfill script for AI Safety Radar.

Fetches historical papers from ArXiv and publishes accepted ones to papers:pending.
Does NOT run in a loop - executes once and exits with summary.

Usage:
    python -m ai_safety_radar.scripts.backfill_once --days-back 60 --max-results 200
    python -m ai_safety_radar.scripts.backfill_once --days-back 30 --max-results 100 --dry-run
"""
import argparse
import asyncio
import logging
import time
from datetime import datetime

from ..ingestion.arxiv import ArXivIngester
from ..agents.filter_agent import FilterAgent
from ..utils.llm_client import LLMClient
from ..utils.redis_client import RedisClient
from ..utils.logging import ForensicLogger
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONSUMER_GROUP = "agent_group"


async def safe_reset_streams(redis_client: RedisClient) -> None:
    """
    Safely reset streams without FLUSHDB (which breaks consumer groups).
    
    Deletes papers:pending and papers:analyzed, then recreates consumer group.
    """
    logger.info("🔄 Safe reset: deleting streams...")
    
    # Delete streams
    await redis_client.client.delete("papers:pending")
    await redis_client.client.delete("papers:analyzed")
    
    # Delete any processed markers
    keys = await redis_client.client.keys("processed:*")
    if keys:
        await redis_client.client.delete(*keys)
        logger.info(f"  Deleted {len(keys)} processed markers")
    
    # Recreate consumer group with MKSTREAM
    try:
        await redis_client.client.xgroup_create(
            "papers:pending", CONSUMER_GROUP, id="0", mkstream=True
        )
        logger.info("  ✅ Consumer group recreated")
    except Exception as e:
        if "BUSYGROUP" in str(e):
            logger.info("  Consumer group already exists")
        else:
            raise
    
    logger.info("✅ Safe reset complete")


async def run_backfill(
    days_back: int,
    max_results: int,
    batch_size: int,
    sleep_seconds: float,
    dry_run: bool,
    reset: bool
) -> dict:
    """
    Execute one-shot backfill.
    
    Returns:
        Summary dict with fetched/accepted/rejected counts and duration.
    """
    start_time = time.time()
    
    # Initialize components
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = RedisClient(redis_url)
    await redis_client.connect()
    
    forensic = ForensicLogger("backfill")
    forensic.log_event("BACKFILL_START", "INFO", details={
        "days_back": days_back,
        "max_results": max_results,
        "dry_run": dry_run
    })
    
    # Safe reset if requested
    if reset and not dry_run:
        await safe_reset_streams(redis_client)
    
    # Ensure consumer group exists
    try:
        await redis_client.client.xgroup_create(
            "papers:pending", CONSUMER_GROUP, id="0", mkstream=True
        )
    except Exception:
        pass  # Group exists
    
    # Initialize filter agent
    filter_client = LLMClient(role="filter")
    filter_agent = FilterAgent(filter_client)
    
    # Fetch papers (async iterator)
    arxiv_ingester = ArXivIngester()
    logger.info(f"📡 Fetching papers from last {days_back} days (max {max_results})...")
    
    # Collect papers from async iterator
    papers = []
    async for paper in arxiv_ingester.fetch_recent(
        max_results=max_results,
        days_back=days_back
    ):
        papers.append(paper)
    
    fetched_count = len(papers)
    logger.info(f"📚 Fetched {fetched_count} papers from ArXiv")
    
    # Process papers
    accepted_count = 0
    rejected_count = 0
    
    for i, paper in enumerate(papers):
        try:
            # Filter using content field (contains abstract)
            result = await filter_agent.analyze(paper.title, paper.content)
            
            if result.is_relevant:
                accepted_count += 1
                logger.info(f"  ✅ [{i+1}/{fetched_count}] ACCEPTED: {paper.title[:60]}...")
                
                if not dry_run:
                    # Publish to pending queue
                    payload = {
                        "id": paper.id,
                        "title": paper.title,
                        "content": paper.content,
                        "source": paper.source,
                        "url": paper.url,
                        "published_date": paper.published_date.isoformat() if paper.published_date else None,
                        "metadata": paper.metadata,
                    }
                    await redis_client.add_job("papers:pending", payload)
            else:
                rejected_count += 1
                if (i + 1) % 10 == 0:  # Log every 10th rejection to reduce noise
                    logger.info(f"  ❌ [{i+1}/{fetched_count}] REJECTED: {paper.title[:60]}...")
            
            # Rate limiting between batches
            if (i + 1) % batch_size == 0:
                logger.info(f"  📊 Progress: {i+1}/{fetched_count} processed, {accepted_count} accepted")
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)
                    
        except Exception as e:
            logger.error(f"  ⚠️ Error processing paper {paper.id}: {e}")
            continue
    
    # Calculate duration
    duration_seconds = time.time() - start_time
    duration_minutes = duration_seconds / 60
    
    # Get final queue lengths
    pending_len = await redis_client.client.xlen("papers:pending") if not dry_run else 0
    analyzed_len = await redis_client.client.xlen("papers:analyzed") if not dry_run else 0
    
    # Summary
    summary = {
        "fetched": fetched_count,
        "accepted": accepted_count,
        "rejected": rejected_count,
        "acceptance_rate": f"{100 * accepted_count / fetched_count:.1f}%" if fetched_count > 0 else "N/A",
        "duration_seconds": round(duration_seconds, 1),
        "duration_minutes": round(duration_minutes, 2),
        "papers_pending": pending_len,
        "papers_analyzed": analyzed_len,
        "dry_run": dry_run,
    }
    
    forensic.log_event("BACKFILL_COMPLETE", "INFO", details=summary)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 BACKFILL SUMMARY")
    print("=" * 60)
    print(f"  Fetched:         {summary['fetched']} papers")
    print(f"  Accepted:        {summary['accepted']} papers")
    print(f"  Rejected:        {summary['rejected']} papers")
    print(f"  Acceptance Rate: {summary['acceptance_rate']}")
    print(f"  Duration:        {summary['duration_minutes']} minutes")
    print(f"  Dry Run:         {summary['dry_run']}")
    if not dry_run:
        print(f"  Queue Pending:   {summary['papers_pending']}")
        print(f"  Queue Analyzed:  {summary['papers_analyzed']}")
    print("=" * 60 + "\n")
    
    await redis_client.close()
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="One-shot backfill for AI Safety Radar"
    )
    parser.add_argument(
        "--days-back", type=int, default=30,
        help="Number of days to look back (default: 30)"
    )
    parser.add_argument(
        "--max-results", type=int, default=100,
        help="Maximum papers to fetch (default: 100)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=20,
        help="Papers per batch before progress log (default: 20)"
    )
    parser.add_argument(
        "--sleep-seconds", type=float, default=1.0,
        help="Sleep between batches for rate limiting (default: 1.0)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run without publishing to Redis (test mode)"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Safe reset streams before backfill (deletes pending/analyzed)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Starting backfill: {args.days_back} days, {args.max_results} max papers")
    
    asyncio.run(run_backfill(
        days_back=args.days_back,
        max_results=args.max_results,
        batch_size=args.batch_size,
        sleep_seconds=args.sleep_seconds,
        dry_run=args.dry_run,
        reset=args.reset,
    ))


if __name__ == "__main__":
    main()
