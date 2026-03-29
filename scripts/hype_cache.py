"""
Shared Hyperliquid /info cache — single fetch per 60s, shared across all pipeline scripts.
Price collector WRITES; all other scripts READ.

File: /var/www/hermes/data/hl_cache.json
TTL:  60 seconds
Keys: allMids, meta
"""
import json, time, os, requests

_CACHE_FILE = "/var/www/hermes/data/hl_cache.json"
_CACHE_TTL  = 60  # seconds
_API_URL    = "https://api.hyperliquid.xyz/info"

def _read() -> dict:
    """Read cache from disk. Returns {allMids, meta, _ts} or empty dict."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _write(data: dict) -> None:
    """Write cache to disk atomically."""
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        tmp = _CACHE_FILE + f".{os.getpid()}.tmp"
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, _CACHE_FILE)
    except Exception as e:
        print(f"[hype_cache] write error: {e}")

def fetch_and_cache() -> dict:
    """
    Fresh fetch of allMids + meta, write to cache.
    Called by price_collector only.
    Returns the fetched data.
    """
    result = {"allMids": None, "meta": None, "_ts": time.time(), "_errors": []}

    # allMids
    try:
        r = requests.post(_API_URL, json={"type": "allMids"}, timeout=10)
        if r.ok:
            result["allMids"] = r.json()
        else:
            result["_errors"].append(f"allMids HTTP {r.status_code}")
    except Exception as e:
        result["_errors"].append(f"allMids: {e}")

    # meta
    try:
        r = requests.post(_API_URL, json={"type": "meta"}, timeout=15)
        if r.ok:
            result["meta"] = r.json()
        else:
            result["_errors"].append(f"meta HTTP {r.status_code}")
    except Exception as e:
        result["_errors"].append(f"meta: {e}")

    _write(result)
    return result

def get_allMids() -> dict:
    """
    Return allMids dict from cache. Falls back to live fetch if cache miss/expired.
    """
    data = _read()
    if data and time.time() - data.get("_ts", 0) < _CACHE_TTL:
        if data.get("allMids"):
            return data["allMids"]
    # Cache miss/expired — fetch fresh
    try:
        r = requests.post(_API_URL, json={"type": "allMids"}, timeout=10)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

def get_meta() -> dict:
    """
    Return meta dict from cache. Falls back to live fetch if cache miss/expired.
    """
    data = _read()
    if data and time.time() - data.get("_ts", 0) < _CACHE_TTL:
        if data.get("meta"):
            return data["meta"]
    # Cache miss/expired — fetch fresh
    try:
        r = requests.post(_API_URL, json={"type": "meta"}, timeout=15)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return {}

def cache_age() -> float:
    """Return seconds since cache was written, or 999 if no cache."""
    data = _read()
    if data and "_ts" in data:
        return time.time() - data["_ts"]
    return 999

def cache_fresh() -> bool:
    """True if cache exists and is within TTL."""
    return cache_age() < _CACHE_TTL
