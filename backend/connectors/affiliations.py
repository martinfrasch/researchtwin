"""Fetch researcher affiliations from Semantic Scholar, ORCID, and OpenAlex."""

import asyncio
import re
import unicodedata
from difflib import SequenceMatcher

import httpx

import cache

S2_BASE = "https://api.semanticscholar.org/graph/v1"
ORCID_BASE = "https://pub.orcid.org/v3.0"
OPENALEX_BASE = "https://api.openalex.org"

# OpenAlex infers affiliations from paper metadata, so a single mislabeled or
# co-authored paper attributes spurious institutions (e.g. "Apple", "Total") to a
# researcher. Require sustained multi-year paper support to treat an OpenAlex
# affiliation as real. ORCID (self-reported) and S2 are trusted without this gate.
MIN_OPENALEX_YEARS = 3


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


async def _fetch_openalex_affiliations(orcid: str) -> list[dict]:
    """Get affiliations from OpenAlex (uses ORCID as author identifier).

    Returns list of dicts with keys: institution, city, country, current.
    OpenAlex infers affiliations from paper metadata, so coverage is
    excellent even when researchers haven't self-reported.
    """
    if not orcid:
        return []

    cache_key = f"openalex:affiliations:{orcid}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{OPENALEX_BASE}/authors/orcid:{orcid}",
                params={"select": "affiliations,last_known_institutions"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
    except Exception:
        return []

    import datetime
    current_year = datetime.date.today().year

    # Build the set of institutions with sustained multi-year paper support. Entries
    # backed by fewer than MIN_OPENALEX_YEARS distinct years are almost always
    # disambiguation noise (a single co-authored or mislabeled paper) and are dropped.
    strong = {}  # norm_key -> affiliation dict
    for aff in data.get("affiliations") or []:
        inst = aff.get("institution", {})
        name = inst.get("display_name", "")
        if not name:
            continue
        years = aff.get("years") or []
        if len(years) < MIN_OPENALEX_YEARS:
            continue
        norm_key = _normalize_name(name)
        if norm_key in strong:
            continue
        strong[norm_key] = {
            "institution": name,
            "city": "",
            "country": inst.get("country_code", ""),
            "current": current_year in years or (current_year - 1) in years,
        }

    results = []
    seen_orgs = set()

    # last_known_institutions = OpenAlex's computed "current", but this list is itself
    # noisy (journals, one-off orgs), so only trust it when corroborated by strong
    # multi-year support. Mark those as current.
    for inst in data.get("last_known_institutions") or []:
        name = inst.get("display_name", "")
        if not name:
            continue
        norm_key = _normalize_name(name)
        if norm_key not in strong or norm_key in seen_orgs:
            continue
        seen_orgs.add(norm_key)
        entry = dict(strong[norm_key])
        entry["current"] = True
        results.append(entry)

    # Remaining strong affiliations (historical or current by year).
    for norm_key, entry in strong.items():
        if norm_key in seen_orgs:
            continue
        seen_orgs.add(norm_key)
        results.append(entry)

    cache.set(cache_key, results, ttl=86400 * 7)
    return results


def _normalize_name(name: str) -> str:
    """Normalize for dedup: strip accents, lowercase, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return " ".join(ascii_str.lower().split())


# Generic organizational words (EN/FR/DE, accent-stripped) that carry no identifying
# information. Removing them leaves the distinctive tokens (usually a place or person
# name) so variant spellings of the same institution can be matched.
_ORG_STOPWORDS = {
    "university", "universite", "universitat", "universidad", "universita", "college",
    "institute", "institut", "institution", "hospital", "hopital", "krankenhaus",
    "klinik", "klinikum", "clinic", "center", "centre", "zentrum", "school", "faculty",
    "department", "dept", "laboratory", "lab", "research", "recherche", "forschung",
    "medical", "medicine", "health", "sante", "sciences", "science", "national",
    "international", "of", "the", "and", "for", "de", "du", "des", "la", "le", "les",
    "el", "und", "fur", "pour", "et", "au", "aux", "chu", "chru", "system", "group",
    "hospitalier", "universitaire", "hochschule", "foundation", "fondation", "trust",
}


def _significant_tokens(name: str) -> set:
    """Distinctive tokens of an institution name, minus generic org words."""
    toks = re.split(r"[^a-z0-9]+", _normalize_name(name))
    return {t for t in toks if len(t) > 1 and t not in _ORG_STOPWORDS}


def _is_duplicate(name: str, existing: list[dict]) -> bool:
    """Check if name is similar to any existing affiliation."""
    norm = _normalize_name(name)
    sig = _significant_tokens(name)
    for aff in existing:
        existing_norm = _normalize_name(aff["institution"])
        if norm == existing_norm:
            return True
        # Similarity check for cross-language variants
        if SequenceMatcher(None, norm, existing_norm).ratio() > 0.8:
            return True
        # Same distinctive tokens (ignoring generic org words) → same institution under
        # a different name form, e.g. "Centre de recherche du CHU Sainte-Justine" vs
        # "Centre Hospitalier Universitaire Sainte-Justine". Require ≥2 shared tokens so
        # single-token collisions ("University of Washington" vs "Washington University")
        # are NOT merged.
        if len(sig) >= 2 and sig == _significant_tokens(aff["institution"]):
            return True
    return False


async def fetch_affiliations(semantic_scholar_id: str, orcid: str) -> list[dict]:
    """Fetch and merge affiliations from all available sources.

    Returns list of dicts: {institution, city, country, current, source}.
    Deduplicates by institution name (case-insensitive).
    """
    s2_task = _fetch_s2_affiliations(semantic_scholar_id)
    orcid_task = _fetch_orcid_affiliations(orcid)
    openalex_task = _fetch_openalex_affiliations(orcid)
    s2_affs, orcid_affs, openalex_affs = await asyncio.gather(
        s2_task, orcid_task, openalex_task,
    )

    results = []

    # ORCID is richest (has city/country from self-report), add first
    for aff in orcid_affs:
        if not _is_duplicate(aff["institution"], results):
            results.append({**aff, "source": "orcid"})

    # OpenAlex next (inferred from papers, good coverage)
    for aff in openalex_affs:
        if not _is_duplicate(aff["institution"], results):
            results.append({**aff, "source": "openalex"})

    # S2 last (current only, no city/country)
    for name in s2_affs:
        if not _is_duplicate(name, results):
            results.append({
                "institution": name,
                "city": "",
                "country": "",
                "current": True,
                "source": "semantic_scholar",
            })

    return results
