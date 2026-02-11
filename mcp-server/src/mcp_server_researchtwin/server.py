"""ResearchTwin MCP Server — inter-agentic research discovery.

Exposes the ResearchTwin platform API as MCP tools for AI agents to discover
researchers, papers, datasets, repositories, and S-Index metrics.

Usage:
    # stdio transport (for Claude Desktop)
    mcp-server-researchtwin

    # With custom base URL
    RESEARCHTWIN_URL=http://localhost:8000 mcp-server-researchtwin
"""

import json
import os

import httpx
from mcp.server import FastMCP
from mcp.types import ToolAnnotations

BASE_URL = os.environ.get("RESEARCHTWIN_URL", "https://researchtwin.net").rstrip("/")
TIMEOUT = 30

mcp = FastMCP(
    name="researchtwin",
    instructions=(
        "ResearchTwin is a federated platform for research discovery. "
        "Use these tools to find researchers, explore their publications, "
        "datasets, and code repositories, and compute S-Index impact metrics. "
        "Start with list_researchers or discover to find relevant research."
    ),
)


async def _get(path: str, params: dict | None = None) -> dict:
    """Make a GET request to the ResearchTwin API."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(annotations=ToolAnnotations(title="List Researchers", read_only_hint=True))
async def list_researchers() -> str:
    """List all researchers registered on the ResearchTwin platform.

    Returns researcher slugs and display names. Use a slug with other
    tools to explore a specific researcher's profile, papers, datasets,
    and repositories.
    """
    data = await _get("/api/researchers")
    researchers = data.get("researchers", [])
    if not researchers:
        return "No researchers registered yet."
    lines = [f"- **{r['display_name']}** (slug: `{r['slug']}`)" for r in researchers]
    return f"**{len(researchers)} researchers:**\n" + "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(title="Get Researcher Profile", read_only_hint=True))
async def get_profile(slug: str) -> str:
    """Get a researcher's profile with S-Index score and summary metrics.

    Args:
        slug: Researcher identifier (e.g. 'martin-frasch'). Use list_researchers to find valid slugs.

    Returns structured profile with S-Index, h-index, paper count, citation count,
    and links to papers/datasets/repos endpoints.
    """
    data = await _get(f"/api/researcher/{slug}/profile")
    return json.dumps(data, indent=2)


@mcp.tool(annotations=ToolAnnotations(title="Get Researcher Context", read_only_hint=True))
async def get_context(slug: str) -> str:
    """Get comprehensive research context for a researcher including all data source metrics.

    Args:
        slug: Researcher identifier (e.g. 'martin-frasch').

    Returns S-Index, paper impact, source connection status (Semantic Scholar,
    Google Scholar, GitHub, Figshare), dataset QIC scores, and repo QIC scores.
    More detailed than get_profile — use this when you need the full picture.
    """
    data = await _get(f"/api/context/{slug}")
    return json.dumps(data, indent=2)


@mcp.tool(annotations=ToolAnnotations(title="Get Papers", read_only_hint=True))
async def get_papers(slug: str) -> str:
    """Get a researcher's publications with citation counts.

    Args:
        slug: Researcher identifier.

    Returns papers from Semantic Scholar and Google Scholar (merged, deduplicated)
    with titles, years, citation counts, and URLs.
    """
    data = await _get(f"/api/researcher/{slug}/papers")
    items = data.get("items", [])
    if not items:
        return f"No papers found for {slug}."

    lines = []
    for p in items[:20]:
        year = p.get("year") or "?"
        cites = p.get("citations", 0)
        lines.append(f"- [{year}] **{p['title']}** ({cites} citations)")

    return f"**{data.get('total', len(items))} papers for {slug}:**\n" + "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(title="Get Datasets", read_only_hint=True))
async def get_datasets(slug: str) -> str:
    """Get a researcher's datasets with QIC (Quality x Impact x Collaboration) scores.

    Args:
        slug: Researcher identifier.

    Returns Figshare datasets with DOIs, download/view counts, and QIC scores
    computed using FAIR-based quality assessment.
    """
    data = await _get(f"/api/researcher/{slug}/datasets")
    items = data.get("items", [])
    if not items:
        return f"No datasets found for {slug}."

    lines = []
    for ds in items:
        qic = ds.get("qic_score", 0)
        lines.append(f"- **{ds['title']}** (QIC: {qic}, downloads: {ds.get('downloads', 0)})")

    return f"**{data.get('total', len(items))} datasets for {slug}:**\n" + "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(title="Get Repositories", read_only_hint=True))
async def get_repos(slug: str) -> str:
    """Get a researcher's code repositories with QIC scores.

    Args:
        slug: Researcher identifier.

    Returns GitHub repositories with stars, forks, language, and QIC scores
    computed using FAIR-based quality assessment.
    """
    data = await _get(f"/api/researcher/{slug}/repos")
    items = data.get("items", [])
    if not items:
        return f"No repositories found for {slug}."

    lines = []
    for repo in items:
        qic = repo.get("qic_score", 0)
        lang = repo.get("language") or "?"
        lines.append(
            f"- **{repo['name']}** ({lang}, {repo.get('stars', 0)} stars, QIC: {qic})"
            + (f" — {repo['description']}" if repo.get("description") else "")
        )

    return f"**{data.get('total', len(items))} repos for {slug}:**\n" + "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(title="Discover Research", read_only_hint=True))
async def discover(query: str, type: str = "") -> str:
    """Search across all researchers for papers, datasets, or repositories matching a keyword.

    Args:
        query: Search keyword (e.g. 'fetal', 'machine learning', 'turbulence').
        type: Optional filter — 'paper', 'dataset', or 'repo'. Leave empty to search all types.

    Returns matching items across all registered researchers, sorted by relevance.
    This is the primary tool for cross-researcher discovery.
    """
    params = {"q": query}
    if type:
        params["type"] = type

    data = await _get("/api/discover", params=params)
    results = data.get("results", [])
    if not results:
        return f"No results found for '{query}'" + (f" (type: {type})" if type else "") + "."

    lines = []
    for r in results[:20]:
        rtype = r.get("@type", "Unknown")
        name = r.get("title") or r.get("name", "Untitled")
        researcher = r.get("researcher", "")
        slug = r.get("researcher_slug", "")

        if rtype == "ScholarlyArticle":
            cites = r.get("citations", 0)
            lines.append(f"- [Paper] **{name}** by {researcher} ({cites} citations)")
        elif rtype == "Dataset":
            qic = r.get("qic_score", 0)
            lines.append(f"- [Dataset] **{name}** by {researcher} (QIC: {qic})")
        elif rtype == "SoftwareSourceCode":
            qic = r.get("qic_score", 0)
            lines.append(f"- [Repo] **{name}** by {researcher} (QIC: {qic})")

    total = data.get("total", len(results))
    shown = min(20, total)
    header = f"**{total} results for '{query}'**"
    if type:
        header += f" (type: {type})"
    if total > shown:
        header += f" (showing top {shown})"

    return header + ":\n" + "\n".join(lines)


@mcp.tool(annotations=ToolAnnotations(title="Get Network Map", read_only_hint=True))
async def get_network_map() -> str:
    """Get geographic affiliations for all researchers in the network.

    Returns researchers with their institutional affiliations and coordinates,
    sourced from ORCID and Semantic Scholar. Useful for understanding the
    geographic distribution of the research network.
    """
    data = await _get("/api/network/map")
    researchers = data.get("researchers", [])
    if not researchers:
        return "No affiliation data available yet."

    lines = []
    for r in researchers:
        affs = r.get("affiliations", [])
        aff_strs = []
        for a in affs:
            loc = [a.get("city"), a.get("country")]
            loc_str = ", ".join(x for x in loc if x)
            status = "current" if a.get("current") else "past"
            aff_strs.append(f"  - {a['institution']}" + (f" ({loc_str})" if loc_str else "") + f" [{status}]")
        lines.append(f"**{r['name']}** (`{r['slug']}`):\n" + "\n".join(aff_strs))

    return f"**Network map — {data.get('total_researchers', len(researchers))} researchers:**\n\n" + "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("researchtwin://about")
def about() -> str:
    """Information about the ResearchTwin platform and its API."""
    return (
        "ResearchTwin is a federated platform that creates conversational digital twins "
        "of researchers by integrating data from Semantic Scholar, Google Scholar, GitHub, "
        "and Figshare. It computes the S-Index (Quality x Impact x Collaboration) across "
        "all research output types.\n\n"
        f"Platform: {BASE_URL}\n"
        f"API base: {BASE_URL}/api/\n\n"
        "Available tools:\n"
        "- list_researchers: Find all registered researchers\n"
        "- get_profile: Get researcher profile with S-Index\n"
        "- get_context: Get full research context with all metrics\n"
        "- get_papers: Get publications with citations\n"
        "- get_datasets: Get datasets with QIC scores\n"
        "- get_repos: Get repositories with QIC scores\n"
        "- discover: Search across all researchers\n"
        "- get_network_map: Geographic affiliation map\n"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
