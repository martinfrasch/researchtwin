# Self-Hosting Guide: Tier 1 Local Node

Run your own ResearchTwin instance locally with full control over your data. A Local Node gives you the same experience as the hosted version — knowledge graph, S-Index metrics, discovery API, and optional chat — running on your own machine.

---

## Prerequisites

- **Python 3.10+**
- **pip** (Python package manager)
- **Git**
- **Anthropic API key** (optional, for chat feature only)

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/martinfrasch/researchtwin.git
cd researchtwin
pip install -r backend/requirements.txt
```

### 2. Configure Your Profile

```bash
cp node_config.json.example node_config.json
```

Edit `node_config.json` with your details:

```json
{
  "display_name": "Jane Doe",
  "email": "jane@university.edu",
  "semantic_scholar_id": "12345678",
  "google_scholar_id": "aBcDeFgHiJk",
  "github_username": "janedoe",
  "figshare_search_name": "Jane Doe",
  "orcid": "0000-0002-1234-5678",
  "tier": 1,
  "port": 8000,
  "register_with_hub": false,
  "hub_url": "https://researchtwin.net"
}
```

### 3. Launch

```bash
python run_node.py --config node_config.json
```

Open `http://localhost:8000/?researcher=jane-doe` in your browser.

---

## Configuration Reference

### Config File Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `display_name` | yes | — | Your full name as shown on the profile |
| `email` | yes | — | Contact email (used for hub registration) |
| `semantic_scholar_id` | no | `""` | Numeric author ID from [semanticscholar.org](https://www.semanticscholar.org/) |
| `google_scholar_id` | no | `""` | Profile ID from Google Scholar URL |
| `github_username` | no | `""` | GitHub username |
| `figshare_search_name` | no | `""` | Name used to search Figshare |
| `orcid` | no | `""` | ORCID iD in `XXXX-XXXX-XXXX-XXXX` format |
| `tier` | no | `1` | Always `1` for local nodes |
| `port` | no | `8000` | HTTP port |
| `register_with_hub` | no | `false` | Register with researchtwin.net for discoverability |
| `hub_url` | no | `https://researchtwin.net` | Hub URL for registration |

### Finding Your Connector IDs

**Semantic Scholar**: Go to [semanticscholar.org](https://www.semanticscholar.org/), search for your name, click your profile. The numeric ID is in the URL: `semanticscholar.org/author/.../XXXXXXXXX`.

**Google Scholar**: Go to [scholar.google.com](https://scholar.google.com/), click your profile. The ID is the `user=` parameter in the URL: `scholar.google.com/citations?user=XXXXXXXXXXX`.

**GitHub**: Your GitHub username from `github.com/USERNAME`.

**Figshare**: The search name used to find your datasets on Figshare. Usually your full name.

**ORCID**: Your ORCID iD from [orcid.org](https://orcid.org/) in the format `0000-0002-1234-5678`.

---

## CLI Arguments

All config file fields can be overridden via CLI flags:

```bash
python run_node.py --name "Jane Doe" --email jane@uni.edu --gh-user janedoe --port 9000
```

| Flag | Config Equivalent | Description |
|------|-------------------|-------------|
| `--config`, `-c` | — | Path to config file |
| `--name` | `display_name` | Researcher name |
| `--email` | `email` | Contact email |
| `--ss-id` | `semantic_scholar_id` | Semantic Scholar ID |
| `--gs-id` | `google_scholar_id` | Google Scholar ID |
| `--gh-user` | `github_username` | GitHub username |
| `--figshare` | `figshare_search_name` | Figshare name |
| `--orcid` | `orcid` | ORCID iD |
| `--port` | `port` | HTTP port |
| `--register-hub` | `register_with_hub` | Register with the hub |

CLI flags take precedence over config file values.

---

## Enabling Chat (Optional)

The chat feature requires an Anthropic API key. Without it, the knowledge graph, S-Index, and discovery API still work.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python run_node.py --config node_config.json
```

Or add it to a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Registering with the Hub

To make your local node discoverable on the global network at [researchtwin.net](https://researchtwin.net):

```bash
python run_node.py --config node_config.json --register-hub
```

Or set `"register_with_hub": true` in your config file.

This sends a `POST /api/register` to the hub with your profile data. Your node runs independently — hub registration is optional and the local node works fully offline.

---

## What You Get

A local node provides the full ResearchTwin experience:

| Feature | Available | Notes |
|---------|-----------|-------|
| Knowledge graph (D3.js) | Yes | Interactive visualization of your research |
| S-Index computation | Yes | Real-time Quality-Impact-Collaboration scoring |
| Discovery API | Yes | Machine-readable endpoints at `/api/researcher/{slug}/...` |
| Chat (RAG) | Requires API key | Set `ANTHROPIC_API_KEY` |
| Self-registration | N/A | Single-researcher instance |
| Swagger docs | Yes | Available at `/docs` (enabled by default for local nodes) |

---

## Data Storage

Local nodes store data in `./data/researchtwin.db` (SQLite with WAL mode). This file is created automatically on first launch.

To back up your data:
```bash
cp data/researchtwin.db data/researchtwin.db.backup
```

To reset:
```bash
rm data/researchtwin.db
python run_node.py --config node_config.json  # recreates from config
```

---

## Docker Alternative

For containerized deployment, use Docker Compose:

```bash
cp .env.example .env  # Add API keys
docker compose up -d --build
```

The `docker-compose.yml` mounts `./backend/data` to persist the database across container restarts.

---

## Troubleshooting

**"No module named 'connectors'"**: Make sure you run `run_node.py` from the project root directory, not from inside `backend/`.

**"ANTHROPIC_API_KEY not set"**: This is informational. All features except `/chat` work without it.

**"Email already registered"** (during hub registration): Your email is already on the hub. Your local node still works independently.

**Slow first load**: The first request fetches live data from Semantic Scholar, GitHub, and Figshare. Subsequent requests use the 24-hour cache.

**Port already in use**: Change the port with `--port 9000` or in `node_config.json`.
