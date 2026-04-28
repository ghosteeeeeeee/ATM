"""
Shared Hyperliquid /info cache — single fetch per 60s, shared across all pipeline scripts.
Price collector WRITES; all other scripts READ.

File: /var/www/hermes/data/hl_cache.json
TTL:  60 seconds
Keys: allMids, meta
"""
from paths import *
import json, time, os, requests

_CACHE_FILE = HL_CACHE_FILE
_CACHE_TTL  = 55  # seconds — slightly less than 60s pipeline cycle to avoid double-fetchs
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

def fetch_and_cache_positions() -> dict:
    """
    Fresh fetch of open positions from Hyperliquid, write to shared cache.
    Called by position_manager (pipeline) so guardian can read from cache instead
    of making a duplicate /info API call. Falls back gracefully on error.
    Returns {coin: position_data} or {} on failure.
    """
    from hyperliquid_exchange import get_open_hype_positions_curl
    try:
        positions = get_open_hype_positions_curl()
        # Merge into existing cache preserving allMids/meta
        data = _read()
        data["positions"] = positions
        data["_pos_ts"] = time.time()
        _write(data)
        return positions
    except Exception as e:
        print(f"[hype_cache] fetch_and_cache_positions failed: {e}")
        return {}


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
    Return allMids dict — PRIMARY SOURCE is hl_cache.json (written by price_collector
    every minute). price_collector is the SOLE HL API caller. hype_cache NEVER calls HL.

    Fallback priority:
      1. hl_cache.json (541 tokens, written by price_collector)
      2. prices.json (191 tokens, subset)
      3. SQLite latest_prices (191 tokens)
    """
    # 1. Try hl_cache.json first (most complete — price_collector writes 541 entries)
    data = _read()
    if data and data.get("allMids"):
        return data["allMids"]

    # 2. Fallback: prices.json written by price_collector.save_prices()
    try:
        from paths import PRICES_FILE
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE) as f:
                p = json.load(f)
            if p.get("prices"):
                return {k: str(v) for k, v in p["prices"].items()}
    except Exception:
        pass

    # 3. Fallback: SQLite (always available)
    try:
        from signal_schema import get_all_latest_prices
        rows = get_all_latest_prices()
        if rows:
            return {token: str(info["price"]) for token, info in rows.items() if info.get("price")}
    except Exception:
        pass

    return {}

def get_meta() -> dict:
    """
    Return meta dict — PRIMARY SOURCE is hl_cache.json (written by price_collector).
    hype_cache NEVER calls HL. price_collector is the SOLE HL API caller.
    """
    data = _read()
    if data and data.get("meta"):
        return data["meta"]

    # Fallback: prices.json tokens dict
    try:
        from paths import PRICES_FILE
        if os.path.exists(PRICES_FILE):
            with open(PRICES_FILE) as f:
                p = json.load(f)
            if p.get("tokens"):
                return {"universe": [{"name": k, "maxLeverage": v} for k, v in p["tokens"].items()]}
    except Exception:
        pass

    return {}

_POS_CACHE_TTL = 60  # seconds — positions cache TTL (same as main cache)


def get_cached_positions() -> dict:
    """
    Return open positions from cache if fresh (< _POS_CACHE_TTL old).
    Returns {coin: position_data} — same format as get_open_hype_positions_curl().
    Returns {} if cache is stale or missing.
    """
    data = _read()
    if data and time.time() - data.get("_pos_ts", 0) < _POS_CACHE_TTL:
        positions = data.get("positions", {})
        if positions:
            return positions
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
