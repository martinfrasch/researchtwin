"""Simple JSON file-based cache with TTL for API responses."""

import hashlib
import json
import os
import time

CACHE_DIR = os.environ.get("CACHE_DIR", "/tmp/researchtwin_cache")
DEFAULT_TTL = 86400  # 24 hours


def _ensure_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def _key_path(key: str) -> str:
    hashed = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{hashed}.json")


def get(key: str):
    """Return cached data if it exists and hasn't expired, else None."""
    path = _key_path(key)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            entry = json.load(f)
        if time.time() - entry["ts"] > entry["ttl"]:
            os.remove(path)
            return None
        return entry["data"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def set(key: str, data, ttl: int = DEFAULT_TTL):
    """Store data with a TTL (seconds)."""
    _ensure_dir()
    entry = {"data": data, "ts": time.time(), "ttl": ttl}
    path = _key_path(key)
    with open(path, "w") as f:
        json.dump(entry, f)


def invalidate(key: str):
    """Remove a cached entry."""
    path = _key_path(key)
    if os.path.exists(path):
        os.remove(path)
