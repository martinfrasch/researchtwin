# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ResearchTwin** is a federated platform that transforms a researcher's publications, datasets, and code repositories into a conversational Digital Twin. Inspired by Bimodal Glial-Neural Optimization (BGNO), it uses a dual-discovery pathway where humans and AI agents collaborate for scientific discovery.

This repository also serves as an **Obsidian vault** (`.obsidian/` is gitignored).

## Architecture (BGNO)

Three-layer design:

1. **Multi-Modal Connector Layer** — Pulls data from Semantic Scholar (publications), GitHub (code), Figshare (datasets)
2. **Glial Layer** — Caching, rate limiting, context preparation
3. **Neural Layer** — RAG with RouteLLM API for answer synthesis

Federated network tiers: **Local Nodes** (individual researchers) → **Hubs** (lab aggregators) → **Hosted Edges** (cloud analytics)

## Build & Run

```bash
# Requires .env with: SEMANTIC_SCHOLAR_API_KEY, GITHUB_TOKEN, FIGSHARE_TOKEN, DISCORD_BOT_TOKEN
docker-compose up -d --build
```

Services:
- `researchtwin_backend` — FastAPI on port 8000 (exposed only within Docker network)
- `researchtwin_discord_bot` — Discord bot, starts after backend is healthy

## Deployment

Deployed on Hetzner `94.130.225.75` alongside other services (SefarAI, PPD). The existing Nginx reverse proxy handles SSL and routing for `researchtwin.net`. ResearchTwin runs on its own `researchtwin-network` Docker network.

Key files for deployment:
- `nginx/researchtwin-ssl.conf` — Drop into the hetzner-deployment `nginx/conf.d/` directory
- The existing Nginx container must join `researchtwin-network` to proxy to the backend

## Tech Stack

- **Backend**: Python 3.12, FastAPI, uvicorn
- **Bot**: discord.py with app_commands (slash commands)
- **Proxy**: Nginx (shared with hetzner-deployment)
- **Infra**: Docker Compose
- **External APIs**: Semantic Scholar, GitHub, Figshare, Discord

## API Endpoints

- `POST /chat` — Chat with a researcher's digital twin (body: `{message, researcher_slug}`)
- `GET /api/context/{slug}` — Get researcher context and S-index
- `GET /health` — Health check

## Key Concept: S-index

A real-time impact metric combining citations, code utility, and data reuse — exposed via the `/sindex` Discord command and the `/api/context/{slug}` API endpoint.
