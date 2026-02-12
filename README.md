# ResearchTwin: Federated Agentic Web of Research Knowledge

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live Platform](https://img.shields.io/badge/platform-researchtwin.net-blue)](https://researchtwin.net)
[![S-Index Spec](https://img.shields.io/badge/metric-S--Index-green)](https://github.com/martinfrasch/s-index)
[![Project Board](https://img.shields.io/badge/project-Ecosystem-purple)](https://github.com/users/martinfrasch/projects/8)

ResearchTwin is an open-source, federated platform that transforms a researcher's publications, datasets, and code repositories into a conversational **Digital Twin**. Built on a Bimodal Glial-Neural Optimization (BGNO) architecture, it enables dual-discovery where both humans and AI agents collaborate to accelerate scientific discovery.

**Live at [researchtwin.net](https://researchtwin.net)** | **[Join the Network](https://researchtwin.net/join.html)**

---

## Project Vision

The exponential growth of scientific outputs has created a "discovery bottleneck." Traditional static PDFs and siloed repositories limit knowledge synthesis and reuse. ResearchTwin addresses this by:

- Integrating multi-modal research artifacts from **Semantic Scholar**, **Google Scholar**, **GitHub**, and **Figshare**
- Computing a real-time **[S-Index](https://github.com/martinfrasch/s-index)** metric (Quality × Impact × Collaboration) across all output types
- Providing a conversational chatbot interface for interactive research exploration
- Exposing an **Inter-Agentic Discovery API** with Schema.org types for machine-to-machine research discovery
- Enabling a **federated, Discord-like architecture** supporting local nodes, hubs, and hosted edges

---

## Architecture Overview

### BGNO (Bimodal Glial-Neural Optimization)

```
Data Sources          Glial Layer          Neural Layer         Interface
┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌────────────┐
│Semantic Scholar│───▶│             │    │              │    │  Web Chat  │
│Google Scholar │───▶│  SQLite     │───▶│  RAG with    │───▶│  Discord   │
│GitHub API     │───▶│  Cache +    │    │  Claude API  │    │  Agent API │
│Figshare API   │───▶│  Rate Limit │    │              │    │  Embed     │
└──────────────┘    └─────────────┘    └──────────────┘    └────────────┘
```

- **Connector Layer**: Pulls papers (S2+GS with deduplication), repos (GitHub), datasets (Figshare), and ORCID metadata
- **Glial Layer**: SQLite caching with 24h TTL, rate limiting, S2+GS title-similarity merge (0.85 threshold)
- **Neural Layer**: RAG with Claude — context assembly, prompt engineering, conversational synthesis
- **Interface Layer**: D3.js knowledge graph, chat widget, Discord bot, REST API

### Federated Network Tiers

| Tier | Name | Description | Status |
|------|------|-------------|--------|
| **Tier 1** | Local Nodes | Researchers run `python run_node.py` locally | Live |
| **Tier 2** | Hubs | Lab aggregators federating multiple nodes | Planned |
| **Tier 3** | Hosted Edges | Cloud-hosted at researchtwin.net | Live |

### Inter-Agentic Discovery API

Machine-readable endpoints with Schema.org `@type` annotations:

| Endpoint | Schema.org Type | Purpose |
|----------|----------------|---------|
| `GET /api/researcher/{slug}/profile` | `Person` | Researcher profile with HATEOAS links |
| `GET /api/researcher/{slug}/papers` | `ItemList` of `ScholarlyArticle` | Papers with citations |
| `GET /api/researcher/{slug}/datasets` | `ItemList` of `Dataset` | Datasets with QIC scores |
| `GET /api/researcher/{slug}/repos` | `ItemList` of `SoftwareSourceCode` | Repos with QIC scores |
| `GET /api/discover?q=keyword&type=paper` | `SearchResultSet` | Cross-researcher search |

---

## Getting Started

### Hosted (Tier 3) — Zero Setup

1. Visit [researchtwin.net/join.html](https://researchtwin.net/join.html)
2. Register with your name, email, and research identifiers
3. Your Digital Twin is live immediately

### Local Node (Tier 1) — Full Control

```bash
git clone https://github.com/martinfrasch/researchtwin.git
cd researchtwin
pip install -r backend/requirements.txt
cp node_config.json.example node_config.json
# Edit node_config.json with your details
python run_node.py --config node_config.json
```

### Docker Deployment

```bash
cp .env.example .env  # Add your API keys
docker-compose up -d --build
```

**Required API keys**: `ANTHROPIC_API_KEY` (for Claude RAG)
**Optional**: `S2_API_KEY`, `GITHUB_TOKEN`, `DISCORD_BOT_TOKEN`, SMTP credentials

---

## Repository Structure

```
researchtwin/
├── backend/
│   ├── main.py              # FastAPI endpoints (REST + Discovery API)
│   ├── researchers.py        # SQLite researcher CRUD + token management
│   ├── database.py           # SQLite schema, WAL mode, migrations
│   ├── models.py             # Pydantic models for all endpoints
│   ├── rag.py                # RAG context assembly for Claude
│   ├── qic_index.py          # S-Index / QIC computation engine
│   ├── email_service.py      # SMTP service for profile update codes
│   ├── connectors/           # Data source connectors
│   │   ├── semantic_scholar.py
│   │   ├── scholarly_lib.py  # Google Scholar via scholarly
│   │   ├── github_connector.py
│   │   └── figshare.py
│   └── discord_bot/          # Discord bot with /research and /sindex
├── frontend/
│   ├── index.html            # Main dashboard with D3.js knowledge graph
│   ├── join.html             # Self-registration page
│   ├── update.html           # Email-verified profile updates
│   ├── privacy.html          # Privacy policy
│   └── widget-loader.js      # Embeddable chat widget
├── run_node.py               # Tier 1 local node launcher
├── node_config.json.example  # Local node configuration template
├── docker-compose.yml        # Docker orchestration
├── nginx/                    # Nginx reverse proxy + SSL
└── whitepaper.tex            # LaTeX manuscript
```

---

## Ecosystem

This repository is part of the **[ResearchTwin Ecosystem](https://github.com/users/martinfrasch/projects/8)** project:

| Repository | Description |
|------------|-------------|
| **[researchtwin](https://github.com/martinfrasch/researchtwin)** | Federated platform (this repo) |
| **[s-index](https://github.com/martinfrasch/s-index)** | S-Index formal specification and reference implementation |

---

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/API.md) | Full REST API documentation with schemas and examples |
| [Self-Hosting Guide](docs/SELF_HOSTING.md) | Tier 1 Local Node setup and configuration |
| [Hub Federation Guide](docs/HUB_FEDERATION.md) | Tier 2 Hub architecture and setup (planned) |
| [Security Policy](SECURITY.md) | Vulnerability reporting and security best practices |

---

## Contributing

Contributions welcome! See the [project board](https://github.com/users/martinfrasch/projects/8) for tracked issues.

- New connectors (ORCID enrichment, PubMed, OpenAlex)
- Affiliation-based geographic mapping
- MCP server for inter-agentic discovery
- UI/UX improvements
- Bug fixes and optimizations

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Contact

- **Platform**: [researchtwin.net](https://researchtwin.net)
- **Email**: martin@researchtwin.net
- **Issues**: [GitHub Issues](https://github.com/martinfrasch/researchtwin/issues)

---

*Empowering researchers and AI agents to discover, collaborate, and innovate together.*
