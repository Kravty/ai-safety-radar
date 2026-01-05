#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-time script to remove duplicate papers from papers:analyzed stream."""
import asyncio
import json
import redis.asyncio as redis

async def remove_duplicates():
    """Remove duplicate papers keeping only the first occurrence."""
    r = await redis.from_url("redis://localhost:6379/0")
    
    # Read all analyzed papers
    messages = await r.xrange("papers:analyzed", "-", "+")
    
    seen_ids = {}
    duplicates = []
    
    print(f"📊 Found {len(messages)} total messages in papers:analyzed")
    
    for msg_id, data in messages:
        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
        
        # Parse payload
        if b"data" in data:
            try:
                payload = json.loads(data[b"data"])
            except json.JSONDecodeError:
                payload = {k.decode(): v.decode() for k, v in data.items()}
        else:
            payload = {k.decode() if isinstance(k, bytes) else k: 
                      v.decode() if isinstance(v, bytes) else v 
                      for k, v in data.items()}
        
        # Get unique identifier (prefer id, fallback to title)
        paper_id = payload.get("id", payload.get("title", msg_id_str))
        
        if paper_id in seen_ids:
            duplicates.append(msg_id_str)
            print(f"  🔁 Duplicate: {msg_id_str} - {paper_id}")
        else:
            seen_ids[paper_id] = msg_id_str
            print(f"  ✅ Keep: {msg_id_str} - {paper_id}")
    
    # Remove duplicates
    if duplicates:
        print(f"\n⚠️ Found {len(duplicates)} duplicates. Removing...")
        for dup_id in duplicates:
            await r.xdel("papers:analyzed", dup_id)
        print(f"✅ Removed {len(duplicates)} duplicate entries")
    else:
        print("\n✅ No duplicates found")
    
    # Mark existing papers as processed to prevent re-ingestion
    print("\n📝 Marking existing papers as processed...")
    for paper_id in seen_ids.keys():
        key = f"processed:{paper_id}"
        await r.set(key, "1", ex=2592000)  # 30 days
    print(f"✅ Marked {len(seen_ids)} papers as processed")
    
    await r.aclose()

if __name__ == "__main__":
    asyncio.run(remove_duplicates())
