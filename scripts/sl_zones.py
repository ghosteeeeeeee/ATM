#!/usr/bin/env python3
"""
sl_zones.py — SL Memory Zone Aggregation Engine

Clusters SL hits into zones (S/R levels) and scores them by strength.
Used by signal_compactor, position_manager, and decider_run for:
- Entry distance filtering (skip trades near death zones)
- Exit tightening (tighten trail near zones)
- Position sizing (reduce size when zone ahead)

Part of the SL Memory S/R System (v2.0)
"""

import os, sys, math, json, time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from paths import HERMES_DATA
from hermes_log import log

# ── Zone Parameters ───────────────────────────────────────────────────────────
# From sl-memory-sr-system-v2.md
ZONE_CLUSTER_TOLERANCE_PCT = 0.5    # cluster SL hits within 0.5% of each other
ZONE_MIN_HITS = 2                   # minimum hits to form a zone
ZONE_RECENTLY_DECAY = 0.95          # exponential decay per day
ZONE_EXTREME_MULT = 1.5             # EXTREME regime multiplier
ZONE_HIGH_MULT = 1.3                # HIGH regime multiplier
ZONE_CONFLUENCE_BONUS = 1.5         # bonus if zone aligns with EMA/BB

# Entry filter thresholds
ENTRY_BLOCK_DISTANCE_PCT = 2.0      # block entry if within 2% of death zone
ENTRY_WATCH_DISTANCE_PCT = 3.0      # watch mode if within 3% of death zone
ENTRY_BLOCK_STRENGTH_MIN = 0.5      # minimum zone strength to trigger block
ENTRY_WATCH_STRENGTH_MIN = 0.3      # minimum zone strength to trigger watch

# Exit tightening thresholds
EXIT_TIGHTEN_ATR = 1.0              # tighten trail within 1 ATR of zone
EXIT_WATCH_ATR = 2.0               # watch mode within 2 ATR of zone
EXIT_TIGHTEN_TRAIL_PCT = 0.10      # tightened trail distance (from 0.20%)

# Position sizing
SIZE_REDUCE_1_ATR = 1.5             # reduce to 50% if zone within 1.5 ATR
SIZE_REDUCE_2_ATR = 3.0             # reduce to 75% if zone within 3.0 ATR


class SLZone:
    """Represents a cluster of SL hits at a similar price level."""
    __slots__ = ('center', 'width', 'hit_count', 'hits', 'strength',
                 'recency_days', 'dominant_regime', 'token', 'direction')
    
    def __init__(self, token, direction, center, width, hits):
        self.token = token
        self.direction = direction
        self.center = center
        self.width = width
        self.hits = hits
        self.hit_count = len(hits)
        self.strength = 0.0
        self.recency_days = 999
        self.dominant_regime = 'UNKNOWN'
    
    def to_dict(self):
        return {
            'token': self.token,
            'direction': self.direction,
            'center': self.center,
            'width': self.width,
            'hit_count': self.hit_count,
            'strength': round(self.strength, 4),
            'recency_days': round(self.recency_days, 1),
            'dominant_regime': self.dominant_regime,
        }


def _get_conn():
    """Get PostgreSQL connection to brain DB."""
    import psycopg2
    return psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')


def get_sl_hits(token, direction, lookback_days=30):
    """Fetch SL hits for a token+direction from sl_memory."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT initial_sl, hit_time, pnl_usdt, atr_at_entry, regime, entry_price, exit_price
            FROM sl_memory
            WHERE token = %s AND direction = %s
              AND hit_time > NOW() - INTERVAL '%s days'
            ORDER BY hit_time DESC
        """, (token, direction, lookback_days))
        hits = []
        for row in cur.fetchall():
            hits.append({
                'sl_price': float(row[0]),
                'hit_time': row[1],
                'pnl_usdt': float(row[2]) if row[2] else 0,
                'atr': float(row[3]) if row[3] else None,
                'regime': row[4] or 'UNKNOWN',
                'entry_price': float(row[5]) if row[5] else None,
                'exit_price': float(row[6]) if row[6] else None,
            })
        return hits
    finally:
        conn.close()


def cluster_hits(hits, tolerance_pct=ZONE_CLUSTER_TOLERANCE_PCT):
    """Cluster SL hits into zones based on price proximity."""
    if not hits:
        return []
    
    # Sort by SL price
    sorted_hits = sorted(hits, key=lambda h: h['sl_price'])
    
    zones = []
    current_cluster = [sorted_hits[0]]
    
    for hit in sorted_hits[1:]:
        # Check if this hit is within tolerance of the cluster center
        cluster_center = sum(h['sl_price'] for h in current_cluster) / len(current_cluster)
        distance_pct = abs(hit['sl_price'] - cluster_center) / cluster_center * 100
        
        if distance_pct <= tolerance_pct:
            current_cluster.append(hit)
        else:
            # Finalize current cluster
            if len(current_cluster) >= ZONE_MIN_HITS:
                zones.append(current_cluster)
            current_cluster = [hit]
    
    # Don't forget the last cluster
    if len(current_cluster) >= ZONE_MIN_HITS:
        zones.append(current_cluster)
    
    return zones


def calculate_zone_strength(zone_hits, now=None):
    """Calculate composite strength score for a zone."""
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Recency: exponential decay from most recent hit
    most_recent = max(h['hit_time'] for h in zone_hits)
    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)
    days_since = (now - most_recent).total_seconds() / 86400
    recency = ZONE_RECENTLY_DECAY ** days_since
    
    # Frequency: logarithmic scaling
    frequency = math.log2(len(zone_hits) + 1) / 5  # normalize to ~1.0 at 31 hits
    
    # Regime: use dominant regime of hits
    regime_counts = defaultdict(int)
    for h in zone_hits:
        regime_counts[h['regime']] += 1
    dominant_regime = max(regime_counts, key=regime_counts.get)
    
    regime_mult = {
        'EXTREME': ZONE_EXTREME_MULT,
        'HIGH': ZONE_HIGH_MULT,
        'NORMAL': 1.0,
        'FLAT': 0.8,
    }.get(dominant_regime, 1.0)
    
    # PnL severity: bigger losses = stronger zone
    total_loss = sum(abs(h['pnl_usdt']) for h in zone_hits if h['pnl_usdt'] < 0)
    severity = min(1.0, total_loss / 2.0)  # cap at $2 total loss
    
    strength = min(1.0, recency * frequency * regime_mult * (1.0 + severity * 0.3))
    
    return strength, dominant_regime, days_since


def get_sl_zones(token, direction, lookback_days=30):
    """
    Main function: get scored zones for a token+direction.
    Returns list of SLZone objects sorted by strength (strongest first).
    """
    hits = get_sl_hits(token, direction, lookback_days)
    if not hits:
        return []
    
    clustered = cluster_hits(hits)
    now = datetime.now(timezone.utc)
    
    zones = []
    for cluster in clustered:
        center = sum(h['sl_price'] for h in cluster) / len(cluster)
        width = max(h['sl_price'] for h in cluster) - min(h['sl_price'] for h in cluster)
        
        zone = SLZone(token, direction, center, width, cluster)
        zone.strength, zone.dominant_regime, zone.recency_days = calculate_zone_strength(cluster, now)
        zones.append(zone)
    
    # Sort by strength (strongest first)
    zones.sort(key=lambda z: z.strength, reverse=True)
    return zones


def get_all_zones(lookback_days=30):
    """Get zones for all tokens (for dashboard/display)."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token, direction FROM sl_memory
            WHERE hit_time > NOW() - INTERVAL '%s days'
        """, (lookback_days,))
        pairs = cur.fetchall()
    finally:
        conn.close()
    
    all_zones = {}
    for token, direction in pairs:
        zones = get_sl_zones(token, direction, lookback_days)
        if zones:
            key = f"{token}_{direction}"
            all_zones[key] = zones
    
    return all_zones


# ── Entry Distance Filter ─────────────────────────────────────────────────────

def entry_distance_filter(token, direction, entry_price, atr):
    """
    Check if entry is too close to a death zone.
    Returns: (pass: bool, score: float, reason: str, closest_zone: SLZone or None)

    Logic:
    - LONG entry: check RESISTANCE zones above entry (previous LONG stops)
    - SHORT entry: check SUPPORT zones below entry (previous SHORT stops)
    """
    if not entry_price or entry_price <= 0:
        return (True, 1.0, "Invalid entry price", None)

    zones = get_sl_zones(token, direction, lookback_days=30)
    
    if not zones:
        return (True, 1.0, "No death zones found", None)
    
    # For LONG: check zones ABOVE entry (resistance)
    # For SHORT: check zones BELOW entry (support)
    if direction == 'LONG':
        danger_zones = [z for z in zones if z.center > entry_price]
    else:
        danger_zones = [z for z in zones if z.center < entry_price]
    
    if not danger_zones:
        return (True, 1.0, "No zones in path", None)
    
    # Find closest zone
    closest = min(danger_zones, key=lambda z: abs(z.center - entry_price))
    distance_pct = abs(closest.center - entry_price) / entry_price * 100
    
    # Block check
    if distance_pct < ENTRY_BLOCK_DISTANCE_PCT and closest.strength >= ENTRY_BLOCK_STRENGTH_MIN:
        score = closest.strength * (1 - distance_pct / ENTRY_BLOCK_DISTANCE_PCT)
        return (False, score,
                f"BLOCKED: {distance_pct:.1f}% from death zone at {closest.center} (strength={closest.strength:.2f})",
                closest)
    
    # Watch check
    if distance_pct < ENTRY_WATCH_DISTANCE_PCT and closest.strength >= ENTRY_WATCH_STRENGTH_MIN:
        score = closest.strength * 0.5 * (1 - (distance_pct - ENTRY_BLOCK_DISTANCE_PCT) /
                                          (ENTRY_WATCH_DISTANCE_PCT - ENTRY_BLOCK_DISTANCE_PCT))
        return (True, 1 - score,
                f"WARNING: {distance_pct:.1f}% from death zone (strength={closest.strength:.2f})",
                closest)
    
    return (True, 1.0, f"Safe — {distance_pct:.1f}% from nearest zone", closest)


# ── Exit Tightening Check ─────────────────────────────────────────────────────

def zone_aware_exit_check(token, direction, current_price, atr):
    """
    Check if price is approaching a death zone during an active trade.
    Returns: {'action': str, 'reason': str, 'new_trail_pct': float or None, 'zone': SLZone or None}
    """
    if not current_price or current_price <= 0:
        return {'action': 'hold', 'reason': 'Invalid price', 'new_trail_pct': None, 'zone': None}

    zones = get_sl_zones(token, direction, lookback_days=30)
    
    if not zones:
        return {'action': 'hold', 'reason': 'No zones', 'new_trail_pct': None, 'zone': None}
    
    # Find zones in the PATH of the trade
    if direction == 'LONG':
        path_zones = [z for z in zones if z.center > current_price]
    else:
        path_zones = [z for z in zones if z.center < current_price]
    
    if not path_zones:
        return {'action': 'hold', 'reason': 'No zones ahead', 'new_trail_pct': None, 'zone': None}
    
    closest = min(path_zones, key=lambda z: abs(z.center - current_price))
    
    if atr and atr > 0:
        distance_atr = abs(closest.center - current_price) / atr
    else:
        # Unknown ATR — cannot compute distance in ATR terms, default to hold
        return {'action': 'hold', 'reason': 'ATR unknown, cannot assess zone distance', 'new_trail_pct': None, 'zone': None}
    
    if distance_atr < EXIT_TIGHTEN_ATR:
        return {
            'action': 'tighten_trail',
            'reason': f'Price {distance_atr:.1f} ATR from death zone at {closest.center}',
            'new_trail_pct': EXIT_TIGHTEN_TRAIL_PCT,
            'zone': closest,
        }
    elif distance_atr < EXIT_WATCH_ATR:
        return {
            'action': 'watch',
            'reason': f'Approaching death zone {distance_atr:.1f} ATR away',
            'new_trail_pct': None,
            'zone': closest,
        }
    
    return {'action': 'hold', 'reason': 'Safe distance', 'new_trail_pct': None, 'zone': None}


# ── Position Sizing ────────────────────────────────────────────────────────────

def zone_adjusted_size(base_size, token, direction, entry_price, atr):
    """
    Reduce position size when a death zone is ahead.
    Returns: adjusted size (same or smaller than base_size).
    """
    if base_size <= 0:
        return base_size

    zones = get_sl_zones(token, direction, lookback_days=30)

    if not zones or not atr or atr <= 0 or entry_price <= 0:
        return base_size
    
    # Find zones in path
    if direction == 'LONG':
        path_zones = [z for z in zones if z.center > entry_price]
    else:
        path_zones = [z for z in zones if z.center < entry_price]
    
    if not path_zones:
        return base_size
    
    closest = min(path_zones, key=lambda z: abs(z.center - entry_price))
    distance_atr = abs(closest.center - entry_price) / atr
    
    if distance_atr < SIZE_REDUCE_1_ATR:
        return base_size * 0.5
    elif distance_atr < SIZE_REDUCE_2_ATR:
        return base_size * 0.75
    
    return base_size


# ── Cache ──────────────────────────────────────────────────────────────────────

_zone_cache = {}  # {token_direction: (timestamp, zones)}
_CACHE_TTL = 300  # 5 minutes


def get_sl_zones_cached(token, direction, lookback_days=30):
    """Cached version of get_sl_zones — refreshes every 5 minutes."""
    key = f"{token}_{direction}"
    now = time.time()

    # Evict expired entries periodically
    if len(_zone_cache) > 100:
        expired = [k for k, (t, _) in _zone_cache.items() if now - t >= _CACHE_TTL]
        for k in expired:
            del _zone_cache[k]

    if key in _zone_cache:
        cached_time, cached_zones = _zone_cache[key]
        if now - cached_time < _CACHE_TTL:
            return cached_zones

    zones = get_sl_zones(token, direction, lookback_days)
    _zone_cache[key] = (now, zones)
    return zones


def clear_cache():
    """Clear the zone cache (for testing or after new data)."""
    global _zone_cache
    _zone_cache = {}


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='SL Memory Zone Engine')
    parser.add_argument('token', help='Token to analyze (e.g., SOL, HYPE)')
    parser.add_argument('--direction', '-d', default='LONG', choices=['LONG', 'SHORT'])
    parser.add_argument('--days', type=int, default=30, help='Lookback days')
    parser.add_argument('--all', action='store_true', help='Show all zones for all tokens')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()
    
    if args.all:
        all_zones = get_all_zones(args.days)
        for key, zones in sorted(all_zones.items()):
            print(f"\n=== {key} ===")
            for z in zones:
                print(f"  SL={z.center:.4f}  hits={z.hit_count}  strength={z.strength:.3f}  "
                      f"regime={z.dominant_regime}  days_ago={z.recency_days:.1f}")
    else:
        zones = get_sl_zones(args.token, args.direction, args.days)
        if not zones:
            print(f"No zones found for {args.token} {args.direction}")
        else:
            print(f"\n=== {args.token} {args.direction} — SL Zones ===")
            for z in zones:
                print(f"  SL={z.center:.4f}  hits={z.hit_count}  strength={z.strength:.3f}  "
                      f"regime={z.dominant_regime}  days_ago={z.recency_days:.1f}")
            
            # Entry filter test
            print(f"\n--- Entry Filter Test ---")
            # Use current price estimate from last hit
            if zones:
                test_price = zones[0].center * 0.98  # 2% below closest zone
                passed, score, reason, _ = entry_distance_filter(args.token, args.direction, test_price, 1.0)
                print(f"  Test entry at {test_price:.4f}: {'PASS' if passed else 'BLOCK'} — {reason}")
