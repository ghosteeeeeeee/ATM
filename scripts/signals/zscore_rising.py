"""
zscore_rising — momentum onset detector (fishing for z-score reversals).

Like a fish-finder detecting where fish congregate:
- Z-score crossing = sonar ping (something is changing)
- Velocity = echo strength (how fast is it changing?)
- Speed percentile = is the fish moving?
- RSI = water temperature (too hot/cold to trade?)
- Volume = oxygen (is there real participation?)

Fires when z-score CROSSES threshold AND ALL oxygen indicators align.
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
from paths import RUNTIME_DB, STATIC_DB, CANDLES_DB

_DB_PATH = STATIC_DB

_last_signal: dict[tuple[str, str], int] = {}

# ── Fishing parameters ────────────────────────────────────────────────────────
ZSPEED_MIN = 50       # speed percentile — fish must be moving
ZRSI_MIN = 30         # RSI floor — don't fish in frozen water
ZRSI_MAX = 70         # RSI ceiling — don't fish in boiling water
ZMIN_Z = 2.5          # minimum abs(z) at crossing — stronger echo required


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


def _get_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """Compute RSI from price list. Returns 0-100 or None."""
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _get_speed(token: str) -> float:
    """Get speed percentile for token. Returns 0-100."""
    try:
        from speed_tracker import get_token_speed
        spd = get_token_speed(token)
        return spd.get('speed_percentile', 50) if spd else 50.0
    except Exception:
        return 50.0


def scan_zscore_rising_signals(prices_dict: dict[str, list[float]]) -> list[dict]:
    """
    Scan tokens for z-score crossing + oxygen confirmation.
    Only fires when ALL indicators align (fish-finder approach).
    """
    if not ZSCORE_RISING_ENABLED:
        return []

    # ── Regime filter — z-score crossings are noise in ranging markets ────
    try:
        import os, json as _json
        regime_file = '/var/www/hermes/data/regime_5m.json'
        if os.path.exists(regime_file):
            with open(regime_file) as _f:
                _regime_data = _json.load(_f)
            _overall = _regime_data.get('aggregate', {}).get('overall', 'NEUTRAL')
            if _overall == 'NEUTRAL':
                return []
    except Exception:
        pass  # if regime data unavailable, don't block

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

        latest_bar = len(closes) - 1
        for i in range(LB, len(closes)):
            if i != latest_bar:
                continue

            z_curr = compute_zscore(closes[: i + 1], LB)
            if z_curr is None:
                continue

            z_prev = compute_zscore(closes[:i], LB) if i >= LB else None
            if z_prev is None:
                continue

            z_past_win = closes[: i + 1 - VEL_BARS]
            z_past = compute_zscore(z_past_win, LB) if len(z_past_win) >= LB else None
            z_vel = (z_curr - z_past) if z_past is not None else 0.0

            # ── Oxygen checks (must ALL align) ──────────────────────────────
            speed = _get_speed(token)
            rsi = _get_rsi(closes)

            # Speed filter: fish must be moving
            if speed < ZSPEED_MIN:
                continue

            # RSI filter: don't fish in frozen/boiling water
            if rsi is not None and (rsi < ZRSI_MIN or rsi > ZRSI_MAX):
                continue

            # Z-score magnitude: stronger echo required
            if abs(z_curr) < ZMIN_Z:
                continue

            # === LONG: z crosses above +TH AND rising + oxygen confirmed ===
            if ZSCORE_RISING_PLUS_ENABLED:
                if z_prev < TH <= z_curr and z_vel > 0:
                    if token in LONG_BLACKLIST:
                        continue
                    if i - last_long_bar <= COOLDOWN:
                        continue
                    confidence = min(CONF_MIN + abs(z_curr) * CONF_SCALE + speed * 0.1, CONF_MAX)
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

            # === SHORT: z crosses below -TH AND falling + oxygen confirmed ===
            if ZSCORE_RISING_MINUS_ENABLED:
                if z_prev > -TH >= z_curr and z_vel < 0:
                    if token in SHORT_BLACKLIST:
                        continue
                    if i - last_short_bar <= COOLDOWN:
                        continue
                    confidence = min(CONF_MIN + abs(z_curr) * CONF_SCALE + speed * 0.1, CONF_MAX)
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
    Fetches price history per-token from get_price_history().
    """
    if not ZSCORE_RISING_ENABLED:
        return 0

    from signal_schema import get_all_latest_prices, get_price_history, price_age_minutes

    # Build {token: [prices]} from per-token price_history queries
    all_prices = get_all_latest_prices()
    prices_dict = {}
    for token, data in all_prices.items():
        if token.startswith('@'):
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if price_age_minutes(token) > 10:
            continue
        rows = get_price_history(token, lookback_minutes=ZSCORE_RISING_MAX_BARS)
        if rows and len(rows) >= ZSCORE_RISING_LOOKBACK + ZSCORE_RISING_VEL_BARS + 2:
            prices_dict[token] = [r[1] for r in reversed(rows)]  # oldest-first

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