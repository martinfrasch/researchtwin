# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ResearchTwin** is a federated platform that transforms a researcher's publications, datasets, and code repositories into a conversational Digital Twin. Inspired by Bimodal Glial-Neural Optimization (BGNO), it uses a dual-discovery pathway where humans and AI agents collaborate for scientific discovery.

This repository also serves as an **Obsidian vault** (`.obsidian/` config present).

## Current State

The project is early-stage. Most files are placeholders (`tier2_local_node.py`, `install-edge.sh`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `LICENSE`). The two substantive files are:

- `discord_bot.py` — Discord bot with `/research` and `/sindex` slash commands using discord.py
- `docker-compose.yml` — Three-service orchestration (backend, discord_bot, nginx)

The `backend/` and `frontend/` directories referenced in README.md do not exist yet. A deprecated Node.js version is archived in `my_research_node_deprecated.zip`.

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

Services: backend (FastAPI on port 8000), discord_bot (depends on backend), nginx (ports 80/443).

## Tech Stack

- **Backend**: Python, FastAPI
- **Bot**: discord.py with app_commands (slash commands)
- **Proxy**: Nginx
- **Infra**: Docker Compose
- **External APIs**: Semantic Scholar, GitHub, Figshare, Discord

## Key Concept: S-index

A real-time impact metric combining citations, code utility, and data reuse — exposed via the `/sindex` Discord command and the `/api/context/{slug}` API endpoint.
