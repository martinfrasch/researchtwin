"""Figshare API connector for dataset metadata."""

import asyncio

import httpx

import cache

FIGSHARE_API = "https://api.figshare.com/v2"
PAGE_SIZE = 50


def _author_matches(article_authors: list[dict], search_name: str) -> bool:
    """Check if any author in the article matches the search name.

    Uses fuzzy matching: splits search_name into first/last and checks if both
    appear in the author's full_name. Handles "Martin Frasch" matching
    "Martin G. Frasch" or "Martin Gerbert Frasch".
    """
    parts = search_name.lower().strip().split()
    if len(parts) < 2:
        return False
    first = parts[0]
    last = parts[-1]
    for author in article_authors:
        full_name = (author.get("full_name") or "").lower().strip()
        if first in full_name and last in full_name:
            return True
    return False


async def fetch_figshare_data(search_name: str) -> dict:
    """Search Figshare for articles by author name, with pagination and filtering."""
    cache_key = f"figshare:search:{search_name.lower().strip()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    articles = []
    total_views = 0
    total_downloads = 0

    async with httpx.AsyncClient(timeout=30) as client:
        page = 1
        while True:
            resp = await client.post(
                f"{FIGSHARE_API}/articles/search",
                json={"search_for": search_name, "page": page, "page_size": PAGE_SIZE},
            )
            resp.raise_for_status()
            page_results = resp.json()

            for item in page_results:
                article_id = item.get("id")
                try:
                    detail_resp = await client.get(f"{FIGSHARE_API}/articles/{article_id}")
                    detail_resp.raise_for_status()
                    raw = detail_resp.json()
                except Exception:
                    continue  # Skip articles that fail to fetch

                raw_authors = raw.get("authors") or []
                if not _author_matches(raw_authors, search_name):
                    continue

                views = raw.get("views", 0)
                downloads = raw.get("downloads", 0)
                total_views += views
                total_downloads += downloads

                authors = [a.get("full_name", "") for a in raw_authors]
                categories = [c.get("title", "") for c in (raw.get("categories") or [])]

                articles.append({
                    "id": article_id,
                    "title": raw.get("title", ""),
                    "doi": raw.get("doi", ""),
                    "description": (raw.get("description") or "")[:500],
                    "views": views,
                    "downloads": downloads,
                    "license": (raw.get("license") or {}).get("name", ""),
                    "authors": authors,
                    "categories": categories,
                    "defined_type_name": raw.get("defined_type_name", ""),
                    "created_date": raw.get("created_date", ""),
                    "url": raw.get("url_public_html", ""),
                    "files_count": len(raw.get("files") or []),
                })

                # Small delay to be polite to Figshare API
                await asyncio.sleep(0.05)

            if len(page_results) < PAGE_SIZE:
                break
            page += 1

    result = {
        "total_datasets": len(articles),
        "total_views": total_views,
        "total_downloads": total_downloads,
        "articles": articles,
    }

    if result["total_datasets"] > 0:
        cache.set(cache_key, result)

    return result
