import pandas as pd
from datasets import load_dataset, Dataset
import logging
from typing import List
from datetime import datetime, timedelta
from ..models.threat_signature import ThreatSignature
from ..config import settings

logger = logging.getLogger(__name__)

class DatasetManager:
    """Manages persistence of ThreatSignatures to Hugging Face Datasets."""
    
    def __init__(self) -> None:
        self.dataset_name = settings.hf_dataset_name
        self.token = settings.hf_token
        
    def _get_dataset(self) -> pd.DataFrame:
        """Load current dataset as DataFrame or create empty."""
        try:
            # Try loading from HF
            ds = load_dataset(self.dataset_name, split="train")
            return ds.to_pandas()
        except Exception as e:
            logger.warning(f"Could not load dataset {self.dataset_name}: {e}. Starting fresh.")
            # return empty df with correct columns
            # We can infer columns from model schema
            return pd.DataFrame(columns=ThreatSignature.model_json_schema()['properties'].keys())

    def save_threats(self, threats: List[ThreatSignature]) -> int:
        """
        Append new threats, deduplicate, and push to HF.
        Returns number of new threats added.
        """
        if not threats:
            return 0
            
        new_df = pd.DataFrame([t.model_dump() for t in threats])
        
        current_df = self._get_dataset()
        
        # Deduplication logic
        # Semantic ID: Title + Published Date? Or just URL?
        # URL is safest for strict dedupe. Title can change slightly.
        # But arXiv versions exist. 
        # Let's use URL as primary key for now.
        

        
        if not current_df.empty:
            # Exclude rows where URL already exists in current_df
            existing_urls = set(current_df['url'])
            new_df = new_df[~new_df['url'].isin(existing_urls)]
            
        added_count = len(new_df)
        
        if added_count > 0:
            final_df = pd.concat([current_df, new_df], ignore_index=True)
            
            # Convert Date objects to string for Parquet compatibility if needed, 
            # but HF Datasets handles datetime objects usually. 
            # Pydantic exports datetime. DataFrame usually keeps it.
            
            # Convert back to HF Dataset
            ds = Dataset.from_pandas(final_df)
            
            # Push to hub
            if self.token:
                try:
                    ds.push_to_hub(self.dataset_name, token=self.token)
                    logger.info(f"Pushed {added_count} new threats to {self.dataset_name}")
                except Exception as e:
                    logger.error(f"Failed to push to hub: {e}")
                    # Local fallback?
            else:
                logger.warning("No HF_TOKEN provided. distinct saving skipped (Simulated).")
                
        return added_count

    def fetch_recent_threats(self, days: int = 1) -> List[ThreatSignature]:
        """Fetch threats published in the last N days."""
        df = self._get_dataset()
        if df.empty:
            return []
            
        # Ensure published_date is datetime
        if not pd.api.types.is_datetime64_any_dtype(df['published_date']):
             df['published_date'] = pd.to_datetime(df['published_date'])
             
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_df = df[df['published_date'] >= cutoff]
        
        threats = []
        for _, row in recent_df.iterrows():
            # Convert row back to dict then ThreatSignature
            # Handle potential NaN or type mismatches
            data = row.to_dict()
            # Pydantic wants string or datetime. Pandas Timestamp is fine usually.
            try:
                threats.append(ThreatSignature(**data))
            except Exception as e:
                logger.error(f"Error parsing row to ThreatSignature: {e}")
                
        return threats
