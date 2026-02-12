"""Geocode institution names to lat/lng using Nominatim (OpenStreetMap).

Nominatim usage policy: max 1 request/second, valid User-Agent.
We cache results for 30 days since institutions don't move.
"""

import asyncio

import httpx

import cache

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ResearchTwin/0.3 (https://researchtwin.net; martin@researchtwin.net)"
CACHE_TTL = 86400 * 30  # 30 days

# Semaphore to enforce 1 request/second to Nominatim
_nominatim_lock = asyncio.Lock()


async def geocode(query: str) -> dict | None:
    """Geocode an institution name or location string.

    Returns {"lat": float, "lng": float, "display_name": str} or None.
    """
    if not query or len(query) < 3:
        return None

    cache_key = f"geocode:{query.lower().strip()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached if cached != "__none__" else None

    async with _nominatim_lock:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 0,
                    },
                    headers={"User-Agent": USER_AGENT},
                )
                resp.raise_for_status()
                results = resp.json()
        except Exception:
            return None

        # Rate limit compliance: wait 1 second between requests
        await asyncio.sleep(1.1)

    if not results:
        cache.set(cache_key, "__none__", ttl=CACHE_TTL)
        return None

    hit = results[0]
    result = {
        "lat": float(hit["lat"]),
        "lng": float(hit["lon"]),
        "display_name": hit.get("display_name", query),
    }
    cache.set(cache_key, result, ttl=CACHE_TTL)
    return result


async def geocode_affiliation(affiliation: dict) -> dict | None:
    """Geocode an affiliation dict (from affiliations.py).

    Tries institution + city + country first, falls back to institution alone.
    """
    parts = [affiliation.get("institution", "")]
    if affiliation.get("city"):
        parts.append(affiliation["city"])
    if affiliation.get("country"):
        parts.append(affiliation["country"])

    full_query = ", ".join(p for p in parts if p)
    result = await geocode(full_query)
    if result:
        return result

    # Fallback: just the institution name
    if len(parts) > 1:
        return await geocode(affiliation["institution"])

    return None
