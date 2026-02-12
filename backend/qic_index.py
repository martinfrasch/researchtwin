"""QIC-Index calculator following the framework from github.com/martinfrasch/s-index.

QIC = Quality × Impact × Collaboration

Q = 0.3*F + 0.3*A + 0.2*I + 0.2*R   (FAIR scores, each 0-10)
I = 1 + ln(1 + reuse_events)
C = (1 + ln(N_authors)) × (1 + 0.5 × ln(N_institutions))
"""

import math


def _quality_score(item: dict) -> dict:
    """Estimate FAIR sub-scores from available metadata.

    Returns dict with f, a, i, r sub-scores and total Q.
    """
    # Findability: DOI, metadata completeness
    f = 0.0
    if item.get("doi"):
        f += 6.0
    if item.get("title"):
        f += 2.0
    if item.get("description") or item.get("categories"):
        f += 2.0
    f = min(f, 10.0)

    # Accessibility: publicly available, API-accessible
    a = 0.0
    if item.get("url"):
        a += 5.0
    if item.get("is_public", True):  # default True for data we can fetch
        a += 3.0
    if item.get("files_count", 0) > 0:
        a += 2.0
    a = min(a, 10.0)

    # Interoperability: standard formats, schemas
    i = 0.0
    if item.get("defined_type_name") in ("dataset", "software", "code"):
        i += 4.0
    if item.get("doi"):
        i += 3.0  # DOI implies some standard metadata
    if item.get("categories"):
        i += 3.0
    i = min(i, 10.0)

    # Reusability: license, documentation
    r = 0.0
    if item.get("license"):
        r += 5.0
    if item.get("description") and len(item.get("description", "")) > 50:
        r += 3.0
    if item.get("has_readme") or item.get("files_count", 0) > 1:
        r += 2.0
    r = min(r, 10.0)

    q = 0.3 * f + 0.3 * a + 0.2 * i + 0.2 * r
    return {"findability": f, "accessibility": a, "interoperability": i, "reusability": r, "Q": q}


def _impact_score(reuse_events: int) -> float:
    """I = 1 + ln(1 + reuse_events)"""
    return 1.0 + math.log(1 + max(reuse_events, 0))


def _collaboration_score(n_authors: int, n_institutions: int = 1) -> float:
    """C = (1 + ln(N_authors)) × (1 + 0.5 × ln(N_institutions))"""
    n_a = max(n_authors, 1)
    n_i = max(n_institutions, 1)
    return (1 + math.log(n_a)) * (1 + 0.5 * math.log(n_i))


def score_figshare_article(article: dict) -> dict:
    """Compute QIC for a single Figshare article."""
    quality = _quality_score(article)
    reuse = (article.get("downloads", 0) or 0) + (article.get("views", 0) or 0) // 10
    impact = _impact_score(reuse)
    n_authors = len(article.get("authors", []) or [1])
    collab = _collaboration_score(n_authors)
    s = quality["Q"] * impact * collab
    return {
        "title": article.get("title", ""),
        "quality": quality,
        "impact": round(impact, 3),
        "collaboration": round(collab, 3),
        "score": round(s, 3),
    }


def score_github_repo(repo: dict) -> dict:
    """Compute QIC for a single GitHub repo."""
    item = {
        "title": repo.get("name", ""),
        "description": repo.get("description", ""),
        "url": repo.get("url", ""),
        "license": "present" if repo.get("has_license") else "",
        "has_readme": repo.get("has_readme", False),
        "is_public": True,
        "defined_type_name": "code",
    }
    quality = _quality_score(item)
    reuse = (repo.get("stars", 0) or 0) + (repo.get("forks", 0) or 0) * 3
    impact = _impact_score(reuse)
    collab = _collaboration_score(1)  # we don't fetch contributors
    s = quality["Q"] * impact * collab
    return {
        "title": repo.get("name", ""),
        "quality": quality,
        "impact": round(impact, 3),
        "collaboration": round(collab, 3),
        "score": round(s, 3),
    }


def compute_researcher_qic(
    figshare_data: dict,
    github_data: dict,
    semantic_scholar_data: dict,
) -> dict:
    """Compute aggregate QIC-Index for a researcher across all data objects.

    Returns per-object breakdowns and total S-index.
    """
    dataset_scores = []
    for article in figshare_data.get("articles", []):
        dataset_scores.append(score_figshare_article(article))

    repo_scores = []
    for repo in github_data.get("top_repos", [])[:10]:
        repo_scores.append(score_github_repo(repo))

    total_score = sum(d["score"] for d in dataset_scores) + sum(r["score"] for r in repo_scores)

    # Paper-based metrics from Semantic Scholar (impact proxy)
    paper_impact = 0.0
    if semantic_scholar_data.get("citation_count", 0) > 0:
        paper_impact = _impact_score(semantic_scholar_data["citation_count"])

    return {
        "s_index": round(total_score, 2),
        "paper_impact": round(paper_impact, 3),
        "dataset_scores": dataset_scores,
        "repo_scores": repo_scores,
        "summary": {
            "total_datasets": len(dataset_scores),
            "total_repos_scored": len(repo_scores),
            "h_index": semantic_scholar_data.get("h_index", 0),
            "i10_index": semantic_scholar_data.get("i10_index", 0),
            "total_citations": semantic_scholar_data.get("citation_count", 0),
            "total_papers": semantic_scholar_data.get("paper_count", 0),
        },
    }
