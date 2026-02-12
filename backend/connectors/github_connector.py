"""GitHub API connector for public repository data."""

import os

import httpx

import cache

GH_API = "https://api.github.com"


async def fetch_github_data(username: str) -> dict:
    """Fetch public repos and aggregate stats for a GitHub user."""
    cache_key = f"gh:user:{username}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GH_API}/users/{username}/repos",
            params={"sort": "updated", "per_page": 100},
            headers=headers,
        )
        resp.raise_for_status()
        repos = resp.json()

    languages = {}
    total_stars = 0
    parsed_repos = []

    for r in repos:
        if r.get("fork"):
            continue
        stars = r.get("stargazers_count", 0)
        total_stars += stars
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        parsed_repos.append({
            "name": r.get("name", ""),
            "description": r.get("description") or "",
            "stars": stars,
            "forks": r.get("forks_count", 0),
            "language": lang,
            "updated_at": r.get("updated_at", ""),
            "url": r.get("html_url", ""),
            "has_license": r.get("license") is not None,
            "has_readme": True,  # assume True for public repos
        })

    # Sort by stars descending
    parsed_repos.sort(key=lambda r: r["stars"], reverse=True)

    result = {
        "username": username,
        "total_repos": len(parsed_repos),
        "total_stars": total_stars,
        "languages": languages,
        "top_repos": parsed_repos[:15],
    }

    cache.set(cache_key, result)
    return result
