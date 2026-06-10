"""
zscore_rising — standalone momentum onset detector.
Fires when z-score CROSSES threshold AND is actively rising (acceleration confirmed).
Eliminates noise from persistently elevated z-scores that plague plain z-score threshold signals.

Logic: prev_z < TH <= cur_z (crossing up) + z_velocity > 0 (rising)
       prev_z > -TH >= cur_z (crossing down) + z_velocity < 0 (falling)
"""

import json
import math
import sqlite3
import time
from typing import Optional

from hermes_constants import (
    ZSCORE_RISING_ENABLED,
    ZSCORE_RISING_PLUS_ENABLED,
    ZSCORE_RISING_MINUS_ENABLED,
    ZSCORE_RISING_LOOKBACK,
    ZSCORE_RISING_THRESHOLD,
    ZSCORE_RISING_VEL_BARS,
    ZSCORE_RISING_COOLDOWN_BARS,
    ZSCORE_RISING_MAX_BARS,
    ZSCORE_RISING_CONF_MIN,
    ZSCORE_RISING_CONF_SCALE,
    ZSCORE_RISING_CONF_MAX,
    SHORT_BLACKLIST,
    LONG_BLACKLIST,
)
from signal_schema import add_signal

_DB_PATH = "/root/.hermes/data/signals_hermes.db"

# In-memory cooldown tracker: (token, direction) -> last_fired_bar
_last_signal: dict[tuple[str, str], int] = {}


def compute_zscore(values: list[float], LB: int) -> Optional[float]:
    """Rolling z-score of the LAST LB elements in values."""
    n = len(values)
    if n < LB:
        return None
    window = values[-LB:]
    mean = sum(window) / LB
    variance = sum((x - mean) ** 2 for x in window) / LB
    std = math.sqrt(variance)
    if std == 0:
        return None
    cur = values[-1]
    return (cur - mean) / std


def scan_zscore_rising_signals(prices_dict: dict[str, list[float]]) -> list[dict]:
    """
    Scan all tokens for z-score crossing + rising momentum onset.
    Per-bar iteration: for each bar i (starting at LB), compute z-score of
    window ending at i vs window ending at i-1, detect crossing, confirm rising.
    """
    if not ZSCORE_RISING_ENABLED:
        return []

    signals = []
    LB = ZSCORE_RISING_LOOKBACK
    TH = ZSCORE_RISING_THRESHOLD
    VEL_BARS = ZSCORE_RISING_VEL_BARS
    COOLDOWN = ZSCORE_RISING_COOLDOWN_BARS
    CONF_MIN = ZSCORE_RISING_CONF_MIN
    CONF_SCALE = ZSCORE_RISING_CONF_SCALE
    CONF_MAX = ZSCORE_RISING_CONF_MAX

    for token, closes in prices_dict.items():
        if len(closes) < LB + VEL_BARS + 2:
            continue

        last_long_bar = -COOLDOWN
        last_short_bar = -COOLDOWN

        # Iterate per-bar: i is the current bar index (0-based, oldest-first)
        for i in range(LB, len(closes)):
            # z_curr: z-score of window [0..i] (bars ending at i)
            z_curr = compute_zscore(closes[: i + 1], LB)
            if z_curr is None:
                continue

            # z_prev: z-score of window [0..i-1] (bars ending at i-1)
            z_prev = compute_zscore(closes[:i], LB) if i >= LB else None
            if z_prev is None:
                continue

            # z_past: z-score of window [0..i-VEL_BARS] (bars ending i-VEL_BARS ago)
            z_past_win = closes[: i + 1 - VEL_BARS]
            z_past = compute_zscore(z_past_win, LB) if len(z_past_win) >= LB else None
            z_vel = (z_curr - z_past) if z_past is not None else 0.0

            # === LONG: z crosses above +TH threshold AND rising ===
            if ZSCORE_RISING_PLUS_ENABLED:
                if z_prev < TH <= z_curr and z_vel > 0:
                    if token in LONG_BLACKLIST:
                        continue
                    if i - last_long_bar <= COOLDOWN:
                        continue
                    confidence = min(CONF_MIN + abs(z_curr) * CONF_SCALE, CONF_MAX)
                    signals.append({
                        "token": token,
                        "direction": "long",
                        "signal_type": "zscore_rising_long",
                        "source": "zscore-rising+",
                        "confidence": confidence,
                        "z_score": round(z_curr, 3),
                        "z_velocity": round(z_vel, 3),
                        "price": closes[i],
                        "atr_pct": 0.0,
                    })
                    last_long_bar = i

            # === SHORT: z crosses below -TH threshold AND falling ===
            if ZSCORE_RISING_MINUS_ENABLED:
                if z_prev > -TH >= z_curr and z_vel < 0:
                    if token in SHORT_BLACKLIST:
                        continue
                    if i - last_short_bar <= COOLDOWN:
                        continue
                    confidence = min(CONF_MIN + abs(z_curr) * CONF_SCALE, CONF_MAX)
                    signals.append({
                        "token": token,
                        "direction": "short",
                        "signal_type": "zscore_rising_short",
                        "source": "zscore-rising-",
                        "confidence": confidence,
                        "z_score": round(z_curr, 3),
                        "z_velocity": round(z_vel, 3),
                        "price": closes[i],
                        "atr_pct": 0.0,
                    })
                    last_short_bar = i

    return signals


def run(prices_dict: dict[str, list[float]] = None) -> int:
    """
    Hermes signal entry point.
    Returns: number of signals emitted.
    Prices dict: {token: [close_prices]} — oldest-first (ASC).
    DB query returns DESC (newest-first); run() reverses each token's list.
    """
    if not ZSCORE_RISING_ENABLED:
        return 0

    if prices_dict is None:
        prices_dict = {}
        conn = sqlite3.connect(_DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, price FROM price_history
            WHERE price IS NOT NULL AND price > 0
            ORDER BY token, timestamp DESC
        """)
        rows = cur.fetchall()
        conn.close()

        from collections import defaultdict
        token_prices: dict[str, list[float]] = defaultdict(list)
        for token, price in rows:
            token_prices[token].append(price)

        # DB returns newest-first (DESC), scan expects oldest-first (ASC)
        for token, prices in token_prices.items():
            prices_dict[token] = list(reversed(prices[:ZSCORE_RISING_MAX_BARS]))

    sigs = scan_zscore_rising_signals(prices_dict)
    for sig in sigs:
        add_signal(
            token=sig["token"],
            direction=sig["direction"],
            signal_type=sig["signal_type"],
            source=sig["source"],
            confidence=sig["confidence"],
            price=sig["price"],
            atr_pct=sig["atr_pct"],
        )
    return len(sigs)


if __name__ == "__main__":
    print(f"ZSCORE_RISING_ENABLED={ZSCORE_RISING_ENABLED}")
    print(f"  LB={ZSCORE_RISING_LOOKBACK}, TH={ZSCORE_RISING_THRESHOLD}")
    print(f"  VEL_BARS={ZSCORE_RISING_VEL_BARS}, COOLDOWN={ZSCORE_RISING_COOLDOWN_BARS}")
    print(f"  MAX_BARS={ZSCORE_RISING_MAX_BARS}")
    print(f"  CONF: min={ZSCORE_RISING_CONF_MIN}, scale={ZSCORE_RISING_CONF_SCALE}, max={ZSCORE_RISING_CONF_MAX}")
    count = run()
    print(f"Signals emitted: {count}")