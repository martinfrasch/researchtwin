#!/usr/bin/env python3
"""
ResearchTwin Local Node Launcher (Tier 1)

Run your own ResearchTwin instance with a single command:

    python run_node.py --config node_config.json

Or with inline arguments:

    python run_node.py --name "Jane Doe" --email jane@uni.edu --gh-user janedoe

Prerequisites:
    pip install -r backend/requirements.txt
"""

import argparse
import json
import os
import sys


def load_config(args):
    """Build researcher config from --config file or CLI flags."""
    cfg = {}

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)

    # CLI flags override config file values
    if args.name:
        cfg["display_name"] = args.name
    if args.email:
        cfg["email"] = args.email
    if args.ss_id is not None:
        cfg["semantic_scholar_id"] = args.ss_id
    if args.gs_id is not None:
        cfg["google_scholar_id"] = args.gs_id
    if args.gh_user is not None:
        cfg["github_username"] = args.gh_user
    if args.figshare is not None:
        cfg["figshare_search_name"] = args.figshare
    if args.orcid is not None:
        cfg["orcid"] = args.orcid
    if args.port:
        cfg["port"] = args.port

    # Validate required fields
    if not cfg.get("display_name"):
        sys.exit("Error: display_name is required (use --name or set in config file)")
    if not cfg.get("email"):
        sys.exit("Error: email is required (use --email or set in config file)")

    # Apply defaults
    cfg.setdefault("tier", 1)
    cfg.setdefault("port", 8000)
    cfg.setdefault("semantic_scholar_id", "")
    cfg.setdefault("google_scholar_id", "")
    cfg.setdefault("github_username", "")
    cfg.setdefault("figshare_search_name", "")
    cfg.setdefault("orcid", "")
    cfg.setdefault("register_with_hub", False)
    cfg.setdefault("hub_url", "https://researchtwin.net")

    return cfg


def register_with_hub(cfg):
    """Register this node with the central hub (researchtwin.net)."""
    import requests

    hub_url = cfg.get("hub_url", "https://researchtwin.net").rstrip("/")
    endpoint = f"{hub_url}/api/register"

    payload = {
        "name": cfg["display_name"],
        "email": cfg["email"],
        "tier": 1,
        "semantic_scholar_id": cfg.get("semantic_scholar_id", ""),
        "google_scholar_id": cfg.get("google_scholar_id", ""),
        "github_username": cfg.get("github_username", ""),
        "figshare_search_name": cfg.get("figshare_search_name", ""),
        "orcid": cfg.get("orcid", ""),
    }

    print(f"Registering with hub at {endpoint}...")
    try:
        resp = requests.post(endpoint, json=payload, timeout=15)
        if resp.ok:
            data = resp.json()
            print(f"Registered as: {data.get('slug', '?')}")
            print(f"View at: {hub_url}/?researcher={data.get('slug', '')}")
        else:
            detail = resp.json().get("detail", resp.text)
            print(f"Hub registration returned {resp.status_code}: {detail}")
    except requests.RequestException as e:
        print(f"Could not reach hub: {e}")
        print("Your local node will still work — hub registration is optional.")


def main():
    parser = argparse.ArgumentParser(
        description="Launch a ResearchTwin Local Node (Tier 1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_node.py --config node_config.json
  python run_node.py --name "Jane Doe" --email jane@uni.edu --gh-user janedoe
  python run_node.py --config node_config.json --register-hub
        """,
    )
    parser.add_argument("--config", "-c", help="Path to node_config.json")
    parser.add_argument("--name", help="Researcher display name")
    parser.add_argument("--email", help="Researcher email")
    parser.add_argument("--ss-id", help="Semantic Scholar author ID")
    parser.add_argument("--gs-id", help="Google Scholar profile ID")
    parser.add_argument("--gh-user", help="GitHub username")
    parser.add_argument("--figshare", help="Figshare author search name")
    parser.add_argument("--orcid", help="ORCID identifier")
    parser.add_argument("--port", type=int, default=None, help="Port (default: 8000)")
    parser.add_argument(
        "--register-hub",
        action="store_true",
        help="Register this node with the central hub for discoverability",
    )

    args = parser.parse_args()
    cfg = load_config(args)

    # Add backend/ to sys.path so imports resolve
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    # Set local data directory (not Docker's /app/data)
    local_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(local_data, exist_ok=True)
    os.environ.setdefault("DB_PATH", os.path.join(local_data, "researchtwin.db"))

    # Enable dev docs for local nodes
    os.environ.setdefault("ENV", "dev")

    # Initialize database and seed the researcher
    import database
    import researchers

    database.init_db()

    slug = researchers.generate_slug(cfg["display_name"])
    existing = researchers.get_by_email(cfg["email"])
    if existing:
        slug = existing["slug"]
        print(f"Researcher already registered: {slug}")
    else:
        slug = researchers.create_researcher(
            slug=slug,
            display_name=cfg["display_name"],
            email=cfg["email"],
            tier=cfg["tier"],
            semantic_scholar_id=cfg.get("semantic_scholar_id", ""),
            google_scholar_id=cfg.get("google_scholar_id", ""),
            github_username=cfg.get("github_username", ""),
            figshare_search_name=cfg.get("figshare_search_name", ""),
            orcid=cfg.get("orcid", ""),
        )
        print(f"Created researcher: {slug}")

    # Optionally register with the hub
    if args.register_hub or cfg.get("register_with_hub"):
        register_with_hub(cfg)

    # Check for Anthropic API key (chat feature)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nNote: ANTHROPIC_API_KEY not set — the /chat endpoint will be disabled.")
        print("All other features (graph, metrics, discovery API) work without it.\n")

    port = cfg.get("port", 8000)
    print(f"\nStarting ResearchTwin Local Node on http://localhost:{port}")
    print(f"Researcher: {cfg['display_name']} ({slug})")
    print(f"Open http://localhost:{port}/?researcher={slug} in your browser\n")

    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
