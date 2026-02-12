# Beyond the PDF: Why Every Researcher Needs a Conversational Digital Twin

![Header Image](/assets/pasted-image-67A7F4E7-FF4F-410B-A65A-B13B42EC5EED.png)
*The future of research isn't a library -- it's a conversation.*

## The Discovery Bottleneck

Science has a search problem. Every year, millions of papers, datasets, and code repositories enter the public record. The knowledge is out there, but finding it -- really finding it, in the sense of understanding how a dataset connects to a paper, how a codebase implements a method, who built on whose work -- remains brutally hard.

Traditional research dissemination still orbits around static PDFs and disconnected repositories. A paper lives on one platform. Its data sits on another. The code that produced the figures? Maybe on GitHub, maybe in a zip file buried in supplementary materials, maybe nowhere at all. For a human researcher trying to piece together the full picture, this fragmentation is exhausting. For an AI agent trying to do the same thing programmatically, it is nearly impossible.

I built [ResearchTwin](https://researchtwin.net) to fix that.

## What Is ResearchTwin?

ResearchTwin creates conversational digital twins of researchers. It pulls together everything a scientist has produced -- publications, code, datasets -- into a single, queryable profile backed by a language model that actually understands the context.

You can talk to it. Ask it about a researcher's most cited work, what programming languages they use, how their datasets have been reused, or how their h-index compares to their software impact. It answers in natural language, grounded in real data fetched in real time from four sources:

1. **Semantic Scholar** -- publications, citations, h-index
2. **Google Scholar** -- additional publications, i10-index (merged with Semantic Scholar results via title similarity matching using a SequenceMatcher threshold of 0.85 to deduplicate)
3. **GitHub** -- repositories, stars, forks, language distributions
4. **Figshare** -- datasets, views, downloads

The platform is live at [researchtwin.net](https://researchtwin.net) and fully open source at [github.com/martinfrasch/researchtwin](https://github.com/martinfrasch/researchtwin).

## The BGNO Architecture: Modeled After Biology

Under the hood, ResearchTwin runs on what I call a *Bimodal Glial-Neural Optimization (BGNO)* architecture, loosely inspired by how biological brains divide labor between glial cells and neurons.

![BGNO Architecture](/assets/pasted-image-91CB685F-069D-41F6-B037-B7689D17FA19.png)
*Bridging raw data and intelligent synthesis.*

The **Glial Layer** handles the unglamorous but essential work: data fetching, caching, rate limiting, and context preparation. A Multi-Modal Connector Layer fans out requests to all four data sources in parallel, so the system does not wait on one slow API before querying the next. Results are cached in SQLite (WAL mode) and shaped into structured context windows.

The **Neural Layer** takes that prepared context and runs retrieval-augmented generation (RAG) with Claude (`claude-sonnet-4-5-20250929`) to produce contextual, grounded answers. Because the Glial Layer has already done the heavy lifting of fetching, deduplicating, and organizing the data, the Neural Layer can focus entirely on reasoning and synthesis.

This separation keeps the system fast, economical, and maintainable. The Glial Layer can evolve independently -- adding new data sources, improving caching strategies -- without touching the reasoning pipeline.

## The S-Index: Measuring What Actually Matters

The h-index was a reasonable metric for the paper era. But modern research output includes code that gets starred and forked, datasets that get downloaded and reused, and collaborative networks that span institutions. A single citation count misses most of this.

The **S-Index** (formalized at [github.com/martinfrasch/S-index](https://github.com/martinfrasch/S-index)) is a real-time, multi-modal impact metric built on a QIC framework: **Quality x Impact x Collaboration**.

Each research object -- paper, dataset, or repository -- receives a per-object score:

> **s_j = Q x I x C**

The three components break down as follows:

**Quality (Q)** uses FAIR-based scoring:

> Q = 0.3 x F + 0.3 x A + 0.2 x I + 0.2 x R

where Findability, Accessibility, Interoperability, and Reusability are each scored 0--10.

**Impact (I)** captures reuse on a logarithmic scale:

> I = 1 + ln(1 + reuse_events)

**Collaboration (C)** rewards breadth of teamwork:

> C = (1 + ln(N_authors)) x (1 + 0.5 x ln(N_institutions))

The researcher-level S-Index aggregates across all output types:

> S-Index = paper_impact + sum(dataset QIC scores) + sum(repo QIC scores)

where `paper_impact = h_index x (1 + log10(citation_count + 1))`.

The result is a single number that reflects the full scope of a researcher's contributions -- not just how many times their PDFs were cited, but how much their code, data, and collaborative reach actually matter.

## The Federated Vision: Research Discovery Like Discord

Centralized platforms create single points of failure and control. ResearchTwin takes a different path, borrowing its topology from Discord's server model:

**Tier 1: Local Nodes** -- Any researcher can run their own instance using `run_node.py`. Your data stays on your machine. You control what is shared and what stays private. This is the self-hosted option for those who want full sovereignty.

**Tier 2: Hubs** -- Lab-level aggregators that connect multiple local nodes, enabling inter-lab discovery without centralizing data. Think of these as department or consortium servers. (Coming soon.)

**Tier 3: Hosted Edge** -- Zero-setup profiles on [researchtwin.net](https://researchtwin.net). Register through the join page, and the platform handles everything. This is the path of least resistance for researchers who want a digital twin without running infrastructure.

This three-tier model preserves data ownership while enabling discovery at every scale, from a single PI's website to a cross-institutional research network.

## The Inter-Agentic Discovery API

Here is where ResearchTwin looks forward. The platform exposes a Schema.org-typed REST API designed not just for humans, but for other AI agents to consume programmatically.

**Profile endpoint:**
`GET /api/researcher/{slug}/profile` returns a `@type: Person` object with HATEOAS links to all related resources.

**Publications:**
`GET /api/researcher/{slug}/papers` returns a `@type: ItemList` of `ScholarlyArticle` objects.

**Datasets:**
`GET /api/researcher/{slug}/datasets` returns a `@type: ItemList` of `Dataset` objects, each annotated with its QIC score.

**Repositories:**
`GET /api/researcher/{slug}/repos` returns a `@type: ItemList` of `SoftwareSourceCode` objects, also with QIC scores.

**Cross-researcher discovery:**
`GET /api/discover?q=keyword&type=paper|dataset|repo` searches across all registered researchers.

Every response uses Schema.org vocabulary and includes navigational links, so an AI agent can crawl the network, discover researchers by topic, and drill into their specific contributions -- all without scraping or guessing at page structure. This is the foundation for a web where research agents talk to research agents.

## The Frontend: Knowledge as a Graph

The interactive frontend renders each researcher's output as a force-directed knowledge graph built with D3.js. Papers, repositories, and datasets appear as interconnected nodes, with edges representing citations, code dependencies, and data lineage. A real-time S-Index dashboard breaks down impact by source, and the entire interface runs in a dark theme designed for extended reading.

For researchers who want to embed the experience on their own sites, ResearchTwin provides a chat widget that can be dropped into any webpage -- giving visitors a conversational interface to a researcher's full body of work.

Discord integration rounds out the access points: the `/research` command handles conversational queries, and `/sindex` returns real-time impact reports, both directly in your lab's Discord server.

## MCP Server: Plug ResearchTwin Into Any AI Agent

The Model Context Protocol (MCP) is an emerging standard for connecting AI assistants to external tools and data sources. ResearchTwin ships an official MCP server — registered in the [MCP Registry](https://registry.modelcontextprotocol.io) as `io.github.martinfrasch/researchtwin` — that exposes all discovery capabilities as structured tools.

Install it from PyPI:

```bash
pip install mcp-server-researchtwin
```

Or run it directly with `uvx`:

```bash
uvx mcp-server-researchtwin
```

The server exposes eight tools over stdio transport:

- **list_researchers** — find all registered researchers in the network
- **get_profile / get_context** — retrieve researcher profiles with S-Index metrics
- **get_papers / get_datasets / get_repos** — drill into publications, datasets, and code
- **discover** — cross-researcher keyword search across all artifact types
- **get_network_map** — geographic affiliation data for the entire network

Add it to Claude Desktop's configuration and your AI assistant can autonomously discover researchers, explore their publications, compare impact metrics, and find collaboration opportunities — all through natural conversation. This is the inter-agentic discovery vision made concrete: AI agents talking to research twins.

## Getting Started: Three Paths

**Path 1 -- Self-host a Local Node.** Clone the [repository](https://github.com/martinfrasch/researchtwin), configure your API keys, and run `run_node.py`. The stack is FastAPI, SQLite, and Docker Compose, fronted by Nginx with rate limiting and security headers. A Hetzner VPS at roughly $20/month handles it comfortably.

**Path 2 -- Join the hosted network.** Visit [researchtwin.net/join.html](https://researchtwin.net/join.html) and use the three-tier selector to register. The form uses honeypot anti-spam, Pydantic validation, and rate limiting. Once registered, you can update your profile anytime through email-verified codes at [researchtwin.net/update.html](https://researchtwin.net/update.html).

**Path 3 -- Wait for Hubs.** If you are a lab manager or department head interested in running a Tier 2 aggregator for your group, the hub architecture is under active development. Reach out through GitHub issues to shape the design.

## Join the Network

ResearchTwin is not a product pitch. It is an open-source bet that research discovery should be conversational, federated, and machine-readable from the ground up. The code is public. The API is documented. The S-Index formalization is its own repository.

If your work involves papers, code, and data -- and whose doesn't, at this point -- you have a digital twin waiting to be built.

**Try the live platform:** [researchtwin.net](https://researchtwin.net)

**Explore the source:** [github.com/martinfrasch/researchtwin](https://github.com/martinfrasch/researchtwin)

**Read the S-Index spec:** [github.com/martinfrasch/S-index](https://github.com/martinfrasch/S-index)

**Install the MCP server:** `pip install mcp-server-researchtwin` ([PyPI](https://pypi.org/project/mcp-server-researchtwin/) | [MCP Registry](https://registry.modelcontextprotocol.io))

![Dual Discovery](/assets/pasted-image-498CE811-D1E6-46FD-9B33-B78FCB89EF3E.png)
*Empowering human and AI agents to collaborate and discover.*
