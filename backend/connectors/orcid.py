"""ORCID API connector — resolve ORCID to Semantic Scholar author ID."""

import asyncio
import logging
from collections import Counter
import httpx

logger = logging.getLogger("researchtwin")

ORCID_BASE = "https://pub.orcid.org/v3.0"
S2_BASE = "https://api.semanticscholar.org/graph/v1"

# How many ORCID works (DOIs) to try before giving up
_MAX_DOIS = 8


def _split_name(name: str) -> tuple[list[str], str]:
    """Split into (given-name tokens, surname).  Last token = surname."""
    import re
    parts = re.sub(r"[.\-,]", " ", name.lower()).split()
    parts = [p for p in parts if p]
    if len(parts) < 2:
        return parts, parts[0] if parts else ""
    return parts[:-1], parts[-1]


def _name_matches(display_name: str, author_name: str) -> bool:
    """Check if two researcher names refer to the same person.

    Handles abbreviated forms common in Semantic Scholar:
      "Gerlinde Metz" vs "G. Metz"
      "Martin Frasch" vs "M. H. Frasch"
      "Gerlinde A. S. Metz" vs "Gerlinde Metz"
    """
    given_a, surname_a = _split_name(display_name)
    given_b, surname_b = _split_name(author_name)

    # Surnames must match
    if surname_a != surname_b:
        return False

    # If either has no given names, surname match is enough
    if not given_a or not given_b:
        return True

    # Check if any given-name token from one side matches (or is an
    # initial of) a given-name token on the other side.
    def _initial_match(tokens_a: list[str], tokens_b: list[str]) -> bool:
        for ta in tokens_a:
            for tb in tokens_b:
                if ta == tb:
                    return True
                if len(ta) == 1 and tb.startswith(ta):
                    return True
                if len(tb) == 1 and ta.startswith(tb):
                    return True
        return False

    return _initial_match(given_a, given_b)


async def _get_dois_from_orcid(orcid: str) -> list[str]:
    """Fetch DOIs from an ORCID profile's works."""
    url = f"{ORCID_BASE}/{orcid}/works"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers={"Accept": "application/json"})
        resp.raise_for_status()
        data = resp.json()

    dois: list[str] = []
    for group in data.get("group", []):
        summary = group.get("work-summary", [{}])[0]
        for ext_id in summary.get("external-ids", {}).get("external-id", []):
            if ext_id.get("external-id-type") == "doi":
                dois.append(ext_id["external-id-value"])
                break
        if len(dois) >= _MAX_DOIS:
            break
    return dois


async def _s2_authors_for_doi(client: httpx.AsyncClient, doi: str) -> list[dict]:
    """Look up a paper on S2 by DOI and return its author list."""
    url = f"{S2_BASE}/paper/DOI:{doi}"
    try:
        resp = await client.get(url, params={"fields": "authors"})
        if resp.status_code == 429:
            await asyncio.sleep(3)
            resp = await client.get(url, params={"fields": "authors"})
        if resp.status_code != 200:
            return []
        return resp.json().get("authors", [])
    except Exception:
        return []


async def resolve_s2_id(orcid: str, display_name: str) -> str | None:
    """Resolve an ORCID to the most likely Semantic Scholar author ID.

    Strategy: fetch DOIs from ORCID, look each up on S2, find the author
    whose name matches *display_name*, and return the most-frequent S2 ID
    (handles S2 profile fragmentation by picking the majority).
    """
    try:
        dois = await _get_dois_from_orcid(orcid)
    except Exception:
        logger.warning("ORCID lookup failed for %s", orcid)
        return None

    if not dois:
        logger.info("No DOIs found in ORCID %s", orcid)
        return None

    id_counts: Counter[str] = Counter()

    async with httpx.AsyncClient(timeout=15) as client:
        for doi in dois:
            authors = await _s2_authors_for_doi(client, doi)
            for author in authors:
                name = author.get("name", "")
                author_id = author.get("authorId")
                if not author_id:
                    continue
                if _name_matches(display_name, name):
                    id_counts[author_id] += 1

    if not id_counts:
        logger.info("No S2 author matched name '%s' via ORCID %s", display_name, orcid)
        return None

    # Collect all candidate IDs: those from DOI lookups + any from S2 name search
    # (handles fragmented profiles where older papers are under a different ID).
    candidates = set(id_counts.keys())
    extra = await _s2_name_search_ids(display_name)
    candidates.update(extra)

    best_id = await _pick_largest_profile(list(candidates))
    logger.info("ORCID %s → S2 author ID %s (from %d candidates)", orcid, best_id, len(candidates))
    return best_id


async def _s2_name_search_ids(display_name: str) -> list[str]:
    """Search S2 by name and return author IDs that match."""
    url = f"{S2_BASE}/author/search"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params={"query": display_name, "fields": "name"})
            if resp.status_code != 200:
                return []
            results = resp.json().get("data", [])
            return [
                r["authorId"] for r in results
                if _name_matches(display_name, r.get("name", ""))
            ]
    except Exception:
        return []


async def _pick_largest_profile(author_ids: list[str]) -> str:
    """Given candidate S2 author IDs, return the one with the most papers."""
    best_id, best_count = author_ids[0], 0
    async with httpx.AsyncClient(timeout=15) as client:
        for aid in author_ids:
            try:
                resp = await client.get(
                    f"{S2_BASE}/author/{aid}", params={"fields": "paperCount"},
                )
                if resp.status_code == 200:
                    count = resp.json().get("paperCount", 0)
                    if count > best_count:
                        best_id, best_count = aid, count
            except Exception:
                continue
    return best_id
