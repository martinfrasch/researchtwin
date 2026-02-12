"""Google Scholar connector via the scholarly library."""

import asyncio
import logging

import cache

logger = logging.getLogger(__name__)

GS_CACHE_TTL = 172800  # 48 hours — GS data changes slowly

_scholarly_initialized = False


def _init_scholarly():
    """Initialize scholarly. Called once per process."""
    global _scholarly_initialized
    if _scholarly_initialized:
        return
    try:
        from scholarly import scholarly, ProxyGenerator
        try:
            pg = ProxyGenerator()
            pg.FreeProxies()
            scholarly.use_proxy(pg)
            logger.info("scholarly initialized with FreeProxies")
        except Exception as proxy_err:
            logger.warning(f"FreeProxies setup failed ({proxy_err}), using scholarly without proxy")
    except Exception as e:
        logger.warning(f"scholarly init failed: {e}")
    _scholarly_initialized = True


def _fetch_scholar_sync(scholar_id: str) -> dict:
    """Synchronous scholarly calls. Runs in thread executor."""
    from scholarly import scholarly

    _init_scholarly()

    author = scholarly.search_author_id(scholar_id)
    author = scholarly.fill(author, sections=["indices", "publications"])

    publications = []
    for pub in author.get("publications", []):
        bib = pub.get("bib", {})
        title = bib.get("title", "")
        year_raw = bib.get("pub_year", "")
        try:
            year = int(year_raw) if year_raw else None
        except (ValueError, TypeError):
            year = None

        publications.append({
            "title": title,
            "year": year,
            "citations": pub.get("num_citations", 0),
            "source": "google_scholar",
        })

    publications.sort(key=lambda p: p["citations"], reverse=True)

    return {
        "name": author.get("name", ""),
        "scholar_id": scholar_id,
        "citation_count": author.get("citedby", 0) or 0,
        "h_index": author.get("hindex", 0) or 0,
        "i10_index": author.get("i10index", 0) or 0,
        "paper_count": len(publications),
        "publications": publications,
    }


async def fetch_scholar_data(scholar_id: str) -> dict:
    """Fetch author profile and publications from Google Scholar.

    Uses scholarly (synchronous) wrapped in run_in_executor.
    Aggressively cached at 48h since GS data changes slowly.
    """
    cache_key = f"gs:author:{scholar_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _fetch_scholar_sync, scholar_id)

    if result["paper_count"] > 0:
        cache.set(cache_key, result, ttl=GS_CACHE_TTL)

    return result
