"""
ATR cache — persistent file + in-memory ATR cache with 300s TTL.
Survives process restarts; safe across concurrent processes via FileLock.

File: /root/.hermes/data/atr_cache.json
Structure: {token: {atr: float, ts: unix_timestamp}}
TTL: 300 seconds (stale ATR is better than no ATR)
"""
import json, time, os
from hermes_file_lock import FileLock

_CACHE_FILE = "/root/.hermes/data/atr_cache.json"
_CACHE_TTL  = 300  # 5 minutes — same as decider_run._ATR_TTL

# In-memory cache mirrors decider_run._ATR_CACHE for speed within a process.
# Format: {token: (atr_value, timestamp)}
_MEMORY_CACHE = {}


def _read_file() -> dict:
    """Read ATR cache from disk. Returns {token: {atr, ts}} or empty dict."""
    try:
        if os.path.exists(_CACHE_FILE):
            with open(_CACHE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _write_file(data: dict) -> None:
    """Write ATR cache to disk atomically under file lock."""
    try:
        os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
        with FileLock('atr_cache'):
            tmp = _CACHE_FILE + f".{os.getpid()}.tmp"
            with open(tmp, 'w') as f:
                json.dump(data, f)
            os.replace(tmp, _CACHE_FILE)
    except Exception as e:
        print(f"[atr_cache] write error: {e}")


def get_atr(token: str, interval: str = '15m') -> float | None:
    """
    Get ATR for token from persistent cache.
    
    Tries in order:
      1. Memory cache (fastest, per-process)
      2. File cache (survives restarts, cross-process)
      3. Returns None if not in any cache (caller should fetch from HL API)
    
    Args:
        token:    Token symbol (e.g. 'BTC', 'ETH')
        interval: Candle interval (default '15m') — included in cache key
    
    Returns:
        ATR value in dollar terms, or None if not cached / expired.
    """
    token_upper = token.upper()
    cache_key = (token_upper, interval)
    now = time.time()

    # 1. Check memory cache
    if cache_key in _MEMORY_CACHE:
        atr_val, ts = _MEMORY_CACHE[cache_key]
        if now - ts < _CACHE_TTL:
            return atr_val

    # 2. Check file cache
    data = _read_file()
    if data and token_upper in data:
        entry = data[token_upper]
        if isinstance(entry, dict) and 'atr' in entry and 'ts' in entry:
            atr_val = float(entry['atr'])
            ts = float(entry['ts'])
            if now - ts < _CACHE_TTL:
                # Populate memory cache for next call
                _MEMORY_CACHE[cache_key] = (atr_val, ts)
                return atr_val

    # Cache miss or expired — return None so caller can fetch from HL API
    return None


def save_atr(token: str, atr: float, interval: str = '15m') -> None:
    """
    Save ATR value to both memory cache and file cache.
    
    Args:
        token:    Token symbol (e.g. 'BTC', 'ETH')
        atr:      ATR value in dollar terms
        interval: Candle interval (default '15m')
    """
    token_upper = token.upper()
    cache_key = (token_upper, interval)
    now = time.time()

    # Update memory cache
    _MEMORY_CACHE[cache_key] = (atr, now)

    # Update file cache (preserve other tokens' entries)
    data = _read_file()
    data[token_upper] = {'atr': atr, 'ts': now}
    _write_file(data)


def cache_age(token: str, interval: str = '15m') -> float:
    """Return seconds since cache was written, or 999 if no cache."""
    token_upper = token.upper()
    data = _read_file()
    if token_upper in data and isinstance(data[token_upper], dict) and 'ts' in data[token_upper]:
        return time.time() - data[token_upper]['ts']
    return 999


def cache_fresh(token: str, interval: str = '15m') -> bool:
    """True if cache exists and is within TTL."""
    return cache_age(token, interval) < _CACHE_TTL
