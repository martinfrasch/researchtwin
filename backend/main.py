import asyncio
import logging
import os
import re
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from difflib import SequenceMatcher

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

import database
import researchers
from connectors import fetch_author_data, fetch_github_data, fetch_figshare_data, fetch_scholar_data, fetch_affiliations
from models import RegisterRequest, RegisterResponse, RequestUpdateRequest, ProfileUpdateRequest, ProfileUpdateResponse
from qic_index import compute_researcher_qic
from rag import build_context, chat_with_context, chat_with_byok

logger = logging.getLogger("researchtwin")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# In-memory rate limiter (defense-in-depth behind nginx)
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple sliding-window rate limiter. No external dependencies."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        hits = self._hits[key] = [t for t in self._hits[key] if t > cutoff]
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True


# Per-IP: 30 chat requests per hour
_chat_ip_limiter = RateLimiter(max_requests=30, window_seconds=3600)
# Global: 150 chat requests per day (cost cap ~$5/day with Perplexity sonar)
_chat_daily_limiter = RateLimiter(max_requests=150, window_seconds=86400)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    # Attach to uvicorn's handler (available now that uvicorn is running)
    uvicorn_logger = logging.getLogger("uvicorn")
    for h in uvicorn_logger.handlers:
        logger.addHandler(h)
    logger.info("ResearchTwin rate limits active: %d/hr per IP, %d/day global",
                _chat_ip_limiter.max_requests, _chat_daily_limiter.max_requests)
    yield
    database.close_db()


# Disable docs in production
docs_url = "/docs" if os.environ.get("ENV") == "dev" else None
redoc_url = "/redoc" if os.environ.get("ENV") == "dev" else None

app = FastAPI(
    title="ResearchTwin API", version="0.3.0",
    docs_url=docs_url, redoc_url=redoc_url, lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{0,126}[a-z0-9]$')


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    researcher_slug: str = Field(..., min_length=1, max_length=128)

    @field_validator('researcher_slug')
    @classmethod
    def validate_slug(cls, v):
        if not SLUG_RE.match(v):
            raise ValueError('Invalid slug format')
        return v


class ChatResponse(BaseModel):
    reply: str
    researcher_slug: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_title(title: str) -> str:
    """Normalize a paper title for comparison."""
    t = title.lower().strip()
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t)
    return t


def _merge_s2_gs(s2_data: dict, gs_data: dict) -> dict:
    """Merge Semantic Scholar and Google Scholar data.

    S2 is primary. GS supplements with papers not found in S2
    and provides i10_index. Author-level metrics use max(S2, GS).
    """
    if "_error" in gs_data:
        s2_data["i10_index"] = 0
        s2_data["_sources"] = ["semantic_scholar"]
        return s2_data

    if "_error" in s2_data:
        return {
            "name": gs_data.get("name", ""),
            "paper_count": gs_data.get("paper_count", 0),
            "citation_count": gs_data.get("citation_count", 0),
            "h_index": gs_data.get("h_index", 0),
            "i10_index": gs_data.get("i10_index", 0),
            "top_papers": gs_data.get("publications", [])[:20],
            "_sources": ["google_scholar"],
        }

    # Both sources available — merge papers
    s2_papers = list(s2_data.get("top_papers", []))
    gs_papers = gs_data.get("publications", [])

    s2_normalized = [_normalize_title(p["title"]) for p in s2_papers]

    for gs_paper in gs_papers:
        gs_norm = _normalize_title(gs_paper["title"])
        if len(gs_norm) < 10:
            continue

        matched = False
        for i, s2_norm in enumerate(s2_normalized):
            ratio = SequenceMatcher(None, gs_norm, s2_norm).ratio()
            if ratio > 0.85:
                s2_papers[i]["citations"] = max(
                    s2_papers[i].get("citations", 0),
                    gs_paper.get("citations", 0),
                )
                matched = True
                break

        if not matched:
            s2_papers.append({
                "title": gs_paper["title"],
                "year": gs_paper.get("year"),
                "citations": gs_paper.get("citations", 0),
                "url": "",
                "source": "google_scholar",
            })

    s2_papers.sort(key=lambda p: p.get("citations", 0), reverse=True)

    return {
        "name": s2_data.get("name", "") or gs_data.get("name", ""),
        "paper_count": len(s2_papers),
        "citation_count": max(
            s2_data.get("citation_count", 0),
            gs_data.get("citation_count", 0),
        ),
        "h_index": max(
            s2_data.get("h_index", 0),
            gs_data.get("h_index", 0),
        ),
        "i10_index": gs_data.get("i10_index", 0),
        "top_papers": s2_papers[:20],
        "_sources": ["semantic_scholar", "google_scholar"],
    }


_EMPTY_S2 = {"name": "", "paper_count": 0, "citation_count": 0, "h_index": 0, "top_papers": [], "_error": "no_id"}
_EMPTY_GH = {"total_repos": 0, "total_stars": 0, "top_repos": [], "languages": {}, "_error": "no_id"}
_EMPTY_FS = {"total_datasets": 0, "total_downloads": 0, "total_views": 0, "articles": [], "_error": "no_id"}
_EMPTY_GS = {"name": "", "citation_count": 0, "h_index": 0, "i10_index": 0, "paper_count": 0, "publications": [], "_error": "no_id"}


async def _empty(default: dict) -> dict:
    return default


async def _fetch_all(researcher: dict) -> tuple[dict, dict, dict]:
    """Fetch data from all four sources in parallel. Merge S2+GS. Gracefully handle failures."""
    s2_id = researcher.get("semantic_scholar_id", "")
    gh_user = researcher.get("github_username", "")
    fs_name = researcher.get("figshare_search_name", "")
    gs_id = researcher.get("google_scholar_id", "")

    s2_task = fetch_author_data(s2_id) if s2_id else _empty(_EMPTY_S2)
    gh_task = fetch_github_data(gh_user) if gh_user else _empty(_EMPTY_GH)
    fs_task = fetch_figshare_data(fs_name) if fs_name else _empty(_EMPTY_FS)
    gs_task = fetch_scholar_data(gs_id) if gs_id else _empty(_EMPTY_GS)

    results = await asyncio.gather(s2_task, gh_task, fs_task, gs_task, return_exceptions=True)

    s2_data = results[0] if not isinstance(results[0], Exception) else {
        "name": researcher.get("display_name", ""), "paper_count": 0, "citation_count": 0,
        "h_index": 0, "top_papers": [], "_error": str(results[0]),
    }
    gh_data = results[1] if not isinstance(results[1], Exception) else {
        "total_repos": 0, "total_stars": 0, "top_repos": [], "languages": {},
        "_error": str(results[1]),
    }
    fs_data = results[2] if not isinstance(results[2], Exception) else {
        "total_datasets": 0, "total_downloads": 0, "total_views": 0, "articles": [],
        "_error": str(results[2]),
    }
    gs_data = results[3] if not isinstance(results[3], Exception) else {
        "name": "", "citation_count": 0, "h_index": 0, "i10_index": 0,
        "paper_count": 0, "publications": [], "_error": str(results[3]),
    }

    merged_academic = _merge_s2_gs(s2_data, gs_data)
    return merged_academic, gh_data, fs_data


def _validate_slug(slug: str):
    if not SLUG_RE.match(slug):
        raise HTTPException(status_code=400, detail="Invalid slug format")


def _get_researcher_or_404(slug: str) -> dict:
    _validate_slug(slug)
    try:
        return researchers.get_researcher(slug)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown researcher")


# ---------------------------------------------------------------------------
# Core endpoints
# ---------------------------------------------------------------------------

@app.get("/api/researchers")
def list_researchers():
    """Return available researchers with display names."""
    result = []
    for slug in researchers.list_slugs():
        r = researchers.get_researcher(slug)
        result.append({"slug": slug, "display_name": r["display_name"]})
    return {"researchers": result}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    client_ip = request.headers.get("x-real-ip", request.client.host if request.client else "unknown")

    # Global daily budget (prevents runaway API costs)
    if not _chat_daily_limiter.is_allowed("__global__"):
        logger.warning("chat DAILY_LIMIT_HIT ip=%s", client_ip)
        raise HTTPException(status_code=503, detail="Daily chat limit reached. Try again tomorrow.")

    # Per-IP hourly limit
    if not _chat_ip_limiter.is_allowed(client_ip):
        logger.warning("chat RATE_LIMITED ip=%s slug=%s", client_ip, req.researcher_slug)
        raise HTTPException(status_code=429, detail="Too many chat requests. Try again later.")

    try:
        researcher = researchers.get_researcher(req.researcher_slug)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown researcher")

    if not os.environ.get("PERPLEXITY_API_KEY"):
        raise HTTPException(status_code=503, detail="Chat unavailable — no API key configured")

    logger.info("chat ip=%s slug=%s msg_len=%d", client_ip, req.researcher_slug, len(req.message))

    try:
        s2_data, gh_data, fs_data = await _fetch_all(researcher)
        qic = compute_researcher_qic(fs_data, gh_data, s2_data)
        context = build_context(researcher["display_name"], s2_data, gh_data, fs_data, qic)
        reply = await chat_with_context(context, req.message, researcher["display_name"])
    except asyncio.TimeoutError:
        logger.error("chat TIMEOUT ip=%s slug=%s", client_ip, req.researcher_slug)
        raise HTTPException(status_code=504, detail="Chat request timed out")
    except Exception:
        logger.exception("chat PIPELINE_ERROR ip=%s slug=%s", client_ip, req.researcher_slug)
        raise HTTPException(status_code=502, detail="Pipeline error")

    return ChatResponse(reply=reply, researcher_slug=req.researcher_slug)


# ---------------------------------------------------------------------------
# BYOK (Bring Your Own Key) chat — for embeddable widget
# ---------------------------------------------------------------------------

class BYOKChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    researcher_slug: str = Field(..., min_length=1, max_length=128)
    api_key: str = Field(..., min_length=1, max_length=256)
    provider: str = Field(default="perplexity")
    model: str = Field(default="")

    @field_validator('researcher_slug')
    @classmethod
    def validate_byok_slug(cls, v):
        if not SLUG_RE.match(v):
            raise ValueError('Invalid slug format')
        return v

    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        from rag import LLM_PROVIDERS
        if v not in LLM_PROVIDERS:
            raise ValueError(f'Unsupported provider. Choose from: {", ".join(LLM_PROVIDERS)}')
        return v


# Per-IP: 10 BYOK requests per hour (no server API cost, but still uses compute)
_byok_ip_limiter = RateLimiter(max_requests=10, window_seconds=3600)


@app.post("/chat/byok", response_model=ChatResponse)
async def chat_byok(req: BYOKChatRequest, request: Request):
    client_ip = request.headers.get("x-real-ip", request.client.host if request.client else "unknown")

    if not _byok_ip_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")

    try:
        researcher = researchers.get_researcher(req.researcher_slug)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown researcher")

    logger.info("byok ip=%s slug=%s provider=%s msg_len=%d",
                client_ip, req.researcher_slug, req.provider, len(req.message))

    try:
        s2_data, gh_data, fs_data = await _fetch_all(researcher)
        qic = compute_researcher_qic(fs_data, gh_data, s2_data)
        context = build_context(researcher["display_name"], s2_data, gh_data, fs_data, qic)
        reply = await chat_with_byok(
            context, req.message, researcher["display_name"],
            api_key=req.api_key, provider=req.provider, model=req.model,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "invalid" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid API key")
        logger.exception("byok PIPELINE_ERROR ip=%s slug=%s", client_ip, req.researcher_slug)
        raise HTTPException(status_code=502, detail="Pipeline error")

    return ChatResponse(reply=reply, researcher_slug=req.researcher_slug)


@app.get("/api/context/{slug}")
async def get_context(slug: str):
    researcher = _get_researcher_or_404(slug)

    merged_data, gh_data, fs_data = await _fetch_all(researcher)
    qic = compute_researcher_qic(fs_data, gh_data, merged_data)

    def _source_status(data, name):
        if "_error" in data:
            return {"status": "error", "error": data["_error"][:100]}
        return {"status": "connected"}

    # Academic sources — merged data has _sources field
    academic_sources = merged_data.get("_sources", [])
    s2_info = {"status": "connected"} if "semantic_scholar" in academic_sources else {"status": "error", "error": "Semantic Scholar unavailable"}
    s2_info.update({"paper_count": merged_data.get("paper_count", 0), "citation_count": merged_data.get("citation_count", 0), "h_index": merged_data.get("h_index", 0)})

    gs_info = {"status": "connected"} if "google_scholar" in academic_sources else {"status": "error", "error": "Google Scholar unavailable"}
    gs_info.update({"i10_index": merged_data.get("i10_index", 0)})

    gh_info = _source_status(gh_data, "github")
    gh_info.update({"total_repos": gh_data.get("total_repos", 0), "total_stars": gh_data.get("total_stars", 0)})

    fs_info = _source_status(fs_data, "figshare")
    fs_info.update({"total_datasets": fs_data.get("total_datasets", 0), "total_downloads": fs_data.get("total_downloads", 0)})

    return {
        "researcher_slug": slug,
        "display_name": researcher["display_name"],
        "s_index": qic["s_index"],
        "paper_impact": qic["paper_impact"],
        "summary": qic["summary"],
        "sources": {
            "semantic_scholar": s2_info,
            "google_scholar": gs_info,
            "github": gh_info,
            "figshare": fs_info,
        },
        "dataset_scores": qic.get("dataset_scores", []),
        "repo_scores": qic.get("repo_scores", [])[:5],
    }


# ---------------------------------------------------------------------------
# Registration endpoint
# ---------------------------------------------------------------------------

@app.post("/api/register", response_model=RegisterResponse)
async def register(req: RegisterRequest):
    # Honeypot — bots fill hidden field, humans never see it
    if req.website:
        return RegisterResponse(
            slug="processing", display_name=req.name,
            tier=req.tier, message="Registration received.",
        )

    # Duplicate email check
    existing = researchers.get_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    slug = researchers.generate_slug(req.name)

    researchers.create_researcher(
        slug=slug,
        display_name=req.name,
        email=req.email,
        tier=req.tier,
        semantic_scholar_id=req.semantic_scholar_id,
        google_scholar_id=req.google_scholar_id,
        github_username=req.github_username,
        figshare_search_name=req.figshare_search_name or "",
        orcid=req.orcid,
    )

    return RegisterResponse(
        slug=slug, display_name=req.name, tier=req.tier,
        message=f"Welcome to ResearchTwin! Your profile is live at /?researcher={slug}",
    )


# ---------------------------------------------------------------------------
# Profile update endpoints
# ---------------------------------------------------------------------------

@app.post("/api/request-update")
async def request_update(req: RequestUpdateRequest):
    """Send a 6-digit verification code to the researcher's registered email."""
    slug = req.slug.lower().strip()
    _validate_slug(slug)

    try:
        researcher = researchers.get_researcher(slug)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown researcher")

    # Verify email matches the one on file
    stored = researchers.get_by_email(req.email)
    if not stored or stored["slug"] != slug:
        raise HTTPException(status_code=403, detail="Email does not match this profile")

    # Rate limit: max 3 codes per hour per slug
    if researchers.count_recent_tokens(slug) >= 3:
        raise HTTPException(status_code=429, detail="Too many requests. Try again later.")

    code = researchers.create_update_token(slug)

    from email_service import send_update_code
    send_update_code(req.email, slug, code)

    return {"message": "Verification code sent to your email."}


@app.patch("/api/researcher/{slug}", response_model=ProfileUpdateResponse)
async def update_profile(slug: str, req: ProfileUpdateRequest):
    """Update researcher profile fields after verifying the emailed code."""
    slug = slug.lower().strip()
    if slug != req.slug.lower().strip():
        raise HTTPException(status_code=400, detail="Slug mismatch")
    _validate_slug(slug)

    # Verify researcher exists
    try:
        researchers.get_researcher(slug)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown researcher")

    # Verify the code
    if not researchers.verify_update_token(slug, req.code):
        raise HTTPException(status_code=403, detail="Invalid or expired code")

    # Apply updates (only non-empty fields override)
    updates = {}
    for field in ("semantic_scholar_id", "google_scholar_id", "github_username",
                  "figshare_search_name", "orcid"):
        val = getattr(req, field)
        if val:  # only update if provided
            updates[field] = val

    if updates:
        researchers.update_researcher(slug, **updates)

    return ProfileUpdateResponse(
        slug=slug,
        message=f"Profile updated successfully. {len(updates)} field(s) changed.",
    )


# ---------------------------------------------------------------------------
# Inter-agentic discovery API
# ---------------------------------------------------------------------------

@app.get("/api/researcher/{slug}/profile")
async def researcher_profile(slug: str):
    """Machine-readable researcher profile for agent discovery."""
    researcher = _get_researcher_or_404(slug)
    s2_data, gh_data, fs_data = await _fetch_all(researcher)
    qic = compute_researcher_qic(fs_data, gh_data, s2_data)

    return {
        "@type": "Person",
        "slug": slug,
        "name": researcher["display_name"],
        "orcid": researcher.get("orcid", ""),
        "s_index": qic["s_index"],
        "paper_impact": qic["paper_impact"],
        "summary": qic["summary"],
        "resources": {
            "papers": f"/api/researcher/{slug}/papers",
            "datasets": f"/api/researcher/{slug}/datasets",
            "repos": f"/api/researcher/{slug}/repos",
        },
    }


@app.get("/api/researcher/{slug}/papers")
async def researcher_papers(slug: str):
    """Papers with citation data for agent consumption."""
    researcher = _get_researcher_or_404(slug)
    s2_data, gh_data, fs_data = await _fetch_all(researcher)

    papers = s2_data.get("top_papers", [])
    return {
        "@type": "ItemList",
        "researcher": slug,
        "total": len(papers),
        "items": [
            {
                "@type": "ScholarlyArticle",
                "title": p.get("title", ""),
                "year": p.get("year"),
                "citations": p.get("citations", 0),
                "url": p.get("url", ""),
            }
            for p in papers
        ],
    }


@app.get("/api/researcher/{slug}/datasets")
async def researcher_datasets(slug: str):
    """Datasets with QIC scores for agent consumption."""
    researcher = _get_researcher_or_404(slug)
    s2_data, gh_data, fs_data = await _fetch_all(researcher)
    qic = compute_researcher_qic(fs_data, gh_data, s2_data)

    return {
        "@type": "ItemList",
        "researcher": slug,
        "total": fs_data.get("total_datasets", 0),
        "items": [
            {
                "@type": "Dataset",
                "title": ds.get("title", ""),
                "quality": ds.get("quality", 0),
                "impact": ds.get("impact", 0),
                "collaboration": ds.get("collaboration", 0),
                "s_score": ds.get("score", 0),
                "fair_gate": ds.get("fair_gate", False),
            }
            for ds in qic.get("dataset_scores", [])
        ],
    }


@app.get("/api/researcher/{slug}/repos")
async def researcher_repos(slug: str):
    """Repos with QIC scores for agent consumption."""
    researcher = _get_researcher_or_404(slug)
    s2_data, gh_data, fs_data = await _fetch_all(researcher)
    qic = compute_researcher_qic(fs_data, gh_data, s2_data)

    return {
        "@type": "ItemList",
        "researcher": slug,
        "total": gh_data.get("total_repos", 0),
        "items": [
            {
                "@type": "SoftwareSourceCode",
                "name": repo.get("title", ""),
                "quality": repo.get("quality", 0),
                "impact": repo.get("impact", 0),
                "collaboration": repo.get("collaboration", 0),
                "s_score": repo.get("score", 0),
                "fair_gate": repo.get("fair_gate", False),
            }
            for repo in qic.get("repo_scores", [])
        ],
    }


@app.get("/api/network/map")
async def network_map():
    """Return geocoded affiliations for all active researchers."""
    import geocoder

    researchers_list = []
    for slug in researchers.list_slugs():
        researcher = researchers.get_researcher(slug)
        s2_id = researcher.get("semantic_scholar_id", "")
        orcid = researcher.get("orcid", "")

        if not s2_id and not orcid:
            continue

        affiliations = await fetch_affiliations(s2_id, orcid)
        if not affiliations:
            continue

        geocoded = []
        for aff in affiliations:
            coords = await geocoder.geocode_affiliation(aff)
            if coords:
                geocoded.append({
                    "institution": aff["institution"],
                    "city": aff.get("city", ""),
                    "country": aff.get("country", ""),
                    "current": aff.get("current", False),
                    "lat": coords["lat"],
                    "lng": coords["lng"],
                })

        if geocoded:
            researchers_list.append({
                "slug": slug,
                "name": researcher["display_name"],
                "affiliations": geocoded,
            })

    return {
        "@type": "NetworkMap",
        "total_researchers": len(researchers_list),
        "researchers": researchers_list,
    }


@app.get("/api/discover")
async def discover(
    q: str = Query(..., min_length=2, max_length=200),
    type: str = Query(default="", pattern="^(dataset|repo|paper|)$"),
):
    """Cross-researcher search for agent-driven discovery."""
    q_lower = q.lower()
    results = []

    for slug in researchers.list_slugs():
        researcher = researchers.get_researcher(slug)
        try:
            s2_data, gh_data, fs_data = await _fetch_all(researcher)
            qic = compute_researcher_qic(fs_data, gh_data, s2_data)
        except Exception:
            continue

        researcher_name = researcher["display_name"]

        # Search papers
        if type in ("", "paper"):
            for p in s2_data.get("top_papers", []):
                title = p.get("title", "")
                if q_lower in title.lower():
                    results.append({
                        "@type": "ScholarlyArticle",
                        "title": title,
                        "year": p.get("year"),
                        "citations": p.get("citations", 0),
                        "researcher": researcher_name,
                        "researcher_slug": slug,
                    })

        # Search datasets
        if type in ("", "dataset"):
            for ds in qic.get("dataset_scores", []):
                title = ds.get("title", "")
                if q_lower in title.lower():
                    results.append({
                        "@type": "Dataset",
                        "title": title,
                        "s_score": ds.get("score", 0),
                        "researcher": researcher_name,
                        "researcher_slug": slug,
                    })

        # Search repos
        if type in ("", "repo"):
            for repo in qic.get("repo_scores", []):
                title = repo.get("title", "")
                if q_lower in title.lower():
                    results.append({
                        "@type": "SoftwareSourceCode",
                        "name": title,
                        "s_score": repo.get("score", 0),
                        "researcher": researcher_name,
                        "researcher_slug": slug,
                    })

    # Sort by relevance (title/name match first, then by score)
    results.sort(key=lambda r: r.get("s_score", r.get("citations", 0)), reverse=True)

    return {
        "@type": "SearchResultSet",
        "query": q,
        "type_filter": type or "all",
        "total": len(results),
        "results": results[:50],
    }
