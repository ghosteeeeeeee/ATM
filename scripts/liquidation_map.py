#!/usr/bin/env python3
"""
Liquidation Map & Stop-Loss Cluster Detector for Hermes

Scans Hyperliquid to find:
1. Liquidation clusters from tracked wallets (forced stops)
2. Order book depth walls (resting limit orders = potential stops)
3. Support/Resistance levels derived from order flow
4. Stop hunt detection (price approaching liquidation clusters)

Data sources:
- clearinghouseState: per-wallet positions + liquidation prices
- l2Book: full order book depth with order counts
- metaAndAssetCtxs: open interest, funding, mark prices
- recentTrades: who's trading what

Output: /var/www/hermes/data/liquidation_map.json (for dashboard)
        /root/.hermes/data/liquidation_clusters.json (for signals)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

from paths import *

BASE_URL = "https://api.hyperliquid.xyz/info"
LIQ_MAP_FILE = os.path.join(WWW_DATA, "liquidation_map.json")
LIQ_CLUSTERS_FILE = os.path.join(HERMES_DATA, "liquidation_clusters.json")
SCAN_INTERVAL = 300  # 5 minutes between full scans

# Tokens to scan (top volume + our traded tokens)
SCAN_TOKENS = [
    "BTC", "ETH", "SOL", "DOGE", "XRP", "SUI", "AVAX", "LINK",
    "PEPE", "WIF", "ARB", "OP", "MATIC", "ADA", "DOT", "NEAR",
    "FIL", "APT", "SEI", "TIA", "INJ", "FET", "RENDER", "ONDO",
    "PUMP", "HYPE", "FARTCOIN", "WLD", "AAVE", "ENA", "TRUMP",
]


def _hl_info(payload: dict, timeout: int = 10):
    """POST to HL /info endpoint."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"[hl_info] Error: {e}")
        return None


# ─── Wallet Universe ─────────────────────────────────────────────────────────

def get_tracked_wallets() -> list:
    """Load all tracked wallets from hl_copy.db + leaderboard."""
    wallets = set()

    # From copy trading DB
    try:
        from hl_copy_db import get_db
        conn = get_db()
        rows = conn.execute(
            "SELECT wallet FROM traders WHERE active = 1"
        ).fetchall()
        conn.close()
        for r in rows:
            wallets.add(r["wallet"].lower())
    except Exception as e:
        print(f"[wallets] DB load failed: {e}")

    # Add known whales from our leaderboard
    LEADERBOARD = [
        "0x2ee6bef5b7b63aeefc9059f1436dabe259c34d1c",
        "0xb83de012dba672c76a7dbbbf3e459cb59d7d6e36",
        "0xb2a1dc0db510e268b645387e852061ce22e2e7aa",
        "0x0e61a8fb14f6ac999646212d30b2192cd02080dd",
        "0x6890f5d900fc26c7563e5032f25bb180bcae2d4a",
        "0x179f3d11483dafe616d56b32c4ce2562faabbbbb",
        "0xc4bb9b6fda3112b381cb94f571bc72db541e7577",
        "0xecb63caa47c7c4292e3c0d35b55e0e0b2bc69b07",  # $46M whale from trades
        "0xf5d81a135f756ca16544e53c20fc20643ec3ad53",  # $1.1M trader
        "0xac487c027ffe3e7c5b6c0e1a5518b1ea1a9c4f4f",  # $1.3M trader
    ]
    for w in LEADERBOARD:
        wallets.add(w.lower())

    return list(wallets)


# ─── Position Scanner ────────────────────────────────────────────────────────

def scan_wallet_positions(wallet: str) -> list:
    """Get all positions + liquidation prices for a wallet."""
    state = _hl_info({"type": "clearinghouseState", "user": wallet})
    if not state or not isinstance(state, dict):
        return []

    positions = []
    for item in state.get("assetPositions", []):
        p = item.get("position", {})
        coin = p.get("coin", "")
        szi = float(p.get("szi", 0))
        if szi == 0:
            continue

        entry = float(p.get("entryPx", 0))
        liq_raw = p.get("liquidationPx")
        liq = float(liq_raw) if liq_raw and liq_raw != "0" else None

        lev = p.get("leverage", 1)
        if isinstance(lev, dict):
            lev = float(lev.get("value", 1))
        else:
            lev = float(lev)

        positions.append({
            "wallet": wallet,
            "coin": coin.upper(),
            "side": "LONG" if szi > 0 else "SHORT",
            "size": abs(szi),
            "entry_px": entry,
            "liquidation_px": liq,
            "leverage": lev,
            "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
        })

    return positions


def scan_all_positions(wallets: list) -> dict:
    """Scan all wallets, return positions grouped by coin."""
    by_coin = defaultdict(list)
    total_wallets = len(wallets)

    for i, wallet in enumerate(wallets):
        if i > 0 and i % 10 == 0:
            time.sleep(1)  # Rate limit every 10 wallets
        elif i > 0:
            time.sleep(0.3)

        positions = scan_wallet_positions(wallet)
        for pos in positions:
            by_coin[pos["coin"]].append(pos)

        if (i + 1) % 25 == 0:
            print(f"[scan] {i+1}/{total_wallets} wallets scanned...")

    return dict(by_coin)


# ─── Liquidation Cluster Analysis ───────────────────────────────────────────

def find_liquidation_clusters(positions: list, current_price: float,
                               bin_pct: float = 0.005) -> list:
    """
    Find price levels where multiple positions would be liquidated.

    Clusters = price zones where total liquidation exposure is high.
    These are 'stop hunt magnets' — price tends to gravitate toward them.

    bin_pct: bin size as fraction of price (0.5% default)
    """
    if not positions:
        return []

    # Collect all liquidation prices with their sizes
    liq_levels = []
    for pos in positions:
        liq = pos.get("liquidation_px")
        if liq and liq > 0:
            # Scale size by leverage (higher leverage = more forced selling)
            effective_size = pos["size"] * pos["leverage"]
            liq_levels.append({
                "price": liq,
                "size": effective_size,
                "wallet": pos["wallet"],
                "side": pos["side"],
                "coin": pos["coin"],
                "leverage": pos["leverage"],
                "distance_pct": (liq - current_price) / current_price,
            })

    if not liq_levels:
        return []

    # Bin liquidation levels — track dominant side in each bin
    bins = defaultdict(lambda: {"total_size": 0, "count": 0,
                                 "wallets": [], "max_leverage": 0,
                                 "total_notional": 0,
                                 "long_size": 0, "short_size": 0})

    for lvl in liq_levels:
        price = lvl["price"]
        bin_idx = round(price / (current_price * bin_pct)) * bin_pct * current_price
        key = f"{bin_idx:.4f}"
        bins[key]["total_size"] += lvl["size"]
        bins[key]["count"] += 1
        bins[key]["wallets"].append(lvl["wallet"][:10])
        bins[key]["max_leverage"] = max(bins[key]["max_leverage"], lvl["leverage"])
        bins[key]["total_notional"] += lvl["size"] * price
        bins[key]["price"] = bin_idx
        if lvl["side"] == "LONG":
            bins[key]["long_size"] += lvl["size"]
        else:
            bins[key]["short_size"] += lvl["size"]

    # Sort by total size (biggest clusters first)
    clusters = sorted(bins.values(), key=lambda x: x["total_size"], reverse=True)

    # Take top clusters and annotate
    result = []
    for cluster in clusters[:30]:
        price = cluster["price"]
        dist = (price - current_price) / current_price
        # Dominant side = whichever has more size in this bin
        dominant = "LONG" if cluster["long_size"] >= cluster["short_size"] else "SHORT"
        result.append({
            "price": round(price, 6),
            "distance_pct": round(dist * 100, 3),
            "total_size": round(cluster["total_size"], 4),
            "count": cluster["count"],
            "max_leverage": cluster["max_leverage"],
            "wallets": cluster["wallets"][:10],
            "total_notional_usd": round(cluster["total_notional"], 2),
            "zone_type": "LIQUIDATION" if abs(dist) > 0.001 else "AT_MARK",
            "side": dominant,
            "long_size": round(cluster["long_size"], 4),
            "short_size": round(cluster["short_size"], 4),
        })

    return result


# ─── Order Book Analysis ─────────────────────────────────────────────────────

def get_order_book_depth(coin: str) -> dict:
    """Get L2 order book and compute depth metrics."""
    book = _hl_info({"type": "l2Book", "coin": coin})
    if not book or "levels" not in book:
        return {}

    bids = book["levels"][0]  # First element = bids
    asks = book["levels"][1]  # Second element = asks

    # Compute cumulative depth
    bid_depth = 0
    ask_depth = 0
    bid_walls = []
    ask_walls = []

    for lvl in bids:
        sz = float(lvl["sz"])
        px = float(lvl["px"])
        n = lvl.get("n", 1)  # Number of individual orders
        bid_depth += sz
        if n >= 3 or sz > 1.0:  # Significant level
            bid_walls.append({"price": px, "size": sz, "orders": n,
                              "cumulative": bid_depth})

    for lvl in asks:
        sz = float(lvl["sz"])
        px = float(lvl["px"])
        n = lvl.get("n", 1)
        ask_depth += sz
        if n >= 3 or sz > 1.0:
            ask_walls.append({"price": px, "size": sz, "orders": n,
                              "cumulative": ask_depth})

    best_bid = float(bids[0]["px"]) if bids else 0
    best_ask = float(asks[0]["px"]) if asks else 0
    spread = best_ask - best_bid if best_bid and best_ask else 0
    spread_bps = (spread / best_bid * 10000) if best_bid else 0

    # Imbalance ratio (bid depth vs ask depth within 0.5% of mid)
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
    threshold = mid * 0.005  # 0.5%

    near_bid_depth = sum(float(l["sz"]) for l in bids
                         if abs(float(l["px"]) - mid) < threshold)
    near_ask_depth = sum(float(l["sz"]) for l in asks
                         if abs(float(l["px"]) - mid) < threshold)

    imbalance = (near_bid_depth / near_ask_depth if near_ask_depth > 0
                 else 999.0)

    return {
        "coin": coin,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread_bps": round(spread_bps, 2),
        "bid_depth_total": round(bid_depth, 4),
        "ask_depth_total": round(ask_depth, 4),
        "imbalance_ratio": round(imbalance, 3),
        "bid_walls": bid_walls[:10],
        "ask_walls": ask_walls[:10],
        "near_bid_depth": round(near_bid_depth, 4),
        "near_ask_depth": round(near_ask_depth, 4),
    }


def find_sr_from_book(book: dict, current_price: float) -> list:
    """
    Derive support/resistance levels from order book walls.

    Large resting orders = potential support (bids) or resistance (asks).
    High order count at a level = many traders placed stops there.
    """
    levels = []

    for wall in book.get("bid_walls", []):
        # Support: large bid walls below price
        if wall["price"] < current_price:
            strength = wall["size"] * min(wall["orders"], 10)  # Size × order density
            levels.append({
                "price": wall["price"],
                "type": "SUPPORT",
                "strength": round(strength, 4),
                "size": wall["size"],
                "orders": wall["orders"],
                "source": "ORDER_BOOK",
                "distance_pct": round(
                    (wall["price"] - current_price) / current_price * 100, 3
                ),
            })

    for wall in book.get("ask_walls", []):
        # Resistance: large ask walls above price
        if wall["price"] > current_price:
            strength = wall["size"] * min(wall["orders"], 10)
            levels.append({
                "price": wall["price"],
                "type": "RESISTANCE",
                "strength": round(strength, 4),
                "size": wall["size"],
                "orders": wall["orders"],
                "source": "ORDER_BOOK",
                "distance_pct": round(
                    (wall["price"] - current_price) / current_price * 100, 3
                ),
            })

    # Sort by strength
    levels.sort(key=lambda x: x["strength"], reverse=True)
    return levels[:20]


# ─── Open Interest & Funding Context ─────────────────────────────────────────

def get_market_context(coin: str) -> dict:
    """Get OI, funding, and meta context for a coin."""
    ctxs = _hl_info({"type": "metaAndAssetCtxs"})
    if not ctxs or len(ctxs) < 2:
        return {}

    for i, asset in enumerate(ctxs[0].get("universe", [])):
        if asset.get("name", "").upper() == coin.upper():
            ctx = ctxs[1][i] if i < len(ctxs[1]) else {}
            return {
                "coin": coin,
                "open_interest": float(ctx.get("openInterest", 0)),
                "funding_rate": float(ctx.get("funding", 0)),
                "mark_px": float(ctx.get("markPx", 0)),
                "oracle_px": float(ctx.get("oraclePx", 0)),
                "day_ntl_vlm": float(ctx.get("dayNtlVlm", 0)),
                "day_base_vlm": float(ctx.get("dayBaseVlm", 0)),
                "prev_day_px": float(ctx.get("prevDayPx", 0)),
                "premium": float(ctx.get("premium", 0)),
            }

    return {}


# ─── Stop Hunt Detection ────────────────────────────────────────────────────

def detect_stop_hunt(prices: dict, clusters: dict, book_data: dict) -> list:
    """
    Detect when price is approaching a liquidation cluster —
    the setup for a stop hunt / cascade.

    Conditions:
    1. Price is within 1% of a liquidation cluster
    2. Cluster has significant total size (>$10K notional)
    3. Order book shows thin liquidity on the hunt side (easy to push through)
    """
    signals = []

    for coin, cluster_list in clusters.items():
        current = prices.get(coin)
        if not current:
            continue

        book = book_data.get(coin, {})
        imbalance = book.get("imbalance_ratio", 1.0)

        for cl in cluster_list[:5]:  # Top 5 clusters per coin
            dist = abs(cl["distance_pct"])
            if dist > 2.0:  # More than 2% away = not urgent
                continue

            notional = cl.get("total_notional_usd", 0)
            if notional < 5000:  # Too small to matter
                continue

            # Check if book is thin on the hunt side
            is_long_hunt = cl["side"] == "LONG"  # Longs getting liquidated = price dropping
            book_thin = False
            if is_long_hunt:
                # Thin asks = easy to push price down
                book_thin = imbalance > 2.0  # 2x more bids than asks = thin downside
            else:
                # Thin bids = easy to push price up
                book_thin = imbalance < 0.5  # More asks than bids = thin upside

            # Score the signal
            urgency = max(0, (2.0 - dist) / 2.0) * 100  # 0-100 based on distance
            size_score = min(100, notional / 1000)  # Cap at $100K
            cascade_score = min(100, cl["count"] * 10)  # More wallets = bigger cascade

            total_score = (urgency * 0.4 + size_score * 0.3 + cascade_score * 0.3)

            signals.append({
                "coin": coin,
                "current_price": current,
                "cluster_price": cl["price"],
                "distance_pct": cl["distance_pct"],
                "cluster_size_usd": notional,
                "position_count": cl["count"],
                "max_leverage": cl["max_leverage"],
                "hunt_direction": "DOWN" if is_long_hunt else "UP",
                "book_thin": book_thin,
                "imbalance_ratio": imbalance,
                "score": round(total_score, 1),
                "signal": "STOP_HUNT_IMMINENT" if dist < 0.5 and notional > 20000
                          else "STOP_HUNT_APPROACHING" if dist < 1.0
                          else "STOP_HUNT_ZONE",
            })

    signals.sort(key=lambda x: x["score"], reverse=True)
    return signals


# ─── Main Aggregation ────────────────────────────────────────────────────────

def build_liquidation_map(coins: list = None) -> dict:
    """
    Full liquidation map build:
    1. Scan all tracked wallets for positions + liquidation levels
    2. Compute L2 order book depth for each coin
    3. Find liquidation clusters (stop magnets)
    4. Derive S/R from order book walls
    5. Detect stop hunt setups
    """
    if coins is None:
        coins = SCAN_TOKENS

    print(f"[liq_map] Starting scan of {len(coins)} coins, "
          f"scanning wallet universe...")

    t0 = time.time()
    wallets = get_tracked_wallets()
    print(f"[liq_map] Wallet universe: {len(wallets)} wallets")

    # 1. Scan all positions
    print("[liq_map] Scanning wallet positions...")
    all_positions = scan_all_positions(wallets)
    scan_time = time.time() - t0
    print(f"[liq_map] Position scan complete in {scan_time:.1f}s, "
          f"found positions on {len(all_positions)} coins")

    # 2. Get prices from all positions
    prices = {}

    # 3. Order book + S/R for each coin
    print("[liq_map] Fetching order books...")
    book_data = {}
    sr_levels = {}
    for coin in coins:
        time.sleep(0.3)
        book = get_order_book_depth(coin)
        if book:
            book_data[coin] = book
            mid = (book["best_bid"] + book["best_ask"]) / 2
            if mid > 0:
                prices[coin] = mid
            sr_levels[coin] = find_sr_from_book(book, mid)
        if len(book_data) % 10 == 0:
            print(f"[liq_map] Order books: {len(book_data)}/{len(coins)}")

    print(f"[liq_map] Got {len(book_data)} order books")

    # 4. Find liquidation clusters
    print("[liq_map] Computing liquidation clusters...")
    clusters = {}
    for coin, positions in all_positions.items():
        price = prices.get(coin)
        if price and price > 0:
            clusters[coin] = find_liquidation_clusters(positions, price)

    # 5. Get market context (OI, funding)
    print("[liq_map] Fetching market context...")
    market_ctx = {}
    for coin in coins[:20]:  # Top 20 for rate limits
        time.sleep(0.3)
        ctx = get_market_context(coin)
        if ctx:
            market_ctx[coin] = ctx

    # 6. Detect stop hunts
    print("[liq_map] Detecting stop hunt setups...")
    stop_hunts = detect_stop_hunt(prices, clusters, book_data)

    # 7. Build composite S/R levels (merge book walls + liquidation clusters)
    composite_sr = {}
    for coin in set(list(clusters.keys()) + list(sr_levels.keys())):
        levels = []
        price = prices.get(coin, 0)

        # Add book-based S/R
        for sr in sr_levels.get(coin, []):
            levels.append(sr)

        # Add liquidation-based S/R
        for cl in clusters.get(coin, [])[:10]:
            if cl["distance_pct"] > 2:
                continue
            side = "SUPPORT" if cl["distance_pct"] < 0 else "RESISTANCE"
            levels.append({
                "price": cl["price"],
                "type": side,
                "strength": cl["total_size"],
                "size": cl["total_size"],
                "orders": cl["count"],
                "source": "LIQUIDATION",
                "distance_pct": cl["distance_pct"],
            })

        # Sort by proximity to current price
        levels.sort(key=lambda x: abs(x["distance_pct"]))
        composite_sr[coin] = levels[:15]

    # 8. Assemble final output
    total_positions = sum(len(v) for v in all_positions.values())
    total_wallets_scanned = len(wallets)
    total_liquidation_usd = sum(
        cl["total_notional_usd"]
        for coin_clusters in clusters.values()
        for cl in coin_clusters
    )

    result = {
        "timestamp": int(time.time()),
        "scan_duration_sec": round(time.time() - t0, 1),
        "wallets_scanned": total_wallets_scanned,
        "coins_scanned": len(coins),
        "total_positions_found": total_positions,
        "total_liquidation_exposure_usd": round(total_liquidation_usd, 2),
        "market_context": market_ctx,
        "liquidation_clusters": clusters,
        "support_resistance": composite_sr,
        "order_books": {coin: {
            "imbalance": book_data[coin]["imbalance_ratio"],
            "spread_bps": book_data[coin]["spread_bps"],
            "bid_walls": book_data[coin]["bid_walls"][:5],
            "ask_walls": book_data[coin]["ask_walls"][:5],
        } for coin in book_data},
        "stop_hunt_signals": stop_hunts,
        "position_summary": {
            coin: {
                "long_count": sum(1 for p in pos if p["side"] == "LONG"),
                "short_count": sum(1 for p in pos if p["side"] == "SHORT"),
                "total_long_size": sum(p["size"] for p in pos if p["side"] == "LONG"),
                "total_short_size": sum(p["size"] for p in pos if p["side"] == "SHORT"),
                "avg_leverage": round(sum(p["leverage"] for p in pos) / len(pos), 1) if pos else 0,
                "max_leverage": max((p["leverage"] for p in pos), default=0),
            }
            for coin, pos in all_positions.items()
        },
    }

    return result


def save_map(data: dict):
    """Save liquidation map to files."""
    # For dashboard
    Path(LIQ_MAP_FILE).parent.mkdir(parents=True, exist_ok=True)
    tmp = LIQ_MAP_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, LIQ_MAP_FILE)

    # For signals (smaller, just clusters + stop hunts)
    signal_data = {
        "timestamp": data["timestamp"],
        "total_liquidation_exposure_usd": data["total_liquidation_exposure_usd"],
        "liquidation_clusters": data["liquidation_clusters"],
        "stop_hunt_signals": data["stop_hunt_signals"],
        "support_resistance": data["support_resistance"],
        "position_summary": data["position_summary"],
    }
    tmp2 = LIQ_CLUSTERS_FILE + ".tmp"
    with open(tmp2, "w") as f:
        json.dump(signal_data, f, indent=2)
    os.replace(tmp2, LIQ_CLUSTERS_FILE)

    print(f"[liq_map] Saved to {LIQ_MAP_FILE}")
    print(f"[liq_map] Saved signal data to {LIQ_CLUSTERS_FILE}")


# ─── Quick Query Functions (for other scripts) ──────────────────────────────

def load_clusters() -> dict:
    """Load the latest liquidation cluster data."""
    try:
        with open(LIQ_CLUSTERS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_nearest_cluster(coin: str, side: str = None) -> dict | None:
    """
    Get the nearest liquidation cluster for a coin.
    side: 'LONG' = nearest long liquidation (price dropping),
          'SHORT' = nearest short liquidation (price rising),
          None = nearest regardless of side
    """
    data = load_clusters()
    clusters = data.get("liquidation_clusters", {}).get(coin.upper(), [])

    if not clusters:
        return None

    # Filter by side if specified
    if side:
        clusters = [c for c in clusters if c.get("side") == side.upper()]

    # Already sorted by total_size, but we want nearest
    clusters.sort(key=lambda x: abs(x["distance_pct"]))

    return clusters[0] if clusters else None


def get_sr_levels(coin: str) -> list:
    """Get composite support/resistance levels for a coin."""
    data = load_clusters()
    return data.get("support_resistance", {}).get(coin.upper(), [])


def get_stop_hunt_signal(coin: str) -> dict | None:
    """Get stop hunt signal for a specific coin if one exists."""
    data = load_clusters()
    for signal in data.get("stop_hunt_signals", []):
        if signal["coin"].upper() == coin.upper():
            return signal
    return None


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Liquidation Map Scanner")
    parser.add_argument("--coins", nargs="*", help="Specific coins to scan")
    parser.add_argument("--query", help="Query a specific coin's clusters")
    parser.add_argument("--sr", help="Get S/R levels for a coin")
    parser.add_argument("--stop-hunt", help="Check stop hunt for a coin")
    parser.add_argument("--quick", action="store_true",
                        help="Quick scan (top 10 coins only)")
    args = parser.parse_args()

    if args.query:
        data = load_clusters()
        coin = args.query.upper()
        clusters = data.get("liquidation_clusters", {}).get(coin, [])
        print(f"\n=== {coin} Liquidation Clusters ===")
        for c in clusters[:10]:
            print(f"  ${c['price']:.4f} ({c['distance_pct']:+.2f}%) "
                  f"size=${c['total_notional_usd']:,.0f} "
                  f"count={c['count']} max_lev={c['max_leverage']}x")
    elif args.sr:
        levels = get_sr_levels(args.sr.upper())
        coin = args.sr.upper()
        print(f"\n=== {coin} Support/Resistance ===")
        for l in levels:
            src = "🔍" if l["source"] == "LIQUIDATION" else "📚"
            print(f"  {src} {l['type']} ${l['price']:.4f} "
                  f"({l['distance_pct']:+.2f}%) strength={l['strength']:.1f} "
                  f"orders={l['orders']}")
    elif args.stop_hunt:
        sig = get_stop_hunt_signal(args.stop_hunt.upper())
        if sig:
            print(f"\n=== {sig['coin']} Stop Hunt Signal ===")
            print(f"  Signal: {sig['signal']}")
            print(f"  Direction: {sig['hunt_direction']}")
            print(f"  Cluster: ${sig['cluster_price']:.4f} "
                  f"({sig['distance_pct']:+.2f}%)")
            print(f"  Size: ${sig['cluster_size_usd']:,.0f}")
            print(f"  Score: {sig['score']}")
        else:
            print(f"No stop hunt signal for {args.stop_hunt.upper()}")
    else:
        coins = args.coins or (SCAN_TOKENS[:10] if args.quick else None)
        data = build_liquidation_map(coins)
        save_map(data)

        # Print summary
        print(f"\n{'='*60}")
        print(f"LIQUIDATION MAP SUMMARY")
        print(f"{'='*60}")
        print(f"Wallets scanned: {data['wallets_scanned']}")
        print(f"Coins scanned: {data['coins_scanned']}")
        print(f"Total positions: {data['total_positions_found']}")
        print(f"Total liq exposure: ${data['total_liquidation_exposure_usd']:,.0f}")
        print(f"Scan duration: {data['scan_duration_sec']:.1f}s")

        if data["stop_hunt_signals"]:
            print(f"\n🚨 STOP HUNT SIGNALS:")
            for sig in data["stop_hunt_signals"][:10]:
                print(f"  {sig['signal']}: {sig['coin']} "
                      f"${sig['cluster_price']:.4f} "
                      f"({sig['distance_pct']:+.2f}%) "
                      f"size=${sig['cluster_size_usd']:,.0f} "
                      f"score={sig['score']}")

        print(f"\n📊 TOP LIQUIDATION CLUSTERS:")
        for coin, cls in sorted(data["liquidation_clusters"].items(),
                                 key=lambda x: max((c["total_notional_usd"]
                                                     for c in x[1]), default=0),
                                 reverse=True)[:10]:
            if cls:
                top = cls[0]
                print(f"  {coin}: ${top['price']:.4f} ({top['distance_pct']:+.2f}%) "
                      f"${top['total_notional_usd']:,.0f} "
                      f"({top['count']} positions)")
