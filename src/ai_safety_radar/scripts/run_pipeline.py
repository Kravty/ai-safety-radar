import asyncio
import logging
from dotenv import load_dotenv

from ai_safety_radar.ingestion.arxiv import ArXivIngester
from ai_safety_radar.orchestration.ingestion_graph import IngestionGraph
from ai_safety_radar.orchestration.editorial_graph import EditorialGraph
from ai_safety_radar.persistence.dataset_manager import DatasetManager
from ai_safety_radar.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_pipeline() -> None:
    load_dotenv()
    
    logger.info("Starting AI Safety Radar Pipeline")
    
    # 1. Ingestion Phase
    logger.info("Phase 1: Ingestion Scan")
    arxiv_ingester = ArXivIngester()
    ingestion_graph = IngestionGraph()
    dataset_manager = DatasetManager()
    
    # Fetch recent papers
    async for doc in arxiv_ingester.fetch_recent(days_back=1, max_results=settings.arxiv_max_results):
        logger.info(f"Processing: {doc.title}")
        try:
             await ingestion_graph.run(doc)
        except Exception as e:
            logger.error(f"Failed to process {doc.id}: {e}")
            
    # 2. Editorial Phase
    logger.info("Phase 2: Editorial Review")
    editorial_graph = EditorialGraph()
    
    # Fetch today's threats
    new_threats = dataset_manager.fetch_recent_threats(days=1)
    
    if new_threats:
        logger.info(f"Found {len(new_threats)} recent threats for briefing")
        
        # Get yesterday's summary (Mock for now, or fetch from file/dataset metadata)
        previous_summary = "Yesterday saw a rise in prompt injection attacks against multimodal models."
        
        briefing = await editorial_graph.run(new_threats, previous_summary=previous_summary)
        
        if briefing:
            logger.info("Daily Briefing Generated:")
            print("\n" + "="*50)
            print(f"HEADLINE: {briefing.headline}")
            print("="*50)
            print(briefing.summary_markdown)
            print("="*50)
            
            # TODO: Save briefing to file/dashboard
            
    else:
        logger.info("No new threats found in the last 24h. Skipping editorial.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
