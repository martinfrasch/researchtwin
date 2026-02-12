"""
S-Index v2 Reference Implementation
====================================
Transparent S-Index with FAIR gate, field-normalized impact, and geometric collaboration.

Formula: s_j = Q_j * I_j * C_j

  Quality:       Q_j = 5 * p_j * l_j * (1 + 0.5*b_DOI + 0.3*b_README + 0.2*b_fmt)
  Impact:        I_j = 1 + ln(1 + r_j / mu_t)
  Collaboration: C_j = sqrt(N_a * N_i)

  Researcher:    S_i = P + sum(s_j)  where P = h * (1 + log10(c + 1))
"""

import math


def calculate_s_index_v2(artifacts, field_medians):
    """
    Calculates the Transparent S-Index (v2) for a list of artifacts.

    Parameters
    ----------
    artifacts : list[dict]
        Each artifact must have keys:
            name, type, is_public, has_license, has_doi, has_readme,
            is_standard_format, reuse_events, n_authors, n_institutions
    field_medians : dict[str, float]
        Mapping from artifact type to median reuse count (e.g., {'dataset': 50, 'code': 10})

    Returns
    -------
    list[dict]
        Per-artifact scores with quality, impact, collab, and s_index_v2 fields.
    """
    results = []

    for art in artifacts:
        # 1. Quality Component: FAIR Gate * (1 + Bonuses)
        #    Gate: public AND licensed = 5, else 0
        base = 5 if (art["is_public"] and art["has_license"]) else 0

        bonuses = 0.0
        if art.get("has_doi"):
            bonuses += 0.5
        if art.get("has_readme"):
            bonuses += 0.3
        if art.get("is_standard_format"):
            bonuses += 0.2

        quality_score = base * (1 + bonuses)

        # 2. Impact Component: field-normalized log scaling
        #    I = 1 + ln(1 + r/mu)
        r = art["reuse_events"]
        mu = field_medians.get(art["type"], 1)
        impact_score = 1 + math.log(1 + (r / mu))

        # 3. Collaboration Component: geometric mean
        #    C = sqrt(authors * institutions)
        collab_score = math.sqrt(art["n_authors"] * art["n_institutions"])

        # Total per-object score
        total_score = quality_score * impact_score * collab_score

        results.append(
            {
                "name": art["name"],
                "type": art["type"],
                "quality": round(quality_score, 2),
                "impact": round(impact_score, 2),
                "collab": round(collab_score, 2),
                "s_index_v2": round(total_score, 2),
            }
        )

    return results


def calculate_paper_impact(h_index, total_citations):
    """Paper Impact term (unchanged from v1): P = h * (1 + log10(c + 1))"""
    return h_index * (1 + math.log10(total_citations + 1))


def calculate_researcher_s_index(paper_impact, artifact_scores):
    """Researcher S-Index: S_i = P + sum(s_j)"""
    return paper_impact + sum(a["s_index_v2"] for a in artifact_scores)


# --- Self-test ---
if __name__ == "__main__":
    field_medians = {"dataset": 50, "code": 10}

    sample_artifacts = [
        {
            "name": "Genomic_Dataset_Alpha",
            "type": "dataset",
            "is_public": True,
            "has_license": True,
            "has_doi": True,
            "has_readme": True,
            "is_standard_format": True,
            "reuse_events": 250,
            "n_authors": 12,
            "n_institutions": 4,
        },
        {
            "name": "Quick_Script_Beta",
            "type": "code",
            "is_public": True,
            "has_license": True,
            "has_doi": False,
            "has_readme": False,
            "is_standard_format": True,
            "reuse_events": 5,
            "n_authors": 1,
            "n_institutions": 1,
        },
        {
            "name": "Collaborative_Tool_Gamma",
            "type": "code",
            "is_public": True,
            "has_license": True,
            "has_doi": True,
            "has_readme": True,
            "is_standard_format": True,
            "reuse_events": 80,
            "n_authors": 5,
            "n_institutions": 5,
        },
        {
            "name": "Siloed_Data_Delta",
            "type": "dataset",
            "is_public": True,
            "has_license": False,
            "has_doi": True,
            "has_readme": True,
            "is_standard_format": True,
            "reuse_events": 1000,
            "n_authors": 2,
            "n_institutions": 1,
        },
    ]

    scores = calculate_s_index_v2(sample_artifacts, field_medians)
    sorted_scores = sorted(scores, key=lambda x: x["s_index_v2"], reverse=True)

    print("S-Index v2 Reference Implementation — Test Results")
    print("=" * 70)
    for s in sorted_scores:
        print(
            f"  {s['name']:30s}  Q={s['quality']:5.1f}  I={s['impact']:5.2f}  "
            f"C={s['collab']:5.2f}  S={s['s_index_v2']:7.2f}"
        )
    print()

    # Verify FAIR gate
    delta = [s for s in scores if s["name"] == "Siloed_Data_Delta"][0]
    assert delta["s_index_v2"] == 0.0, "FAIR gate failed: unlicensed artifact should score 0"
    print("FAIR gate verified: unlicensed artifact scores 0 despite 1000 reuse events")

    # Verify field normalization
    alpha = [s for s in scores if s["name"] == "Genomic_Dataset_Alpha"][0]
    gamma = [s for s in scores if s["name"] == "Collaborative_Tool_Gamma"][0]
    assert alpha["impact"] < gamma["impact"], "Field normalization: 250/50=5x should < 80/10=8x"
    print("Field normalization verified: 80/10 median > 250/50 median in impact")
