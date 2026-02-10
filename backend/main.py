import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="ResearchTwin API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://researchtwin.net", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    researcher_slug: str


class ChatResponse(BaseModel):
    reply: str
    researcher_slug: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # TODO: wire up RAG pipeline (Glial + Neural layers)
    return ChatResponse(
        reply=f"ResearchTwin for '{req.researcher_slug}' received your query. RAG pipeline not yet connected.",
        researcher_slug=req.researcher_slug,
    )


@app.get("/api/context/{slug}")
async def get_context(slug: str):
    # TODO: compute real S-index from Semantic Scholar + GitHub + Figshare
    return {
        "researcher_slug": slug,
        "s_index": 0.0,
        "sources": {
            "semantic_scholar": {"status": "not_connected"},
            "github": {"status": "not_connected"},
            "figshare": {"status": "not_connected"},
        },
    }
