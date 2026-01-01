import asyncio
import os
import re
import redis
import logging
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("readme_updater")

def get_redis_client():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    return redis.from_url(redis_url, decode_responses=True)

def fetch_latest_threats(client, count=5):
    # This is a bit inefficient without indexing, but for demo stream size it's fine.
    # Ideally we'd have a separate sorted set for stats or distinct list.
    try:
        items = client.xrevrange("papers:analyzed", max="+", min="-", count=50) # Look at last 50
        threats = []
        for msg_id, data in items:
            if 'data' in data:
                import json
                payload = json.loads(data['data'])
            else:
                 payload = data
            
            if payload.get('severity') in ['High', 'Critical']:
                threats.append(payload)
                if len(threats) >= count:
                    break
        return threats
    except Exception as e:
        logger.error(f"Error fetching threats: {e}")
        return []

def format_threat_table(threats: List[Dict[str, Any]]) -> str:
    if not threats:
        return "_No high-severity threats detected recently._"
        
    md = "| Threat | Severity | Vector | Date |\n|---|---|---|---|\n"
    for t in threats:
        # Sanitize
        title = t.get('title', 'Unknown').replace('|', '-')
        sev = t.get('severity', 'Unknown')
        vec = t.get('attack_vector', 'Unknown').replace('|', '-')
        date = t.get('published_date', 'Unknown')
        
        md += f"| {title} | **{sev}** | {vec} | {date} |\n"
    return md

def update_readme_content(content: str, marker_name: str, new_text: str) -> str:
    # Regex find <!-- AUTO_UPDATE:marker_name:START --> ... <!-- AUTO_UPDATE:marker_name:END -->
    pattern = re.compile(
        f"(<!-- AUTO_UPDATE:{marker_name}:START -->)(.*?)(<!-- AUTO_UPDATE:{marker_name}:END -->)", 
        re.DOTALL
    )
    
    if pattern.search(content):
        return pattern.sub(f"\\1\n{new_text}\n\\3", content)
    else:
        logger.warning(f"Marker {marker_name} not found in README.")
        return content

def main():
    logger.info("Starting README automation...")
    
    try:
        r = get_redis_client()
        r.ping()
    except Exception as e:
        logger.error(f"Cannot connect to Redis: {e}")
        return

    # 1. Fetch Stats
    # redis-cli XLEN papers:analyzed
    total_analyzed = r.xlen("papers:analyzed")
    pending = r.xlen("papers:pending")
    
    # 2. Fetch Threats
    threats = fetch_latest_threats(r)
    threat_table = format_threat_table(threats)
    
    # 3. Read README
    readme_path = "README.md" # Assumes running from root or we find it
    if not os.path.exists(readme_path):
         # Try parent dir if running from scripts
         readme_path = "../../../README.md"
         
    if not os.path.exists(readme_path):
        logger.error("README.md not found.")
        return
        
    with open(readme_path, 'r') as f:
        content = f.read()
        
    # 4. Update Sections
    
    # Statistics
    stats_md = f"""
- **Papers Analyzed**: {total_analyzed}
- **Pending Queue**: {pending}
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    # Need datetime import
    from datetime import datetime
    stats_md = f"""
- **Papers Analyzed**: {total_analyzed}
- **Pending Queue**: {pending}
- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
    content = update_readme_content(content, "STATS", stats_md)
    content = update_readme_content(content, "RECENT_THREATS", threat_table)
    
    # 5. Write back
    with open(readme_path, 'w') as f:
        f.write(content)
        
    logger.info("README.md updated successfully.")

if __name__ == "__main__":
    main()
