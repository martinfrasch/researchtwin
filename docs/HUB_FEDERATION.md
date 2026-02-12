# Hub Federation Guide (Tier 2)

> **Status**: Planned. This document describes the architecture and setup for Tier 2 Hubs, which aggregate multiple Tier 1 Local Nodes into a unified research group. The database schema and registration fields are in place; federation protocol implementation is upcoming.

---

## Overview

A **Hub** is a lab-level or department-level aggregator that federates multiple Tier 1 Local Nodes into a single discoverable unit. Think of it as a "Discord server for research" — a shared space where a research group's Digital Twins are accessible under one roof.

```
┌────────────────────────────────────────────────────┐
│                   Tier 3: Hosted Edge               │
│                 researchtwin.net                     │
│        (Global discovery, network map)               │
└───────────────┬──────────────────┬─────────────────┘
                │                  │
        ┌───────▼──────┐   ┌──────▼───────┐
        │  Tier 2: Hub │   │  Tier 2: Hub │
        │  Lab Alpha   │   │  Lab Beta    │
        └──┬───┬───┬───┘   └──┬───┬──────┘
           │   │   │          │   │
         ┌─▼─┐│ ┌─▼─┐      ┌─▼─┐│
         │T1 ││ │T1 │      │T1 ││
         │   ││ │   │      │   ││
         └───┘│ └───┘      └───┘│
              │                  │
            ┌─▼─┐              ┌─▼─┐
            │T1 │              │T1 │
            └───┘              └───┘
```

---

## Architecture

### What a Hub Does

1. **Aggregates researchers**: Multiple researchers register under one Hub, sharing infrastructure
2. **Proxies discovery API**: Agents querying the Hub get combined results from all member researchers
3. **Registers upstream**: The Hub registers itself with the Hosted Edge (Tier 3) for global discoverability
4. **Manages resources**: Shared caching, rate limiting, and API key management for the group

### Hub vs. Local Node vs. Hosted Edge

| Capability | Tier 1 (Local) | Tier 2 (Hub) | Tier 3 (Hosted) |
|-----------|----------------|--------------|-----------------|
| Researchers | 1 (self) | Multiple | Many |
| Data sovereignty | Full | Group-level | Platform-level |
| Discovery API | Own profile only | All members | All registered |
| Registration | Self or hub | Managed by hub admin | Self-service |
| Infrastructure | Own machine | Shared server | Cloud (researchtwin.net) |
| Chat (RAG) | Optional | Shared API key | Included |

---

## Setting Up a Hub

### Prerequisites

- A server or VM accessible to lab members (Linux recommended)
- Python 3.10+ or Docker
- Domain name (recommended) or static IP
- Anthropic API key (optional, for chat)
- SMTP credentials (for profile update verification)

### Step 1: Deploy the Backend

```bash
git clone https://github.com/martinfrasch/researchtwin.git
cd researchtwin

# Option A: Docker (recommended for production)
cp .env.example .env
# Edit .env with your API keys
docker compose up -d --build

# Option B: Direct Python
pip install -r backend/requirements.txt
python run_node.py --config hub_config.json
```

### Step 2: Configure as Hub

Create `hub_config.json`:

```json
{
  "display_name": "Hub Admin",
  "email": "admin@lab.university.edu",
  "tier": 2,
  "port": 8000,
  "register_with_hub": true,
  "hub_url": "https://researchtwin.net"
}
```

The key difference from a Tier 1 config is `"tier": 2`. This tells the Hosted Edge that this instance aggregates multiple researchers.

### Step 3: Register Lab Members

Each lab member registers through the Hub's `/api/register` endpoint or join page:

**Via join page**: Members visit `https://your-hub-domain/join.html` and fill in the registration form.

**Via API**:
```bash
curl -X POST https://your-hub-domain/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lab Member Name",
    "email": "member@university.edu",
    "tier": 2,
    "semantic_scholar_id": "12345678",
    "github_username": "member-gh"
  }'
```

**Via local node registration**: Members running Tier 1 nodes can register with the Hub instead of the global Hosted Edge:

```json
{
  "register_with_hub": true,
  "hub_url": "https://your-hub-domain"
}
```

### Step 4: Reverse Proxy (Production)

For production deployments, place the Hub behind Nginx with TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name hub.lab.university.edu;

    ssl_certificate     /etc/letsencrypt/live/hub.lab.university.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hub.lab.university.edu/privkey.pem;

    # Rate limit registration
    limit_req_zone $binary_remote_addr zone=register_limit:10m rate=1r/m;

    location = /api/register {
        limit_req zone=register_limit burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }

    location / {
        root /opt/researchtwin/frontend;
        try_files $uri $uri.html $uri/ =404;
    }
}
```

### Step 5: Register with the Hosted Edge

The Hub registers itself with `researchtwin.net` so its members appear on the global network map:

```bash
python run_node.py --config hub_config.json --register-hub
```

---

## Federation Protocol (Planned)

The federation protocol governs how Hubs communicate with the Hosted Edge and with each other. The following describes the target architecture.

### Discovery Proxying

When an agent queries the Hosted Edge's `/api/discover` endpoint, the Edge forwards the query to all registered Hubs. Each Hub returns results from its local researchers.

```
Agent → GET /api/discover?q=fetal → Hosted Edge
                                      ├→ Hub Alpha → [results from members]
                                      ├→ Hub Beta  → [results from members]
                                      └→ Local researchers → [results]
                                    ← Merged SearchResultSet
```

### Hub Registration Protocol

Hubs register with the Hosted Edge via the same `/api/register` endpoint, identified by `tier: 2`. The Edge stores the Hub's callback URL for federation queries.

```json
{
  "name": "Lab Alpha Hub",
  "email": "admin@lab-alpha.university.edu",
  "tier": 2,
  "callback_url": "https://hub.lab-alpha.university.edu/api"
}
```

### Health and Synchronization

- Hubs send periodic heartbeats to the Hosted Edge (`POST /api/hub/heartbeat`)
- The Edge tracks Hub availability and excludes unresponsive Hubs from federation queries
- Member counts and aggregate metrics are synced during heartbeats

### Data Flow

```
                    ┌─────────────────┐
                    │   Hosted Edge   │
                    │ (researchtwin.net)│
                    └───────┬─────────┘
                            │
              Heartbeat + sync (periodic)
                            │
                    ┌───────▼─────────┐
                    │      Hub        │
                    │  (university)   │
                    └───┬───┬───┬─────┘
                        │   │   │
              Live API fetch from S2/GH/FS
                        │   │   │
                    ┌───▼───▼───▼─────┐
                    │  Member Nodes   │
                    │  (researchers)  │
                    └─────────────────┘
```

Each Hub maintains its own SQLite database with its members' profiles. Data is fetched live from upstream APIs (Semantic Scholar, GitHub, Figshare) by the Hub on behalf of its members.

---

## Security Considerations

- **Access control**: Hub admins should restrict `/api/register` to trusted networks or require approval
- **API keys**: Store all API keys in `.env` with restricted permissions (`chmod 600 .env`)
- **TLS**: Always use HTTPS in production
- **Rate limiting**: Apply Nginx rate limits on registration and update endpoints
- **Database**: Restrict SQLite file permissions (`chmod 600 data/researchtwin.db`)

See [SECURITY.md](../SECURITY.md) for comprehensive security guidance.

---

## Roadmap

The following features are planned for the Hub federation tier:

- [ ] Hub heartbeat protocol (`POST /api/hub/heartbeat`)
- [ ] Federated discovery query forwarding
- [ ] Hub admin dashboard for member management
- [ ] Member approval workflow (invite-only registration)
- [ ] Aggregated S-Index computation across hub members
- [ ] Hub-to-Hub direct federation (bypassing Hosted Edge)
- [ ] ActivityPub integration for cross-platform federation

Track progress on the [project board](https://github.com/users/martinfrasch/projects/8).
