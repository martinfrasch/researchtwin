"""SQLite database for persistent researcher storage."""

import os
import sqlite3
import threading

_DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "researchtwin.db"),
)

_local = threading.local()


def get_db() -> sqlite3.Connection:
    """Return a thread-local SQLite connection."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_db():
    """Create tables and seed initial data if empty."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS researchers (
            slug                TEXT PRIMARY KEY,
            display_name        TEXT NOT NULL,
            email               TEXT NOT NULL,
            tier                INTEGER NOT NULL DEFAULT 3,
            status              TEXT NOT NULL DEFAULT 'active',
            semantic_scholar_id TEXT DEFAULT '',
            google_scholar_id   TEXT DEFAULT '',
            github_username     TEXT DEFAULT '',
            figshare_search_name TEXT DEFAULT '',
            orcid               TEXT DEFAULT '',
            created_at          TEXT DEFAULT (datetime('now')),
            updated_at          TEXT DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_email ON researchers(email);

        CREATE TABLE IF NOT EXISTS update_tokens (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slug        TEXT NOT NULL REFERENCES researchers(slug),
            token_hash  TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            expires_at  TEXT NOT NULL,
            attempts    INTEGER DEFAULT 0,
            used        INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_update_tokens_slug ON update_tokens(slug);
    """)
    conn.commit()

    # Migration: add LLM key columns (idempotent)
    for col, typedef in [("llm_api_key", "TEXT DEFAULT ''"), ("llm_provider", "TEXT DEFAULT ''")]:
        try:
            conn.execute(f"ALTER TABLE researchers ADD COLUMN {col} {typedef}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Seed from _SEED_DATA if table is empty
    count = conn.execute("SELECT COUNT(*) FROM researchers").fetchone()[0]
    if count == 0:
        from researchers import _SEED_DATA
        for slug, data in _SEED_DATA.items():
            conn.execute(
                """INSERT INTO researchers
                   (slug, display_name, email, tier, status,
                    semantic_scholar_id, google_scholar_id,
                    github_username, figshare_search_name, orcid)
                   VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)""",
                (
                    slug,
                    data["display_name"],
                    data.get("email", f"{slug}@researchtwin.net"),
                    data.get("tier", 3),
                    data.get("semantic_scholar_id", ""),
                    data.get("google_scholar_id", ""),
                    data.get("github_username", ""),
                    data.get("figshare_search_name", ""),
                    data.get("orcid", ""),
                ),
            )
        conn.commit()


def close_db():
    """Close the thread-local connection if open."""
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None
