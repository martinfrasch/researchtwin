"""S-Index v2 calculator following the framework from github.com/martinfrasch/s-index.

Per-Object Score:  s_j = Q_j × I_j × C_j

  Quality:       Q_j = 5 · p_j · ℓ_j · (1 + 0.5·b_DOI + 0.3·b_doc + 0.2·b_fmt)
  Impact:        I_j = 1 + ln(1 + r_j / μ_t)
  Collaboration: C_j = √(N_a · N_i)

Researcher:      S_i = P + Σ s_j
                 P   = h · (1 + log₁₀(c + 1))
"""

import math
import re

from connectors.figshare import normalize_item as normalize_figshare_item
from connectors.github_connector import normalize_item as normalize_github_item

# Field medians for impact normalization (v2.0 deployment baselines)
FIELD_MEDIANS = {"dataset": 50, "code": 10}

# Figshare defined_type_names that represent independent research artifacts.
# Excludes figures, posters, presentations, media — those are paper components.
_ARTIFACT_TYPES = {"dataset", "software", "code", "fileset"}

# Regex patterns for extracting parent work from Figshare figure/supplement titles.
_PARENT_RE = re.compile(
    r"^(?:FIGURE\s*\d+|Figure\s+S\d+|Additional\s+file\s+\d+|"
    r"Supplementary\s+(?:file|data|table|figure)\s*\d*|Table\s+S?\d+)"
    r"\s*(?:from|of)\s+(.+)",
    re.IGNORECASE,
)


def _quality_score(item: dict) -> dict:
    """Compute Quality score using the FAIR gate model.

    Gate: public AND licensed → base = 5, else 0.
    Bonuses: DOI (+0.5), documentation (+0.3), standard format (+0.2).
    Q ∈ {0} ∪ [5, 10]
    """
    is_public = item.get("is_public", True)
    has_license = bool(item.get("license"))

    # FAIR gate: both required for any score
    gate = 1 if (is_public and has_license) else 0
    base = 5 * gate

    b_doi = 0.5 if item.get("has_doi") else 0
    b_doc = 0.3 if item.get("has_readme") else 0
    b_fmt = 0.2 if item.get("is_standard_format") else 0

    bonuses = b_doi + b_doc + b_fmt
    q = base * (1 + bonuses)

    return {"fair_gate": bool(gate), "bonuses": round(bonuses, 1), "Q": round(q, 2)}


def _impact_score(reuse_events: int, field_type: str = "code") -> float:
    """I = 1 + ln(1 + r / μ), field-normalized by median."""
    mu = FIELD_MEDIANS.get(field_type, 10)
    r = max(reuse_events, 0)
    return 1.0 + math.log(1 + (r / mu))


def _collaboration_score(n_authors: int, n_institutions: int = 1) -> float:
    """C = √(N_a × N_i), geometric mean of team breadth."""
    n_a = max(n_authors, 1)
    n_i = max(n_institutions, 1)
    return math.sqrt(n_a * n_i)


def score_item(item: dict) -> dict:
    """Score a normalized item (dataset or code artifact).

    Accepts the normalized schema:
        title, source_type, is_public, license, has_doi, has_readme,
        is_standard_format, reuse_events, n_authors, n_institutions
    """
    quality = _quality_score(item)
    impact = _impact_score(item.get("reuse_events", 0), item.get("source_type", "code"))
    collab = _collaboration_score(
        item.get("n_authors", 1), item.get("n_institutions", 1)
    )

    s = quality["Q"] * impact * collab
    return {
        "title": item.get("title", ""),
        "quality": quality["Q"],
        "fair_gate": quality["fair_gate"],
        "impact": round(impact, 3),
        "collaboration": round(collab, 3),
        "score": round(s, 3),
    }


def score_figshare_article(article: dict) -> dict:
    """Compute S-Index v2 score for a single Figshare article."""
    return score_item(normalize_figshare_item(article))


def score_github_repo(repo: dict) -> dict:
    """Compute S-Index v2 score for a single GitHub repo."""
    return score_item(normalize_github_item(repo))


def _deduplicate_figshare(articles: list[dict]) -> list[dict]:
    """Deduplicate Figshare articles so each parent work is scored once.

    Many Figshare "articles" are individual figures or supplementary files
    from the same paper. Scoring each separately inflates the S-Index.

    Strategy:
      1. Filter to genuine artifact types (datasets, software, filesets).
      2. Group remaining items by parent work (title heuristics).
      3. Keep the highest-scoring representative from each group.
    """
    # Phase 1: separate standalone artifacts from paper components
    standalone = []
    components = []  # (group_key, article)

    for art in articles:
        dtype = (art.get("defined_type_name") or "").lower()
        title = art.get("title", "")

        # Check if it's a figure/supplement via title pattern
        m = _PARENT_RE.match(title)
        if m:
            parent = m.group(1).strip()[:80].lower()
            components.append((parent, art))
            continue

        # Check if it's a non-artifact type (figure, poster, presentation, media)
        if dtype and dtype not in _ARTIFACT_TYPES and dtype in (
            "figure", "poster", "presentation", "media",
        ):
            # Group by author fingerprint: figures from the same paper share
            # identical author lists, even when titles differ.
            authors = art.get("authors", []) or []
            if isinstance(authors, list) and authors:
                if isinstance(authors[0], str):
                    author_key = "|".join(sorted(a.lower() for a in authors))
                else:
                    author_key = "|".join(sorted(
                        (a.get("full_name", "") or "").lower() for a in authors
                    ))
            else:
                author_key = title[:80].lower()
            group_key = f"authors:{author_key}"
            components.append((group_key, art))
            continue

        standalone.append(art)

    # Phase 2: group standalone items by similar titles (catch duplicates)
    groups: dict[str, list[dict]] = {}
    for art in standalone:
        title_key = art.get("title", "")[:80].lower().strip()
        groups.setdefault(title_key, []).append(art)

    # Add components grouped by their group key (parent title or author fingerprint)
    for group_key, art in components:
        groups.setdefault(group_key, []).append(art)

    # Phase 3: from each group, pick the item with highest reuse events
    deduped = []
    for group_items in groups.values():
        best = max(group_items, key=lambda a: (
            (a.get("downloads", 0) or 0) + (a.get("views", 0) or 0)
        ))
        deduped.append(best)

    return deduped


def compute_researcher_qic(
    figshare_data: dict,
    github_data: dict,
    semantic_scholar_data: dict,
) -> dict:
    """Compute S-Index v2 for a researcher across all artifacts.

    S_i = P + Σ s_j    where P = h × (1 + log₁₀(c + 1))
    """
    deduped_articles = _deduplicate_figshare(figshare_data.get("articles", []))
    dataset_scores = []
    for article in deduped_articles:
        dataset_scores.append(score_figshare_article(article))

    repo_scores = []
    for repo in github_data.get("top_repos", [])[:10]:
        repo_scores.append(score_github_repo(repo))

    artifact_total = sum(d["score"] for d in dataset_scores) + sum(
        r["score"] for r in repo_scores
    )

    # Paper Impact: P = h × (1 + log₁₀(c + 1))
    h = semantic_scholar_data.get("h_index", 0) or 0
    c = semantic_scholar_data.get("citation_count", 0) or 0
    paper_impact = h * (1 + math.log10(c + 1)) if h > 0 else 0.0

    s_index = paper_impact + artifact_total

    return {
        "s_index": round(s_index, 2),
        "paper_impact": round(paper_impact, 3),
        "artifact_total": round(artifact_total, 3),
        "dataset_scores": dataset_scores,
        "repo_scores": repo_scores,
        "summary": {
            "total_datasets": len(dataset_scores),
            "total_repos_scored": len(repo_scores),
            "h_index": h,
            "i10_index": semantic_scholar_data.get("i10_index", 0),
            "total_citations": c,
            "total_papers": semantic_scholar_data.get("paper_count", 0),
        },
    }
