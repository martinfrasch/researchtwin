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


async def geocode(query: str, countrycode: str = "") -> dict | None:
    """Geocode an institution name or location string.

    countrycode: optional ISO 3166-1 alpha-2 code (e.g. "de", "ca") passed to
    Nominatim's countrycodes filter to disambiguate results — far more reliable
    than putting a bare country code in the free-text query.

    Returns {"lat": float, "lng": float, "display_name": str} or None.
    """
    if not query or len(query) < 3:
        return None

    cache_key = f"geocode:{query.lower().strip()}|cc={countrycode}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached if cached != "__none__" else None

    async with _nominatim_lock:
        try:
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 0,
            }
            if countrycode:
                params["countrycodes"] = countrycode
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    NOMINATIM_URL,
                    params=params,
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

    Tries institution + city (country applied as a Nominatim filter) first, then
    falls back to institution alone.
    """
    institution = affiliation.get("institution", "")
    city = affiliation.get("city", "")
    country = affiliation.get("country", "")

    # Country is usually an ISO 3166-1 alpha-2 code (e.g. "DE", "CA"). A bare code in
    # the query text confuses Nominatim, so use it as the countrycodes filter and keep
    # only real place names (city, or a full country name) in the query string.
    is_code = len(country) == 2 and country.isalpha()
    countrycode = country.lower() if is_code else ""
    country_text = "" if is_code else country

    parts = [p for p in [institution, city, country_text] if p]
    full_query = ", ".join(parts)
    result = await geocode(full_query, countrycode=countrycode)
    if result:
        return result

    # Fallback 1: institution name alone (still country-filtered when we have a code).
    if city or country_text:
        result = await geocode(institution, countrycode=countrycode)
        if result:
            return result

    # Fallback 2: city-level (approximate). Many hospitals/research institutes aren't
    # named features in Nominatim, but their city is — placing the pin in the right city
    # beats dropping the affiliation entirely.
    if city:
        return await geocode(city, countrycode=countrycode)

    return None
