from abc import ABC, abstractmethod
from typing import AsyncIterator
from ..models.raw_document import RawDocument

class BaseIngester(ABC):
    """Abstract base class for all ingestion sources."""
    
    @abstractmethod
    def fetch_recent(
        self,
        days_back: int = 7,
        max_results: int | None = None
    ) -> AsyncIterator[RawDocument]:
        """
        Fetch recent documents from the source.
        
        Args:
            days_back: Number of days to look back
            max_results: Max documents to return
            
        Yields:
            RawDocument objects
        """
        pass
