# ResearchTwin — Project Index

> Federated platform transforming publications, datasets, and code into conversational Digital Twins with the S-Index metric.

**Live**: [researchtwin.net](https://researchtwin.net) · **Repo**: [github.com/martinfrasch/researchtwin](https://github.com/martinfrasch/researchtwin) · **S-Index**: [github.com/martinfrasch/s-index](https://github.com/martinfrasch/s-index)

---

## Architecture (BGNO)

Three-layer design inspired by Bimodal Glial-Neural Optimization:

1. **Multi-Modal Connector Layer** — Pulls from Semantic Scholar, Google Scholar, GitHub, Figshare, ORCID
2. **Glial Layer** — Caching (24h TTL), rate limiting, context preparation, deduplication
3. **Neural Layer** — RAG with Perplexity/OpenAI for answer synthesis

Federated tiers: **Local Nodes** → **Hubs** → **Hosted Edges**

---

## Directory Structure

```
researchtwin/
├── backend/                    # FastAPI backend (Python 3.12)
│   ├── main.py                 # 877 lines — API endpoints, rate limiting, middleware
│   ├── rag.py                  # RAG pipeline: build_context(), chat_with_context(), chat_with_byok()
│   ├── qic_index.py            # S-Index v2: Quality × Impact × Collaboration scoring
│   ├── database.py             # SQLite schema, WAL mode, migrations
│   ├── researchers.py          # Researcher CRUD, slug generation, update tokens
│   ├── models.py               # Pydantic request/response models with validators
│   ├── cache.py                # File-based JSON cache with TTL (24h default)
│   ├── email_service.py        # SMTP email for verification codes
│   ├── geocoder.py             # Nominatim geocoding for affiliations
│   ├── discord_bot.py          # Discord slash commands (/research, /sindex)
│   ├── connectors/
│   │   ├── semantic_scholar.py # Author data + top papers (with retry on 429)
│   │   ├── google_scholar.py   # Scholar data via scholarly library (48h cache)
│   │   ├── github_connector.py # Repos, languages, stars (token auth)
│   │   ├── figshare.py         # Dataset search, fuzzy author matching, pagination
│   │   └── affiliations.py     # S2 + ORCID affiliation lookup (30d cache)
│   ├── requirements.txt
│   └── Dockerfile              # Python 3.12-slim, non-root, port 8000
│
├── frontend/                   # Static HTML/JS/CSS (dark theme)
│   ├── index.html              # Landing page: D3.js network graph, stats, researcher cards
│   ├── join.html               # Self-registration with LLM key funding option
│   ├── update.html             # Email-verified profile updates (6-digit code)
│   ├── chat-widget.html        # Embeddable chat: free/funded/BYOK adaptive modes
│   ├── embed.html              # Embeddable S-Index badge widget
│   ├── map.html                # Leaflet.js geographic researcher map
│   ├── privacy.html / terms.html
│   └── .well-known/            # ai-plugin.json, openapi.json (agent discovery)
│
├── mcp-server/                 # Model Context Protocol server for AI agents
│   └── server.py               # FastMCP tools: list_researchers, get_profile, search, etc.
│
├── nginx/
│   └── researchtwin-ssl.conf   # HTTPS proxy, rate limiting, security headers
│
├── docs/
│   ├── API.md                  # REST API reference
│   ├── SELF_HOSTING.md         # Tier 1 Local Node setup
│   ├── HUB_FEDERATION.md       # Tier 2 Hub architecture (planned)
│   └── PROJECT_INDEX.md        # ← This file
│
├── scripts/                    # Utilities (invitation email template, icon generator)
├── discord/                    # Discord bot how-to guide
├── docker-compose.yml          # Backend + Discord bot orchestration
├── whitepaper.tex              # S-Index v2 formal definition
├── s_index_v2_reference.py     # Standalone S-Index v2 reference implementation
├── run_node.py                 # Tier 1 Local Node launcher
└── README.md / CLAUDE.md / SECURITY.md
```

---

## API Endpoints (17 total)

### Chat (4 endpoints)

| Method | Path | Rate Limit | Description |
|--------|------|------------|-------------|
| `POST` | `/chat` | 30/hr IP, 150/day global | Server-funded chat via Perplexity |
| `POST` | `/chat/byok` | 10/hr IP | Bring-Your-Own-Key chat |
| `POST` | `/chat/free` | 5/day IP, 150/day global | Free tier (limited queries) |
| `POST` | `/chat/funded` | 10/hr IP | Researcher-funded (stored key) |

**Priority chain**: visitor BYOK key > researcher stored key > server free tier

### Context & Configuration

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/context/{slug}` | Full researcher data: S-Index, sources, scores |
| `GET` | `/api/chat-config/{slug}` | Available chat modes + remaining free queries |
| `GET` | `/api/researchers` | List all active researchers |
| `GET` | `/health` | Server health check |

### Registration & Profile

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/register` | Self-registration (honeypot protected) |
| `POST` | `/api/request-update` | Send 6-digit verification code to email |
| `PATCH` | `/api/researcher/{slug}` | Update profile (code-verified) |

### Discovery API (Schema.org typed, agent-optimized)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/researcher/{slug}/profile` | Schema.org Person |
| `GET` | `/api/researcher/{slug}/papers` | ScholarlyArticle ItemList |
| `GET` | `/api/researcher/{slug}/datasets` | Dataset ItemList with QIC scores |
| `GET` | `/api/researcher/{slug}/repos` | SoftwareSourceCode ItemList |
| `GET` | `/api/network/map` | Geocoded affiliations for all researchers |
| `GET` | `/api/discover` | Cross-researcher search (`?q=...&type=...`) |

---

## Database Schema

### `researchers` (primary)

| Column | Type | Constraint | Notes |
|--------|------|------------|-------|
| `slug` | TEXT | PRIMARY KEY | URL-safe, auto-generated from name |
| `display_name` | TEXT | NOT NULL | 2-100 chars |
| `email` | TEXT | NOT NULL, UNIQUE | RFC 5321 |
| `tier` | INTEGER | DEFAULT 3 | 1-3 |
| `status` | TEXT | DEFAULT 'active' | Only active returned |
| `semantic_scholar_id` | TEXT | DEFAULT '' | Numeric, ≤20 |
| `google_scholar_id` | TEXT | DEFAULT '' | Alphanumeric, ≤20 |
| `github_username` | TEXT | DEFAULT '' | GitHub format, ≤39 |
| `figshare_search_name` | TEXT | DEFAULT '' | ≤100 |
| `orcid` | TEXT | DEFAULT '' | XXXX-XXXX-XXXX-XXXX |
| `llm_api_key` | TEXT | DEFAULT '' | Hidden from public queries |
| `llm_provider` | TEXT | DEFAULT '' | 'perplexity' or 'openai' |
| `created_at` | TEXT | DEFAULT now() | Immutable |
| `updated_at` | TEXT | DEFAULT now() | Auto-updated |

### `update_tokens` (transient)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER | AUTOINCREMENT |
| `slug` | TEXT | FK → researchers |
| `token_hash` | TEXT | SHA256 of 6-digit code |
| `expires_at` | TEXT | 1 hour TTL |
| `attempts` | INTEGER | Max 5 per token |
| `used` | INTEGER | 0 or 1 |

---

## S-Index v2 Formula

### Per-Artifact Score

```
s_j = Q_j × I_j × C_j
```

| Component | Formula | Range | Description |
|-----------|---------|-------|-------------|
| **Quality (Q)** | `5 × gate × (1 + bonuses)` | {0} ∪ [5, 10] | FAIR gate: public AND licensed → 5, else 0. Bonuses: DOI (+0.5), docs (+0.3), format (+0.2) |
| **Impact (I)** | `1 + ln(1 + r/μ)` | [1, ∞) | Field-normalized log scaling. μ: dataset=50, code=10 |
| **Collaboration (C)** | `√(authors × institutions)` | [1, ∞) | Geometric mean of team breadth |

### Researcher Score

```
S_i = P + Σ s_j

P = h × (1 + log₁₀(c + 1))    (Paper Impact)
```

### Figshare Deduplication

Individual figures/supplements from the same paper are grouped before scoring:
1. **Title pattern**: "FIGURE N from...", "Additional file N of..." → group by parent title
2. **Author fingerprint**: Figure-type items with unique titles → group by sorted author list
3. **Best representative**: Highest reuse (downloads + views) kept from each group

---

## Deployment

**Server**: 94.130.225.75 (Hetzner) · **Domain**: researchtwin.net (Cloudflare DNS)

```bash
# Deploy
rsync -avz backend/ frontend/ docker-compose.yml root@94.130.225.75:/opt/researchtwin/
ssh root@94.130.225.75 'cd /opt/researchtwin && docker compose down && docker compose up -d --build'
```

**Docker services**: `researchtwin_backend` (FastAPI :8000), `researchtwin_discord_bot`
**Network**: `researchtwin-network` (shared with Nginx container)
**Nginx**: SSL termination, rate limiting, security headers for `researchtwin.net`

---

## Security

- **Rate limiting**: Per-IP sliding window (in-memory) + Nginx layer
- **Honeypot**: Hidden `website` field in registration (bot detection)
- **Token verification**: SHA256-hashed 6-digit codes, 5 attempt max, 1hr expiry
- **API key isolation**: `llm_api_key` excluded from `_FIELDS` tuple, never in public responses
- **Security headers**: CSP, HSTS, X-Frame-Options, XSS-Protection (via middleware + Nginx)
- **CORS**: Open for GET/POST/PATCH (public API by design)

---

## External Dependencies

| Service | Purpose | Auth |
|---------|---------|------|
| Semantic Scholar | Papers, citations, h-index | API key (env) |
| Google Scholar | i10-index, publications | scholarly library (no key) |
| GitHub | Repos, stars, languages | Token (env) |
| Figshare | Datasets, downloads, views | Public API |
| ORCID | Affiliations | Public API |
| Nominatim | Geocoding institutions | Public (1 req/s) |
| Perplexity | LLM for chat (server) | API key (env) |
| OpenAI | LLM for chat (BYOK option) | User-provided |

---

## Key Files Quick Reference

| Need to... | File |
|------------|------|
| Add an API endpoint | `backend/main.py` |
| Change S-Index formula | `backend/qic_index.py` |
| Add a data connector | `backend/connectors/` |
| Modify registration | `backend/models.py` + `backend/main.py` |
| Update landing page | `frontend/index.html` |
| Change chat widget behavior | `frontend/chat-widget.html` |
| Modify database schema | `backend/database.py` (add migration) |
| Update Nginx config | `nginx/researchtwin-ssl.conf` |
| Add MCP tool for agents | `mcp-server/server.py` |

---

*Generated 2026-02-12. See [API.md](API.md) for detailed endpoint documentation.*
