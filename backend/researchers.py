"""Researcher lookup — backed by SQLite, seeded from _SEED_DATA."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import database

# Seed data: used only by database.init_db() on first run.
_SEED_DATA = {
    "martin-frasch": {
        "display_name": "Martin Frasch",
        "email": "martin@researchtwin.net",
        "semantic_scholar_id": "4019392",
        "github_username": "martinfrasch",
        "figshare_search_name": "Martin Frasch",
        "google_scholar_id": "3lacmuYAAAAJ",
        "orcid": "0000-0003-3159-6321",
    },
}

# Fields returned by get_researcher() — must match what main.py expects.
_FIELDS = (
    "display_name", "semantic_scholar_id", "github_username",
    "figshare_search_name", "google_scholar_id", "orcid",
)


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to the dict shape callers expect."""
    return {f: (row[f] or "") for f in _FIELDS}


def get_researcher(slug: str) -> dict:
    """Look up researcher by slug. Returns dict or raises KeyError."""
    slug = slug.lower().strip()
    row = database.get_db().execute(
        "SELECT * FROM researchers WHERE slug = ? AND status = 'active'",
        (slug,),
    ).fetchone()
    if row is None:
        raise KeyError(f"Unknown researcher: {slug}")
    return _row_to_dict(row)


def get_researcher_llm_config(slug: str) -> dict | None:
    """Return the researcher's stored LLM key/provider, or None if not set.

    Intentionally separate from get_researcher() to prevent key leakage.
    """
    slug = slug.lower().strip()
    row = database.get_db().execute(
        "SELECT llm_api_key, llm_provider FROM researchers WHERE slug = ? AND status = 'active'",
        (slug,),
    ).fetchone()
    if row is None or not row["llm_api_key"]:
        return None
    return {"api_key": row["llm_api_key"], "provider": row["llm_provider"] or "perplexity"}


def list_slugs() -> list[str]:
    """Return slugs of all active researchers."""
    rows = database.get_db().execute(
        "SELECT slug FROM researchers WHERE status = 'active' ORDER BY created_at"
    ).fetchall()
    return [r["slug"] for r in rows]


def get_by_email(email: str) -> dict | None:
    """Look up researcher by email. Returns dict or None."""
    row = database.get_db().execute(
        "SELECT * FROM researchers WHERE email = ?", (email,)
    ).fetchone()
    return dict(row) if row else None


def create_researcher(
    slug: str,
    display_name: str,
    email: str,
    tier: int = 3,
    semantic_scholar_id: str = "",
    google_scholar_id: str = "",
    github_username: str = "",
    figshare_search_name: str = "",
    orcid: str = "",
    llm_api_key: str = "",
    llm_provider: str = "",
) -> str:
    """Insert a new researcher. Returns the slug."""
    conn = database.get_db()
    conn.execute(
        """INSERT INTO researchers
           (slug, display_name, email, tier, status,
            semantic_scholar_id, google_scholar_id,
            github_username, figshare_search_name, orcid,
            llm_api_key, llm_provider)
           VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)""",
        (slug, display_name, email, tier,
         semantic_scholar_id, google_scholar_id,
         github_username, figshare_search_name, orcid,
         llm_api_key, llm_provider),
    )
    conn.commit()
    return slug


def slug_exists(slug: str) -> bool:
    """Check whether a slug is already taken."""
    row = database.get_db().execute(
        "SELECT 1 FROM researchers WHERE slug = ?", (slug,)
    ).fetchone()
    return row is not None


def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a display name, handling collisions."""
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    if not base:
        base = "researcher"
    slug = base
    counter = 2
    while slug_exists(slug):
        slug = f"{base}-{counter}"
        counter += 1
    return slug


# ---------------------------------------------------------------------------
# Profile update tokens
# ---------------------------------------------------------------------------

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def count_recent_tokens(slug: str) -> int:
    """Count tokens created for this slug in the last hour."""
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    row = database.get_db().execute(
        "SELECT COUNT(*) FROM update_tokens WHERE slug = ? AND created_at > ?",
        (slug, one_hour_ago),
    ).fetchone()
    return row[0]


def create_update_token(slug: str) -> str:
    """Generate a 6-digit code, store its hash, return the plaintext code."""
    code = f"{secrets.randbelow(1000000):06d}"
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    conn = database.get_db()
    conn.execute(
        "INSERT INTO update_tokens (slug, token_hash, expires_at) VALUES (?, ?, ?)",
        (slug, _hash_token(code), expires),
    )
    conn.commit()
    return code


def verify_update_token(slug: str, code: str) -> bool:
    """Verify code against stored hash. Increments attempts. Returns True if valid."""
    conn = database.get_db()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        "SELECT id, token_hash, attempts FROM update_tokens WHERE slug = ? AND used = 0 AND expires_at > ?",
        (slug, now),
    ).fetchall()

    token_hash = _hash_token(code)
    for row in rows:
        conn.execute(
            "UPDATE update_tokens SET attempts = attempts + 1 WHERE id = ?",
            (row["id"],),
        )
        if row["attempts"] >= 5:
            continue  # too many attempts on this token
        if row["token_hash"] == token_hash:
            conn.execute("UPDATE update_tokens SET used = 1 WHERE id = ?", (row["id"],))
            conn.commit()
            return True

    conn.commit()
    return False


def update_researcher(slug: str, **fields) -> None:
    """Update specific fields on a researcher record."""
    allowed = {"semantic_scholar_id", "google_scholar_id", "github_username",
               "figshare_search_name", "orcid", "llm_api_key", "llm_provider"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [slug]
    conn = database.get_db()
    conn.execute(
        f"UPDATE researchers SET {set_clause}, updated_at = datetime('now') WHERE slug = ?",
        values,
    )
    conn.commit()
