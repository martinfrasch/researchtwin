"""Semantic Scholar API connector."""

import asyncio

import httpx

import cache

S2_BASE = "https://api.semanticscholar.org/graph/v1"
# Minimal fields to stay within rate limits (no papers.authors to reduce payload)
AUTHOR_FIELDS = "name,paperCount,citationCount,hIndex"
PAPERS_FIELDS = "title,year,citationCount,url"


async def _fetch_with_retry(client: httpx.AsyncClient, url: str, params: dict, retries: int = 3) -> dict:
    """Fetch with retry on 429."""
    for attempt in range(retries):
        resp = await client.get(url, params=params)
        if resp.status_code == 429:
            wait = 3 * (attempt + 1)  # 3s, 6s, 9s
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    # All retries exhausted — return empty rather than crashing
    return {}


async def fetch_author_data(author_id: str) -> dict:
    """Fetch author profile and top papers from Semantic Scholar."""
    cache_key = f"s2:author:{author_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch author info
        author_url = f"{S2_BASE}/author/{author_id}"
        raw = await _fetch_with_retry(client, author_url, {"fields": AUTHOR_FIELDS})

        # Fetch papers separately (paginated, sorted by citation count)
        papers_url = f"{S2_BASE}/author/{author_id}/papers"
        papers_raw = await _fetch_with_retry(
            client, papers_url,
            {"fields": PAPERS_FIELDS, "limit": 50, "sort": "citationCount:desc"},
        )

    papers = papers_raw.get("data") or []
    top_papers = []
    for p in papers[:20]:
        top_papers.append({
            "title": p.get("title", ""),
            "year": p.get("year"),
            "citations": p.get("citationCount", 0),
            "url": p.get("url", ""),
        })

    result = {
        "name": raw.get("name", ""),
        "paper_count": raw.get("paperCount", 0),
        "citation_count": raw.get("citationCount", 0),
        "h_index": raw.get("hIndex", 0),
        "top_papers": top_papers,
    }

    # Only cache if we got real data (not empty from rate limit fallback)
    if result["paper_count"] > 0:
        cache.set(cache_key, result)

    return result
