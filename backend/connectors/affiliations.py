"""Fetch researcher affiliations from Semantic Scholar and ORCID."""

import asyncio
import unicodedata
from difflib import SequenceMatcher

import httpx

import cache

S2_BASE = "https://api.semanticscholar.org/graph/v1"
ORCID_BASE = "https://pub.orcid.org/v3.0"


async def _fetch_s2_affiliations(author_id: str) -> list[str]:
    """Get current affiliations from Semantic Scholar."""
    if not author_id:
        return []

    cache_key = f"s2:affiliations:{author_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{S2_BASE}/author/{author_id}",
                params={"fields": "affiliations"},
            )
            if resp.status_code == 429:
                await asyncio.sleep(3)
                resp = await client.get(
                    f"{S2_BASE}/author/{author_id}",
                    params={"fields": "affiliations"},
                )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    affiliations = data.get("affiliations") or []
    # S2 may return a single string or a list
    if isinstance(affiliations, str):
        affiliations = [affiliations] if affiliations else []

    cache.set(cache_key, affiliations, ttl=86400 * 7)  # 7-day cache
    return affiliations


async def _fetch_orcid_affiliations(orcid: str) -> list[dict]:
    """Get employment history from ORCID public API.

    Returns list of dicts with keys: institution, city, country, current.
    """
    if not orcid:
        return []

    cache_key = f"orcid:employments:{orcid}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{ORCID_BASE}/{orcid}/employments",
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    results = []
    seen_orgs = set()
    groups = data.get("affiliation-group", []) or []
    for group in groups:
        summaries = group.get("summaries", []) or []
        for item in summaries:
            summary = item.get("employment-summary", {})
            org = summary.get("organization", {})
            name = org.get("name", "")
            if not name:
                continue

            # Deduplicate within ORCID (same org, different periods)
            nfkd = unicodedata.normalize("NFKD", name)
            org_key = "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()
            if org_key in seen_orgs:
                continue
            seen_orgs.add(org_key)

            address = org.get("address", {}) or {}
            city = address.get("city", "")
            country = address.get("country", "")

            # Check if current (no end date)
            end_date = summary.get("end-date")
            is_current = end_date is None or end_date.get("year") is None

            results.append({
                "institution": name,
                "city": city,
                "country": country,
                "current": is_current,
            })

    cache.set(cache_key, results, ttl=86400 * 7)
    return results


async def fetch_affiliations(semantic_scholar_id: str, orcid: str) -> list[dict]:
    """Fetch and merge affiliations from all available sources.

    Returns list of dicts: {institution, city, country, current, source}.
    Deduplicates by institution name (case-insensitive).
    """
    s2_task = _fetch_s2_affiliations(semantic_scholar_id)
    orcid_task = _fetch_orcid_affiliations(orcid)
    s2_affs, orcid_affs = await asyncio.gather(s2_task, orcid_task)

    results = []

    def _normalize_name(name: str) -> str:
        """Normalize for dedup: strip accents, lowercase, collapse whitespace."""
        nfkd = unicodedata.normalize("NFKD", name)
        ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
        return " ".join(ascii_str.lower().split())

    def _is_duplicate(name: str, existing: list[dict]) -> bool:
        """Check if name is similar to any existing affiliation."""
        norm = _normalize_name(name)
        for aff in existing:
            existing_norm = _normalize_name(aff["institution"])
            if norm == existing_norm:
                return True
            # Similarity check for cross-language variants (e.g. Universite vs University)
            if SequenceMatcher(None, norm, existing_norm).ratio() > 0.8:
                return True
        return False

    # ORCID is richer (has city/country), so add it first
    for aff in orcid_affs:
        if not _is_duplicate(aff["institution"], results):
            results.append({**aff, "source": "orcid"})

    # Add S2 affiliations not already covered by ORCID
    for name in s2_affs:
        if not _is_duplicate(name, results):
            results.append({
                "institution": name,
                "city": "",
                "country": "",
                "current": True,  # S2 only returns current
                "source": "semantic_scholar",
            })

    return results
