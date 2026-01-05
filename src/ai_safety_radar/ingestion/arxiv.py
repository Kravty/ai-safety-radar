import asyncio
import httpx
import feedparser
import logging
from typing import AsyncIterator
from datetime import datetime, timedelta
from ..models.raw_document import RawDocument
from .base import BaseIngester
from ..config import settings

logger = logging.getLogger(__name__)

class ArXivIngester(BaseIngester):
    """Async scraper for ArXiv papers related to AI safety."""
    
    BASE_URL = "https://export.arxiv.org/api/query"
    
    SAFETY_KEYWORDS = [
        "adversarial",
        "jailbreak", 
        "alignment",
        "poisoning",
        "backdoor",
        "robustness",
        "prompt injection",
        "model extraction"
    ]
    
    async def fetch_recent(
        self,
        days_back: int = 30,
        max_results: int | None = None
    ) -> AsyncIterator[RawDocument]:
        """
        Fetch recent papers matching AI safety keywords.
        
        Args:
            days_back: Number of days to look back
            max_results: Max papers to return (None = unlimited)
            
        Yields:
            RawDocument instances for each relevant paper
            
        Raises:
            httpx.HTTPError: If API request fails
        """
        SECURITY_SEARCH_QUERIES = [
            # Adversarial ML
            'cat:cs.CR AND (adversarial OR attack OR robustness)',
            'cat:cs.LG AND (jailbreak OR "red team" OR "prompt injection")',
            
            # AI Safety & Alignment
            'cat:cs.AI AND (safety OR alignment OR "catastrophic risk")',
            'cat:cs.CY AND ("AI governance" OR "AI policy")',
            
            # Specific Attack Types
            'all:"backdoor attack" AND (neural OR deep OR model)',
            'all:"model extraction" OR all:"membership inference"',
            'all:"data poisoning" AND machine learning',
            
            # Defense Research
            'all:"adversarial training" OR all:"certified robustness"',
            'all:"AI safety" AND (technical OR research)',
            
            # Multi-modal Security
            'all:"vision-language model" AND (security OR adversarial)',
        ]
        
        # Combine all queries with OR (API allows boolean) - but max length might be issue.
        # Splitting logic would be better if volume requires, but let's try combined first or pick one/round-robin?
        # User implies we should expand coverage. Combined OR might hit API limits.
        # Let's iterate if possible or combine intelligently.
        # With httpx, we can only send one 'search_query'.
        # Let's join them with OR.
        query = " OR ".join([f"({q})" for q in SECURITY_SEARCH_QUERIES])
        
        start = 0
        batch_size = settings.arxiv_max_results
        total_fetched = 0
        
        limit = max_results if max_results else 1000 # Safety limit
        
        async with httpx.AsyncClient() as client:
            while total_fetched < limit:
                params: dict[str, str | int] = {
                    "search_query": query,
                    "start": start,
                    "max_results": batch_size,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }
                
                try:
                    logger.info(f"Fetching ArXiv batch starting at {start}")
                    response = await client.get(self.BASE_URL, params=params, timeout=settings.request_timeout)
                    response.raise_for_status()
                    
                    feed = feedparser.parse(response.text)
                    
                    if not feed.entries:
                        break
                        
                    for entry in feed.entries:
                        # Parse published date
                        published = datetime(*entry.published_parsed[:6])
                        
                        # Stop if older than days_back
                        if published < datetime.utcnow() - timedelta(days=days_back):
                            logger.info("Reached date limit, stopping ingestion.")
                            return
                            
                        # Extract PDF link
                        pdf_link = next((link.href for link in entry.links if link.type == 'application/pdf'), entry.link)
                        
                        doc = RawDocument(
                            id=entry.id.split('/')[-1], # ArXiv ID
                            title=entry.title,
                            url=pdf_link,
                            content=f"{entry.title}\n\nAbstract:\n{entry.summary}",
                            source="arxiv",
                            published_date=published,
                            metadata={
                                "authors": [a.name for a in entry.authors],
                                "categories": [t.term for t in entry.tags],
                                "comment": getattr(entry, "arxiv_comment", None)
                            }
                        )
                        
                        yield doc
                        total_fetched += 1
                        
                        if max_results and total_fetched >= max_results:
                            return
                            
                    start += len(feed.entries)
                    
                    # Rate limiting: 3 seconds
                    await asyncio.sleep(3)
                    
                except httpx.HTTPError as e:
                    logger.error(f"ArXiv API error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error during ingestion: {e}")
                    raise
