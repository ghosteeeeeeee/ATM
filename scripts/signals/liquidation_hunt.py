#!/usr/bin/env python3
"""
Signal: Liquidation Stop Hunt

Fires when:
1. Price approaches a liquidation cluster from tracked wallets
2. Order book shows thin liquidity on the hunt side
3. Funding rate confirms crowded trade direction

Entry: Before the cascade (front-run the stop hunt)
Exit: After cascade completes (cluster is consumed)

This is a CONTRARIAN signal — we trade INTO the stop hunt, not with it.
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *

from hermes_constants import (
    STOP_HUNT_DISTANCE_PCT,
    STOP_HUNT_MIN_CLUSTER_USD,
    STOP_HUNT_MIN_SCORE,
)

try:
    LIQ_CLUSTERS_FILE = os.path.join(HERMES_DATA, "liquidation_clusters.json")
except NameError:
    LIQ_CLUSTERS_FILE = "/root/.hermes/data/liquidation_clusters.json"


def load_liquidation_data():
    """Load latest liquidation cluster data."""
    try:
        with open(LIQ_CLUSTERS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def get_signal(token: str, timeframe: str, **kwargs) -> list:
    """
    Check for liquidation stop hunt opportunity for a token.

    Returns signal dict if conditions are met, None otherwise.
    """
    data = load_liquidation_data()
    if not data:
        return []

    token_upper = token.upper()
    clusters = data.get("liquidation_clusters", {}).get(token_upper, [])
    stop_hunts = data.get("stop_hunt_signals", [])

    # Check if there's a stop hunt signal for this token
    hunt = None
    for sh in stop_hunts:
        if sh["coin"] == token_upper:
            hunt = sh
            break

    if not hunt:
        return []

    # Filter by our thresholds
    if hunt["score"] < STOP_HUNT_MIN_SCORE:
        return []
    if hunt["cluster_size_usd"] < STOP_HUNT_MIN_CLUSTER_USD:
        return []
    if abs(hunt["distance_pct"]) > STOP_HUNT_DISTANCE_PCT:
        return []

    # The signal: trade OPPOSITE to the hunt direction
    # If hunt is DOWN (longs getting liquidated) → go LONG (contrarian)
    # If hunt is UP (shorts getting liquidated) → go SHORT (contrarian)
    if hunt["hunt_direction"] == "DOWN":
        direction = "LONG"
        entry_zone = hunt["cluster_price"] * 1.002  # Just above cluster
        stop_loss = hunt["cluster_price"] * 0.985   # Below cluster
        take_profit = hunt["current_price"] * 1.015  # Back to current + 1.5%
    else:
        direction = "SHORT"
        entry_zone = hunt["cluster_price"] * 0.998  # Just below cluster
        stop_loss = hunt["cluster_price"] * 1.015   # Above cluster
        take_profit = hunt["current_price"] * 0.985  # Back to current - 1.5%

    # Compute confidence from multiple factors
    base_conf = min(0.8, hunt["score"] / 100)
    book_bonus = 0.1 if hunt.get("book_thin") else 0
    cluster_bonus = min(0.1, hunt["cluster_size_usd"] / 200000)
    confidence = round(base_conf + book_bonus + cluster_bonus, 2)

    return [{
        "token": token_upper,
        "signal_name": "liquidation_hunt",
        "direction": direction,
        "timeframe": timeframe,
        "confidence": confidence,
        "value": hunt["score"],
        "price": hunt["current_price"],
        "exchange": "hyperliquid",
        "notes": (
            f"Stop hunt {hunt['signal']}: {hunt['hunt_direction']} "
            f"cluster ${hunt['cluster_price']:.4f} "
            f"({hunt['distance_pct']:+.2f}%) "
            f"size=${hunt['cluster_size_usd']:,.0f} "
            f"({hunt['position_count']} positions, "
            f"max {hunt['max_leverage']}x leveraged) "
            f"book_thin={hunt.get('book_thin', False)} "
            f"imbalance={hunt.get('imbalance_ratio', 0):.2f}"
        ),
        "metadata": {
            "cluster_price": hunt["cluster_price"],
            "distance_pct": hunt["distance_pct"],
            "cluster_size_usd": hunt["cluster_size_usd"],
            "position_count": hunt["position_count"],
            "max_leverage": hunt["max_leverage"],
            "hunt_direction": hunt["hunt_direction"],
            "book_thin": hunt.get("book_thin", False),
            "imbalance_ratio": hunt.get("imbalance_ratio", 1.0),
            "entry_zone": entry_zone,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward": round(abs(take_profit - entry_zone) /
                                 max(abs(entry_zone - stop_loss), 0.001), 2),
        },
    }]


# ─── Standalone Test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    data = load_liquidation_data()
    if not data:
        print("No liquidation data found. Run liquidation_map.py first.")
        sys.exit(1)

    print(f"Liquidation data age: {time.time() - data.get('timestamp', 0):.0f}s")
    print(f"Total liq exposure: ${data.get('total_liquidation_exposure_usd', 0):,.0f}")
    print()

    # Check all coins we trade
    signals = []
    from tokens import get_tradeable_tokens
    for token in get_tradeable_tokens():
        sigs = get_signal(token, "15m")
        signals.extend(sigs)

    if signals:
        print(f"🚨 Found {len(signals)} liquidation hunt signals:")
        for sig in sorted(signals, key=lambda x: x["confidence"], reverse=True):
            m = sig["metadata"]
            print(f"  {sig['direction']:5} {sig['token']:8} "
                  f"conf={sig['confidence']:.2f} "
                  f"cluster=${m['cluster_price']:.4f} "
                  f"({m['distance_pct']:+.2f}%) "
                  f"RR={m['risk_reward']:.1f} "
                  f"size=${m['cluster_size_usd']:,.0f}")
    else:
        print("No liquidation hunt signals at this time.")
