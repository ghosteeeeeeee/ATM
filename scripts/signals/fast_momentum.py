# Extracted from signal_gen.py lines 1874-2015 — fast-momentum signal
#!/usr/bin/env python3
"""
fast_momentum.py — Explosive Short-Term Momentum Signal.

Detects explosive short-term momentum bursts by comparing 5m z-score
acceleration against 30m momentum. When the short window shows much
stronger momentum than the medium window, it signals a quick move.

Generates 'fast-momentum+' (LONG) or 'fast-momentum-' (SHORT) signals
with 1.3x source weight in signal_compactor.

Signal type: fast_momentum
Sources:     fast-momentum+, fast-momentum-
"""
import os, sys, statistics

# ── Paths ─────────────────────────────────────────────────────────────────────
SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)

def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass

# ── Signal constants ───────────────────────────────────────────────────────────
ACCEL_THRESHOLD  = 0.15   # minimum z-acceleration to qualify
MIN_CONFIDENCE   = 62     # minimum confidence score to write signal
MIN_TRADE_INTERVAL_MINUTES = 10   # dedup window (same as signal_gen)
TRADE_LOG_FILE   = '/var/www/hermes/data/recent_trades.json'
MIN_PRICE_ROWS   = 60     # minimum 1m bars for z-score computation

# ── Feature flags ──────────────────────────────────────────────────────────────
# Gating — set to False in hermes_constants or env to disable entirely
try:
    from hermes_constants import (
        FAST_MOMENTUM_ENABLED,
        FAST_MOMENTUM_PLUS_ENABLED,
        FAST_MOMENTUM_MINUS_ENABLED,
    )
except Exception:
    FAST_MOMENTUM_ENABLED      = True
    FAST_MOMENTUM_PLUS_ENABLED = True
    FAST_MOMENTUM_MINUS_ENABLED = True

# ── Imports (mirror signal_gen.py) ─────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import (
    get_all_latest_prices,
    get_price_history,
    add_signal,
    price_age_minutes,
    get_latest_price,
    expire_pending_signals,
)
from position_manager import get_open_positions as _get_open_pos
from hyperliquid_exchange import is_delisted
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST

# Speed tracker (optional — degrade gracefully)
try:
    from speed_tracker import SpeedTracker, get_token_speed
    speed_tracker = SpeedTracker()
except Exception:
    speed_tracker = None


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: _fast_zscore (copied from signal_gen.py ~2018)
# ═══════════════════════════════════════════════════════════════════════════════

def _fast_zscore(prices_subset):
    """Compute z-score for a subset of prices. Returns None if insufficient data."""
    if len(prices_subset) < 5:
        return None
    mu = statistics.mean(prices_subset)
    std = statistics.stdev(prices_subset) if len(prices_subset) > 1 else 1
    if std == 0:
        return None
    return (prices_subset[-1] - mu) / std


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: compute_zscore_velocity (copied from signal_gen.py ~450)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_zscore_velocity(prices, window=240):
    """Compute how the z-score has CHANGED over recent bars."""
    if len(prices) < window:
        return 0.0
    recent  = prices[-window:]
    earlier = prices[-window*2:-window] if len(prices) >= window * 2 else prices[:window]
    if len(recent) < 5 or len(earlier) < 5:
        return 0.0
    z_now   = _fast_zscore(recent)
    z_prior = _fast_zscore(earlier)
    if z_now is None or z_prior is None:
        return 0.0
    return z_now - z_prior


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: recent_trade_exists (copied from signal_gen.py ~823)
# ═══════════════════════════════════════════════════════════════════════════════

def recent_trade_exists(token, minutes=MIN_TRADE_INTERVAL_MINUTES):
    """Return True if token was traded in last N minutes."""
    try:
        if not os.path.exists(TRADE_LOG_FILE):
            return False
        with open(TRADE_LOG_FILE) as f:
            data = json.load(f) if os.path.getsize(TRADE_LOG_FILE) > 0 else {}
    except Exception:
        return False
    cutoff = time.time() - minutes * 60
    return any(
        entry.get('time', 0) >= cutoff
        for entry in data.get(token.upper(), [])
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: is_reasonable_price (copied from signal_gen.py ~109)
# ═══════════════════════════════════════════════════════════════════════════════

def is_reasonable_price(token: str, price) -> bool:
    """Return False if price is corrupted (None, zero, negative, impossibly high/low)."""
    if price is None or price <= 0:
        return False
    if price > 1_000_000:
        return False
    if price < 0.00001:
        return False
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: get_momentum_stats (copied from signal_gen.py ~619)
# ═══════════════════════════════════════════════════════════════════════════════

def get_momentum_stats(token, rows=None):
    """
    Compute RSI and MACD histogram for a token.
    Returns: {rsi_14, macd_hist} or None on error.
    """
    try:
        if rows is None:
            rows = get_price_history(token, lookback_minutes=240)
        if len(rows) < 30:
            return None
        closes = [r[1] for r in rows]

        # RSI-14
        delta = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gain = [d if d > 0 else 0 for d in delta]
        loss = [-d if d < 0 else 0 for d in delta]
        avg_gain = sum(gain[-14:]) / 14 if len(gain) >= 14 else 0
        avg_loss = sum(loss[-14:]) / 14 if len(loss) >= 14 else 0
        rs = avg_gain / avg_loss if avg_loss != 0 else 100
        rsi_14 = 100 - (100 / (1 + rs)) if avg_loss != 0 else 100

        # MACD (12, 26, 9)
        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        macd_line = ema12 - ema26
        signal_line = _ema([macd_line] * 9, 9) if len(closes) >= 26 else macd_line
        macd_hist = macd_line - signal_line

        return {'rsi_14': rsi_14, 'macd_hist': macd_hist}
    except Exception:
        return None


def _ema(values, period):
    """Compute EMA for a list of values."""
    if len(values) < period:
        return values[-1] if values else 0
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


# ═══════════════════════════════════════════════════════════════════════════════
# Main run() function
# ═══════════════════════════════════════════════════════════════════════════════

def run():
    """
    Entry point — no arguments, fetches prices_dict internally.

    Returns:
        int: number of fast-momentum signals written to DB.
    """
    import json, time

    # NOTE: FAST_MOMENTUM_ENABLED guard is in signal_gen.py (inline version).
    # Per-direction FAST_MOMENTUM_PLUS/MINUS_ENABLED checks remain active.
    # This registry version is called by signals_runner.py — Layer 2 add_signal()
    # guard handles final per-source filtering.

    prices_dict = get_all_latest_prices()
    open_pos    = {p['token']: p['direction'] for p in _get_open_pos()}
    added       = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if token.upper() in SHORT_BLACKLIST or token.upper() in LONG_BLACKLIST:
            continue
        if is_delisted(token.upper()):
            continue

        price = data['price']
        if not is_reasonable_price(token, price):
            continue

        # ── Price history for multi-window z-score analysis ───────────────────
        rows = get_price_history(token, lookback_minutes=240)
        if len(rows) < MIN_PRICE_ROWS:
            continue
        prices = [r[1] for r in rows]

        # ── Compute z-scores at different windows ──────────────────────────────
        z_5m  = _fast_zscore(prices[-5:])  if len(prices) >= 5  else None
        z_30m = _fast_zscore(prices[-30:]) if len(prices) >= 30 else None
        z_60m = _fast_zscore(prices[-60:]) if len(prices) >= 60 else None

        if z_5m is None or z_30m is None or z_60m is None:
            continue

        # ── Speed percentile filter (Binance-style top movers) ─────────────────
        spd = None
        if speed_tracker is not None:
            spd = speed_tracker.get_token_speed(token)
        speed_pctl = spd.get('speed_percentile', 50.0) if spd else 50.0
        if speed_pctl < 70:
            continue  # not a top mover — skip

        # ── Acceleration: short-term z change vs medium-term ──────────────────
        z_accel = z_5m - z_30m

        # ── Velocity ───────────────────────────────────────────────────────────
        velocity = compute_zscore_velocity(prices, window=30)

        # Direction logic
        is_bullish = z_accel > ACCEL_THRESHOLD and velocity > 0
        is_bearish = z_accel < -ACCEL_THRESHOLD and velocity < 0

        if not (is_bullish or is_bearish):
            continue

        # Direction-gated enables
        if is_bullish and not FAST_MOMENTUM_PLUS_ENABLED:
            continue
        if is_bearish and not FAST_MOMENTUM_MINUS_ENABLED:
            continue

        # ── Confidence scoring ─────────────────────────────────────────────────
        accel_magnitude = abs(z_accel)
        confidence = min(95.0, 60.0 + accel_magnitude * 100)

        if confidence < MIN_CONFIDENCE:
            continue

        direction = 'LONG' if is_bullish else 'SHORT'
        source    = 'fast-momentum+' if is_bullish else 'fast-momentum-'

        # ── Additional filter: 5m z should be more extreme than 60m z ─────────
        if is_bullish and not (z_5m < z_60m - 0.1):
            continue  # not a true upside acceleration
        if is_bearish and not (z_5m > z_60m + 0.1):
            continue  # not a true downside acceleration

        # ── RSI / MACD confirmation ────────────────────────────────────────────
        mom     = get_momentum_stats(token)
        rsi_val = mom.get('rsi_14')   if mom else None
        macd_hist = mom.get('macd_hist') if mom else None

        if direction == 'LONG':
            if rsi_val is not None and rsi_val > 70:
                continue  # overbought — skip LONG
            if macd_hist is not None and macd_hist < 0:
                continue  # MACD bearish — skip LONG

        if direction == 'SHORT':
            if rsi_val is not None and rsi_val < 45:
                continue  # oversold — skip SHORT
            if macd_hist is not None and macd_hist > 0:
                continue  # MACD bullish — skip SHORT

        # ── Write signal ──────────────────────────────────────────────────────
        sid = add_signal(
            token          = token,
            direction      = direction,
            signal_type    = 'fast_momentum',
            source         = source,
            confidence     = confidence,
            value          = round(confidence, 1),
            price          = price,
            exchange       = 'hyperliquid',
            timeframe      = '5m',
            z_score        = z_5m,
            z_score_tier   = 'fast-accel' if is_bullish else 'fast-decel',
            rsi_14         = rsi_val,
            macd_hist      = macd_hist,
        )
        if sid:
            added += 1

    if added > 0:
        _log(f'  Fast-momentum: {added} fast-momentum signals written to DB')
    return added


if __name__ == '__main__':
    n = run()
    print(f'fast_momentum: {n} signals added')
