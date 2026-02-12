"""S-Index v2 calculator following the framework from github.com/martinfrasch/s-index.

Per-Object Score:  s_j = Q_j × I_j × C_j

  Quality:       Q_j = 5 · p_j · ℓ_j · (1 + 0.5·b_DOI + 0.3·b_doc + 0.2·b_fmt)
  Impact:        I_j = 1 + ln(1 + r_j / μ_t)
  Collaboration: C_j = √(N_a · N_i)

Researcher:      S_i = P + Σ s_j
                 P   = h · (1 + log₁₀(c + 1))
"""

import math

# Field medians for impact normalization (v2.0 deployment baselines)
FIELD_MEDIANS = {"dataset": 50, "code": 10}


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


def score_figshare_article(article: dict) -> dict:
    """Compute S-Index v2 score for a single Figshare article."""
    item = {
        "is_public": True,
        "license": article.get("license", ""),
        "has_doi": bool(article.get("doi")),
        "has_readme": bool(
            article.get("description") and len(article.get("description", "")) > 50
        ),
        "is_standard_format": article.get("defined_type_name")
        in ("dataset", "software", "code", "figure", "media", "poster", "presentation"),
    }
    quality = _quality_score(item)

    reuse = (article.get("downloads", 0) or 0) + (article.get("views", 0) or 0) // 10
    impact = _impact_score(reuse, "dataset")

    n_authors = max(len(article.get("authors", []) or []), 1)
    collab = _collaboration_score(n_authors, 1)

    s = quality["Q"] * impact * collab
    return {
        "title": article.get("title", ""),
        "quality": quality["Q"],
        "fair_gate": quality["fair_gate"],
        "impact": round(impact, 3),
        "collaboration": round(collab, 3),
        "score": round(s, 3),
    }


def score_github_repo(repo: dict) -> dict:
    """Compute S-Index v2 score for a single GitHub repo."""
    item = {
        "is_public": True,
        "license": "present" if repo.get("has_license") else "",
        "has_doi": False,
        "has_readme": repo.get("has_readme", False),
        "is_standard_format": True,
    }
    quality = _quality_score(item)

    reuse = (repo.get("stars", 0) or 0) + (repo.get("forks", 0) or 0) * 3
    impact = _impact_score(reuse, "code")
    collab = _collaboration_score(1)

    s = quality["Q"] * impact * collab
    return {
        "title": repo.get("name", ""),
        "quality": quality["Q"],
        "fair_gate": quality["fair_gate"],
        "impact": round(impact, 3),
        "collaboration": round(collab, 3),
        "score": round(s, 3),
    }


def compute_researcher_qic(
    figshare_data: dict,
    github_data: dict,
    semantic_scholar_data: dict,
) -> dict:
    """Compute S-Index v2 for a researcher across all artifacts.

    S_i = P + Σ s_j    where P = h × (1 + log₁₀(c + 1))
    """
    dataset_scores = []
    for article in figshare_data.get("articles", []):
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
