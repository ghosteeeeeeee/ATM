#!/usr/bin/env python3
"""
top150.py — Maintain top-150 token filter based on 24h Binance volume.

Usage:
  python3 top150.py          # update and print top 150
  python3 top150.py --check  # just check current status
  python3 top150.py --force  # force refresh even if cache is fresh

Output: /root/.hermes/data/top150_tokens.json
  {"tokens": ["BTC","ETH",...], "updated": 1743216000, "count": 150}

How it works:
  1. Get full HL universe (which tokens are tradeable)
  2. Fetch Binance 24h volume for all USDT pairs
  3. Map HL tokens to Binance symbols (direct match for most)
  4. Rank by volume, take top 150 from HL universe
  5. Cache for 1 hour
"""
import sys, os, time, json, urllib.request, math

# Use cached HL meta from hyperliquid_exchange (already cached, avoids rate limits)
import sys as _sys
_sys.path.insert(0, '/root/.hermes/scripts')
from hyperliquid_exchange import _get_meta, get_tradeable_tokens

HL_INFO_URL = "https://api.hyperliquid.xyz/info"
BINANCE_VOL_URL = "https://api.binance.com/api/v3/ticker/24hr"
CACHE_FILE = "/root/.hermes/data/top150_tokens.json"
CACHE_TTL = 3600  # 1 hour


def hl_info(payload):
    req = urllib.request.Request(
        HL_INFO_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def get_hl_universe():
    """Get all non-delisted tokens from Hyperliquid (uses cached meta)."""
    return get_tradeable_tokens()


def get_binance_volumes():
    """Get 24h quote volumes for all Binance USDT pairs. Returns {symbol: volume}."""
    req = urllib.request.Request(BINANCE_VOL_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    # Filter USDT pairs only
    out = {}
    for t in data:
        sym = t.get("symbol", "")
        if sym.endswith("USDT"):
            vol = float(t.get("quoteVolume", 0) or 0)
            if vol > 0:
                out[sym] = vol
    return out


def hl_to_binance_symbol(hl_token: str) -> str:
    """Map HL token name to Binance USDT symbol."""
    return hl_token + "USDT"


def get_top150():
    """Main: fetch HL universe + Binance volumes, return top 150 by volume."""
    print("[top150] Fetching HL universe...")
    hl_tokens = get_hl_universe()
    print(f"[top150] HL tradeable tokens: {len(hl_tokens)}")

    print("[top150] Fetching Binance volumes...")
    bnb_vols = get_binance_volumes()
    print(f"[top150] Binance USDT pairs with volume: {len(bnb_vols)}")

    # Score each HL token by Binance volume
    scored = []
    for token in hl_tokens:
        bnb_sym = hl_to_binance_symbol(token)
        vol = bnb_vols.get(bnb_sym, 0)
        # Tokens with no Binance volume get sorted to bottom (but we keep them if <150)
        scored.append((token, vol))

    # Sort by volume descending, take top 150
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:150]
    top_tokens = [t for t, _ in top]

    # If HL has fewer than 150 tokens, take all
    if len(top_tokens) < 150:
        all_tokens = [t for t, _ in scored]
        top_tokens = all_tokens

    print(f"[top150] Selected {len(top_tokens)} tokens (top by Binance 24h volume)")
    print(f"[top150] Bottom 5: {[(t, f'${v/1e6:.1f}M') for t, v in scored[145:150] if v > 0]}")
    print(f"[top150] No-Binance-volume tokens: {[t for t, v in scored if v == 0]}")

    return top_tokens


def load_cache():
    """Load cached top150 if fresh."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE) as f:
            data = json.load(f)
        age = time.time() - data.get("updated", 0)
        if age < CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def save_cache(tokens):
    """Save top150 to cache."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump({"tokens": tokens, "updated": int(time.time()), "count": len(tokens)}, f)


def get_allowed_tokens(force_refresh=False) -> list:
    """Get the list of allowed (top-150) tokens. Cached for 1h."""
    if not force_refresh:
        cached = load_cache()
        if cached:
            return cached["tokens"]
    tokens = get_top150()
    save_cache(tokens)
    return tokens


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Show current cached top150")
    parser.add_argument("--force", action="store_true", help="Force refresh (ignore cache)")
    args = parser.parse_args()

    if args.check:
        cached = load_cache()
        if cached:
            age = time.time() - cached["updated"]
            print(f"Cached: {cached['count']} tokens, age: {age/60:.1f}m ago")
            print(f"Tokens: {', '.join(cached['tokens'])}")
        else:
            print("No cache — run without --check to fetch")
        sys.exit(0)

    print(f"[top150] {'Refreshing' if args.force else 'Fetching'} top 150 tokens...")
    tokens = get_allowed_tokens(force_refresh=args.force)
    save_cache(tokens)
    print(f"\nTop {len(tokens)} tokens:")
    for i, t in enumerate(tokens, 1):
        print(f"  {i:3d}. {t}")
