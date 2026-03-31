#!/usr/bin/env python3
# Redirect stdin before any imports — prevents deadlock when run via subprocess with
# a writable pipe (hermes-pipeline calls signal_gen with stdout=subprocess.DEVNULL but
# Python 3.12's import machinery can probe stdin on some platforms/configurations).
try:
    import os
    if os.isatty(0):
        pass  # interactive: keep stdin as-is
    else:
        import sys
        sys.stdin = open(os.devnull, 'r')
except Exception:
    pass

"""
signal_gen.py — Hermes signal generation with momentum-based z-score analysis.

Architecture:
  - Z-score percentile rank: how unusual is this z for THIS token? (rolling 500-bar)
  - Z-score velocity: is z rising or falling? (momentum direction)
  - Phase detection: quiet | building | accelerating | exhaustion | extreme
  - LONG: rising z + moderate-high percentile rank
  - SHORT: falling z from exhaustion zone + confirmation
  - Entry: >=65 | Auto-approve: >=85
"""
import sys, sqlite3, time, os, json, statistics, math
from functools import lru_cache
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import (
    init_db, DB_PATH, get_all_latest_prices, get_price_history,
    get_latest_price, add_signal, set_cooldown, get_cooldown,
    price_age_minutes, approve_signal, update_signal_decision,
    mark_signal_processed
)
from hyperliquid_exchange import is_delisted

# ── In-memory cache for z-scores (avoids repeated SQLite reads per token) ──────
# Key: token → (z_1h, tier_1h, z_4h, tier_4h, z_30m, tier_30m, z_24h, tier_24h, ts)
_ZSCORE_CACHE = {}
_ZSCORE_CACHE_TTL = 60  # seconds

# Module-level stop signal for bg volume prefetch thread.
# Must be module-level so the daemon thread can read it after run() returns.
_STOP_VOL_PREFETCH = None

LOG_FILE = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ─── Momentum phase thresholds ─────────────────────────────────
# Based on z-score percentile rank (how unusual for this token)
PHASE_BUILDING    = 60    # percentile ≥60 → momentum starting
PHASE_ACCELERATING= 75    # percentile ≥75 → strong momentum
PHASE_EXHAUSTION  = 88    # percentile ≥88 → late phase, watch for exit
PHASE_EXTREME     = 95    # percentile ≥95 → exhaustion/mean-reversion territory

# Entry score thresholds
ENTRY_THRESHOLD   = 55    # min score to add signal
AUTO_APPROVE      = 95    # ≥ this → auto-approve (≥95 no AI needed, 65-94 → AI review)
EXIT_THRESHOLD    = 55    # opposite signal ≥ this → consider closing

# Z-score lookback for percentile ranking (in price rows, ~1 row/min)
ZSCORE_HISTORY    = 500   # compute percentile from last 500 bars

# ─── Scoring weights ────────────────────────────────────────────
W_PERCENTILE      = 3.0   # percentile rank is primary signal
W_VELOCITY        = 2.0   # momentum direction (rising/falling z)
W_RSI             = 1.0   # RSI confirmation
W_MACD            = 0.8   # MACD confirmation
W_VOLUME          = 1.5   # volume rate-of-change confirmation

# ─── Timeframe windows ──────────────────────────────────────────
TF_WINDOWS = [
    ('1m',  20),   # 20 minutes
    ('5m',  60),   # 1 hour
    ('15m', 120),  # 2 hours
    ('30m', 240),  # 4 hours
    ('1h',  480),  # 8 hours
    ('4h',  1440),  # 24 hours
]

# ─── Token Universe ────────────────────────────────────────────────
# Scan all tokens with prices, filtered by is_delisted at scan time.
# No top-150 restriction needed — is_delisted() handles dead tokens.

def _get_top_tokens():
    """Return all tokens that have a price (full universe, no volume cap)."""
    prices = get_all_latest_prices()
    return list(prices.keys())

# ─── Broad Market Trend Tokens (for regime override) ─────────────────
BROAD_MARKET_TOKENS = ['BTC', 'ETH', 'SOL']

# ─── LONG Trend Filter Thresholds ───────────────────────────────────
# Require longer TFs to be below these z-score thresholds for LONG entry
LONG_1H_Z_MAX   = +0.5    # 1H z-score must be below this (negative = suppressed)
LONG_4H_Z_MAX   = +0.3    # 4H z-score must be below this
LONG_30M_Z_MAX  = +0.5    # 30m z-score must be below this
LONG_AGREE_TFS  = 2       # Require at least 2 of (1h, 4h, 30m) to agree
# Broad market trend: if BTC+ETH+SOL avg 4h z > this, block LONGs
BROAD_UPTEND_Z   = +1.0    # If avg 4h z > +1.0 → block all LONG entries

# ─── Per-Token Rate Limiting ─────────────────────────────────────────
MIN_TRADE_INTERVAL_MINUTES = 10   # min minutes between trades on same token


# ═══════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'{ts} {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


# ═══════════════════════════════════════════════════════════════
# Core Indicator Computations
# ═══════════════════════════════════════════════════════════════

def zscore(prices):
    """Return (z, tier_str) or (None, None)."""
    if len(prices) < 20:
        return None, None
    try:
        mu  = statistics.mean(prices)
        std = statistics.stdev(prices)
        if std == 0:
            return None, None
        z = (prices[-1] - mu) / std
        tier = 'extreme' if abs(z) >= 3 else 'strong' if abs(z) >= 2 else 'moderate' if abs(z) >= 1 else 'weak'
        return round(z, 3), tier
    except:
        return None, None


def rsi(prices, period=14):
    """RSI from close prices. Returns float or None."""
    if len(prices) < period + 2:
        return None
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 2)


def ema(prices, period):
    """Exponential moving average."""
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val


def macd(prices, fast=12, slow=26, signal=9):
    """
    MACD. Returns (macd_line, histogram) or (None, None).
    - MACD line = 12-period EMA - 26-period EMA
    - Signal line = 9-period EMA of MACD line
    - Histogram = MACD line - Signal line
    """
    if len(prices) < slow + signal:
        return None, None
    ef = ema(prices, fast)
    es = ema(prices, slow)
    if ef is None or es is None:
        return None, None

    macd_line = ef - es  # absolute value

    # Compute signal line (9-period EMA of MACD values)
    # Approximate by iterating backwards through prices
    macd_values = []
    for i in range(len(prices) - 1, -1, -1):
        chunk = prices[max(0, i-slow):i+1] if i >= slow else prices[:i+1]
        if len(chunk) >= slow:
            e_slow = ema(chunk, slow)
            e_fast = ema(chunk, fast)
            if e_slow is not None and e_fast is not None:
                macd_values.append(e_fast - e_slow)
            if len(macd_values) > 100:
                break

    if len(macd_values) < signal:
        # Fallback: signal ≈ EMA(slow) approximation
        signal_val = es
    else:
        # Compute 9-period EMA of MACD values
        macd_rev = list(reversed(macd_values))
        k = 2 / (signal + 1)
        signal_val = sum(macd_rev[:signal]) / signal
        for v in macd_rev[signal:]:
            signal_val = v * k + signal_val * (1 - k)

    hist = macd_line - signal_val
    return round(macd_line, 6), round(hist, 6)

# ═══════════════════════════════════════════════════════════════
# Z-Score Percentile Rank
# ═══════════════════════════════════════════════════════════════

def compute_zscore_percentile(prices, window=500):
    """
    Compute directional percentile ranks for the current z-score.
    Returns: (pct_rank, pct_long, pct_short)
      pct_rank   = overall percentile (0-100)
      pct_long   = directional percentile for LONG (how far below mean historically?)
      pct_short  = directional percentile for SHORT (how far above mean historically?)
    """
    if len(prices) < 60:
        return 50.0, 50.0, 50.0

    lookback = prices[-window:] if len(prices) >= window else prices
    current_price = prices[-1]

    # Compute rolling z-scores over lookback window (every 5 bars for speed)
    step = max(1, len(lookback) // 100)
    z_values = []
    for i in range(20, len(lookback), step):
        chunk = lookback[max(0, i-20):i]
        if len(chunk) < 10:
            continue
        mu = statistics.mean(chunk)
        std = statistics.stdev(chunk)
        if std > 0:
            z_values.append((current_price - mu) / std)

    if not z_values:
        return 50.0, 50.0, 50.0

    current_z = z_values[-1]

    # Overall percentile
    below = sum(1 for z in z_values if z <= current_z)
    pct_rank = round((below / len(z_values)) * 100, 1)

    # Directional percentiles based on PRICE position (not z-score)
    # pct_long: what % of historical prices are BELOW current price?
    #   HIGH pct_long = suppressed price = good LONG entry (low = elevated = bad)
    # pct_short: what % of historical prices are ABOVE current price?
    #   HIGH pct_short = elevated price = good SHORT entry (low = suppressed = bad)
    #
    # Use raw price percentile, not z-score percentile, for directional signals.
    # pct_rank (above) = z-score percentile = useful for phase, NOT direction.
    price_below = sum(1 for z in z_values if z <= current_z)
    price_above = sum(1 for z in z_values if z >= current_z)
    pct_long  = round((price_below / len(z_values)) * 100, 1)
    pct_short = round((price_above / len(z_values)) * 100, 1)

    return pct_rank, pct_long, pct_short


# ═══════════════════════════════════════════════════════════════
# Z-Score Velocity (Momentum Direction)
# ═══════════════════════════════════════════════════════════════

def compute_zscore_velocity(prices, window=240):
    """
    Compute how the z-score has CHANGED over recent bars.

    Returns: float
      > 0  → z-score rising (momentum building)
      < 0  → z-score falling (momentum fading)
      ~ 0  → neutral/consolidating

    Uses short vs medium window comparison to detect direction.
    """
    if len(prices) < 60:
        return 0.0

    # Compare z-score now vs z-score N bars ago
    ago = min(60, len(prices) // 4)

    def z_at(prices_subset):
        if len(prices_subset) < 20:
            return None
        mu = statistics.mean(prices_subset)
        std = statistics.stdev(prices_subset) if len(prices_subset) > 1 else 1
        if std == 0:
            return None
        return (prices_subset[-1] - mu) / std

    z_now = z_at(prices[-20:])
    z_then = z_at(prices[-20-ago:-ago]) if len(prices) > ago + 20 else None

    if z_now is None or z_then is None:
        return 0.0

    # Velocity = change in z-score per bar, scaled
    velocity = (z_now - z_then) / ago  # z-change per bar
    return round(velocity, 4)


# ═══════════════════════════════════════════════════════════════
# Phase Detection
# ═══════════════════════════════════════════════════════════════

def detect_phase(percentile, velocity):
    """
    Classify the current market phase based on percentile and velocity.

    Phases:
      quiet        → wait, no trade
      building     → A/B zone, monitor for confirmation
      accelerating → good momentum, trade in direction
      exhaustion   → late phase, protect profits, look for reversal
      extreme      → exhaustion territory, reversal candidates
    """
    if percentile < PHASE_BUILDING and abs(velocity) < 0.05:
        return 'quiet'
    if percentile >= PHASE_EXTREME:
        return 'extreme'
    if percentile >= PHASE_EXHAUSTION:
        return 'exhaustion'
    if percentile >= PHASE_ACCELERATING:
        return 'accelerating'
    if percentile >= PHASE_BUILDING:
        return 'building'
    return 'quiet'


# ═══════════════════════════════════════════════════════════════
# Volume Rate-of-Change (from Hyperliquid recentTrades)
# ═══════════════════════════════════════════════════════════════
_VOL_CACHE = {}   # token → (timestamp, data)
_VOL_TTL   = 55   # seconds — within 1-min pipeline cadence

def _fetch_trades_sync(token):
    """Fetch recentTrades for one token (called from background thread)."""
    key = token.upper()
    now = time.time()
    try:
        import sys as _sys
        _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hyperliquid_exchange import _hl_info
        r = _hl_info({'type': 'recentTrades', 'coin': key})
        # Only cache non-empty results; empty means rate-limited or no data
        if r:
            _VOL_CACHE[key] = (now, r)
    except Exception:
        pass   # Don't cache failures — leave existing entry or skip

def prefetch_volume(tokens):
    """
    Batch-fetch recentTrades for all tokens in parallel using threads.
    Runs in background — pipeline continues without waiting.
    Populates _VOL_CACHE for all tokens within ~3-5 seconds.
    """
    import concurrent.futures
    tokens_to_fetch = [t for t in tokens if t.upper() not in _VOL_CACHE
                       or time.time() - _VOL_CACHE[t.upper()][0] >= _VOL_TTL]
    if not tokens_to_fetch:
        return
    # Use ThreadPoolExecutor — parallel HL calls, ~3-5 sec for 50 tokens
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        ex.map(_fetch_trades_sync, tokens_to_fetch)

def get_volume_roc(token):
    """
    Volume rate-of-change from HL recentTrades.
    Returns (vol_roc, vol_score, vol_reason):
      vol_roc:  recent_avg / older_avg - 1  (normalized, can be negative)
      vol_score: 0-10 pts contribution to signal score
      vol_reason: human-readable string
    Higher recent volume confirms directional momentum.
    """
    trades = _VOL_CACHE.get(token.upper(), (0, []))[1]
    if not trades or len(trades) < 4:
        return 0.0, 0.0, None

    sizes = [abs(float(t['sz'])) for t in trades]
    recent = sizes[:3]
    older  = sizes[3:7] if len(sizes) > 3 else sizes

    avg_recent = sum(recent) / len(recent)
    avg_older  = sum(older)  / len(older)

    if avg_older <= 0:
        return 0.0, 0.0, None

    vol_roc = (avg_recent / avg_older) - 1.0  # e.g. +1.5 = 150% surge

    # Score: cap at ±10 pts. Negative = volume dying (weakens signal)
    # vol_roc of 1.0 = 100% increase → +8 pts
    vol_score = max(-5.0, min(10.0, vol_roc * 5.0))
    vol_score = round(vol_score, 2)

    if abs(vol_roc) < 0.2:
        return vol_roc, 0.0, None  # not enough change to matter

    vol_reason = f'vol={vol_roc:+.0%}'
    return vol_roc, vol_score, vol_reason


# ═══════════════════════════════════════════════════════════════
# Z-Score Multi-Timeframe Analysis
# ═══════════════════════════════════════════════════════════════

def get_tf_zscores(token, max_rows=60480):
    """Z-score across all timeframes. Returns {tf_name: (z, tier)}.
    Cached for 60s — safe for single-run use (run() completes in <60s).
    """
    now = time.time()
    if token in _ZSCORE_CACHE:
        cached_ts, cached_data = _ZSCORE_CACHE[token]
        if now - cached_ts < _ZSCORE_CACHE_TTL:
            return cached_data

    rows = get_price_history(token, lookback_minutes=max_rows)
    if len(rows) < 60:
        _ZSCORE_CACHE[token] = (now, {})
        return {}

    prices = [r[1] for r in rows]
    results = {}
    for tf_name, window in TF_WINDOWS:
        window_prices = prices[-window:] if len(prices) >= window else prices
        z, tier = zscore(window_prices)
        if z is not None:
            results[tf_name] = (z, tier)

    _ZSCORE_CACHE[token] = (now, results)
    return results


def get_momentum_stats(token):
    """
    Compute all momentum metrics for a token.
    Returns: {percentile, percentile_long, percentile_short, velocity, phase,
              avg_z, max_z, min_z, z_direction}
    """
    rows = get_price_history(token, lookback_minutes=60480)
    if len(rows) < 60:
        return None
    prices = [r[1] for r in rows]

    pct_rank, pct_long, pct_short = compute_zscore_percentile(prices, window=ZSCORE_HISTORY)
    velocity   = compute_zscore_velocity(prices)
    percentile = pct_rank  # overall for phase detection

    # Phase based on OVERALL percentile (not direction-specific)
    phase = detect_phase(percentile, velocity)

    zscores = get_tf_zscores(token)
    z_vals  = [z for z, _ in zscores.values()] if zscores else []
    avg_z   = statistics.mean(z_vals) if z_vals else 0
    max_z   = max(z_vals) if z_vals else 0
    min_z   = min(z_vals) if z_vals else 0
    z_direction = 'rising' if avg_z > 0.3 else 'falling' if avg_z < -0.3 else 'neutral'

    # NOTE: volume_roc is NOT cached here — fetch it AFTER prefetch completes
    # via get_volume_roc() in compute_score, which reads the shared _VOL_CACHE

    return {
        'percentile': percentile,
        'percentile_long': pct_long,
        'percentile_short': pct_short,
        'velocity':   velocity,
        'phase':     phase,
        'avg_z':     round(avg_z, 3),
        'max_z':     round(max_z, 3),
        'min_z':     round(min_z, 3),
        'z_direction': z_direction,
    }


# ═══════════════════════════════════════════════════════════════
# Market Regime (from cross-token z-score consensus)
# ═══════════════════════════════════════════════════════════════

def compute_regime():
    """
    Compare short vs medium z-scores across top tokens.
    Returns: (regime_name, long_mult, short_mult, broad_trending_up, broad_z_avg)
    broad_trending_up: bool — BTC/ETH/SOL 4h avg z > BROAD_UPTEND_Z
    """
    short_z, med_z = [], []
    for tok in _get_top_tokens():
        zscores = get_tf_zscores(tok)
        if '1m'   in zscores: short_z.append(zscores['1m'][0])
        if '30m'  in zscores: med_z.append(zscores['30m'][0])

    if not short_z or not med_z:
        return 'neutral', 1.0, 1.0, False, 0.0

    avg_s = statistics.mean(short_z)
    avg_m = statistics.mean(med_z)

    # ── Broad market trend check ─────────────────────────────────────
    broad_z_vals = []
    for tok in BROAD_MARKET_TOKENS:
        zs = get_tf_zscores(tok)
        if '4h' in zs and zs['4h'][0] is not None:
            broad_z_vals.append(zs['4h'][0])
    broad_z_avg = statistics.mean(broad_z_vals) if broad_z_vals else 0.0
    broad_trending_up = broad_z_avg > BROAD_UPTEND_Z

    # Consensus oversold → bullish bias
    if avg_s < -1.5 and avg_m < -1.0:
        return 'bullish', 1.4, 0.9, broad_trending_up, broad_z_avg
    # Consensus overbought → bearish bias
    if avg_s > 1.5 and avg_m > 1.0:
        return 'bearish', 0.9, 1.4, broad_trending_up, broad_z_avg
    # Short mean-reverting UP from medium → bullish
    if avg_s < avg_m - 0.3:
        return 'bullish', 1.2, 1.0, broad_trending_up, broad_z_avg
    # Short mean-reverting DOWN from medium → bearish
    if avg_s > avg_m + 0.3:
        return 'bearish', 1.0, 1.2, broad_trending_up, broad_z_avg
    return 'neutral', 1.0, 1.0, broad_trending_up, broad_z_avg


def check_long_trend_filter(token):
    """
    Check if token passes the LONG trend filter.
    Returns (passes, reason).
    BLOCKS LONG if:
      1. Broad market (BTC/ETH/SOL) avg 4h z > BROAD_UPTEND_Z (uptrend)
      2. Fewer than LONG_AGREE_TFS of (1h, 4h, 30m) z-scores are suppressed
    """
    # ── Broad market trend ─────────────────────────────────────────
    broad_z_vals = []
    for tok in BROAD_MARKET_TOKENS:
        zs = get_tf_zscores(tok)
        if '4h' in zs and zs['4h'][0] is not None:
            broad_z_vals.append(zs['4h'][0])
    if broad_z_vals:
        broad_avg = statistics.mean(broad_z_vals)
        if broad_avg > BROAD_UPTEND_Z:
            return False, f'broad_market_z={broad_avg:+.2f}>+{BROAD_UPTEND_Z}'

    # ── Token-specific multi-TF check ──────────────────────────────
    zscores = get_tf_zscores(token)
    agreeing = 0
    if '1h'  in zscores and zscores['1h'][0]  is not None and zscores['1h'][0]  <= LONG_1H_Z_MAX:  agreeing += 1
    if '4h'  in zscores and zscores['4h'][0]  is not None and zscores['4h'][0]  <= LONG_4H_Z_MAX:  agreeing += 1
    if '30m' in zscores and zscores['30m'][0] is not None and zscores['30m'][0] <= LONG_30M_Z_MAX: agreeing += 1

    if agreeing < LONG_AGREE_TFS:
        z1h  = zscores.get('1h',  (None, None))[0]
        z4h  = zscores.get('4h',  (None, None))[0]
        z30m = zscores.get('30m', (None, None))[0]
        def fmt(z): return f'{z:+.2f}' if z is not None else 'N/A'
        return False, f'long_tfs={agreeing}/{LONG_AGREE_TFS} agree (1h={fmt(z1h)} 4h={fmt(z4h)} 30m={fmt(z30m)})'

    return True, 'passed'


# ─── Per-token rate limit ──────────────────────────────────────────────
TRADE_LOG_FILE = '/var/www/hermes/data/recent_trades.json'

def recent_trade_exists(token, minutes=MIN_TRADE_INTERVAL_MINUTES):
    """Return True if token was traded in last N minutes."""
    try:
        if not os.path.exists(TRADE_LOG_FILE):
            return False
        with open(TRADE_LOG_FILE) as f:
            data = json.load(f)
        cutoff = time.time() - minutes * 60
        entries = data.get(token.upper(), [])
        for entry in entries:
            if isinstance(entry, dict):
                ts = entry.get('timestamp', 0)
            else:
                ts = entry
            if ts > cutoff:
                return True
    except:
        pass
    return False


def log_trade(token):
    """Record a trade for rate limiting purposes."""
    try:
        try:
            with open(TRADE_LOG_FILE) as f:
                data = json.load(f)
        except:
            data = {}
        token = token.upper()
        if token not in data:
            data[token] = []
        data[token].append({'timestamp': time.time()})
        # Keep only last 100 entries per token
        data[token] = data[token][-100:]
        with open(TRADE_LOG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f'log_trade error: {e}')


# ═══════════════════════════════════════════════════════════════
# Token Scoring — Momentum Model
# ═══════════════════════════════════════════════════════════════

def compute_score(token, direction, long_mult, short_mult):
    """
    Momentum-based confidence scoring (0-100 scale).

    Logic:
    - Use DIRECTIONAL percentile (pct_long or pct_short)
      Long: pct_long=95 → price is at historical lows → good LONG
      Short: pct_short=95 → price is at historical highs → good SHORT
    - Velocity: rising z = good for LONG, falling z = good for SHORT
    - Phase: quiet=skip, building=partial, accelerating=full, exhaustion=reduce longs
    - RSI/MACD as confirmation only
    """
    price = get_latest_price(token)
    if not price or price <= 0:
        return None, None

    rows   = get_price_history(token, lookback_minutes=60480)
    prices = [r[1] for r in rows] if rows else []
    if len(prices) < 60:
        return None, None

    # ── Core momentum metrics ──────────────────────────────────
    mom = get_momentum_stats(token)
    if not mom:
        return None, None

    percentile_long  = mom['percentile_long']
    percentile_short = mom['percentile_short']
    percentile       = mom['percentile']   # overall for phase
    velocity         = mom['velocity']
    phase            = mom['phase']        # default (built from pct_long)
    avg_z            = mom['avg_z']

    # Recompute phase using direction-appropriate percentile
    # pct_long for LONG: low = suppressed = potential long zone
    # pct_short for SHORT: high = elevated = potential short zone (invert)
    if direction == 'LONG':
        dir_percentile = percentile_long
        # At extreme suppression: treat as extreme even if velocity neutral
        if percentile_long <= 10:
            phase = 'extreme'
        else:
            phase = detect_phase(dir_percentile, velocity)
    else:
        dir_percentile = 100 - percentile_short   # invert: pct_short=100 → 0
        # At extreme elevation: never quiet, treat as extreme
        if percentile_short >= 90:
            phase = 'extreme'
        else:
            phase = detect_phase(dir_percentile, velocity)

    # Directional percentile scoring
    # pct_long: % of z-scores BELOW current z
    #   HIGH pct_long = price elevated = bad for LONG
    #   LOW pct_long = price suppressed = good for LONG
    # pct_short: % of z-scores ABOVE current z
    #   HIGH pct_short = price elevated = good for SHORT
    #   LOW pct_short = price suppressed = bad for SHORT
    #
    # pct_long_score_fn: 0-60 pts (suppressed → strong long)
    # pct_short_score_fn: 0-60 pts (elevated → strong short)
    # pct_contrib is 0-60, velocity + phase give another 0-30
    # Target: suppressed pct_long=35 → ~50 pts + good phase/vel → hits 65+
    def pct_long_score_fn(pct):
        # pct_long = % below current → LOW = suppressed = good for LONG
        # pct 50→0pts, pct 35→30pts, pct 20→60pts (capped)
        if pct >= 50:
            return 0.0
        if pct <= 20:
            return min(60.0, (50 - pct) / 10 * 60)
        return (50 - pct) / 30 * 30

    def pct_short_score_fn(pct):
        # pct_short = % above current → HIGH = elevated = good for SHORT
        # Give positive score for elevated prices, 0 for suppressed
        # pct 40→0pts, pct 55→30pts, pct 70→60pts (capped)
        if pct <= 40:
            return 0.0
        if pct >= 70:
            return min(60.0, (pct - 40) / 10 * 60)
        return (pct - 40) / 30 * 30

    p_long  = pct_long_score_fn(percentile_long)
    p_short = pct_short_score_fn(percentile_short)
    pct_score = p_long if direction == 'LONG' else p_short

    # ── Volume ROC ─────────────────────────────────────────────
    # High volume confirms directional momentum; negative = weakening
    vol_roc_val, vol_score_adj, vol_reason = get_volume_roc(token)
    vol_score = vol_score_adj  # 0 to +10, or negative

    # Slightly loosen phase gate if volume strongly confirms direction
    # (vol_roc > 1.0 = 100%+ surge → gives one additional grace pass)
    vol_grace = vol_roc_val >= 1.0 and pct_score >= 10  # strong vol + some pct signal
    if phase == 'quiet':
        # Loosen: allow quiet phase signals for mean reversion setups
        # LONG: pct_long must be suppressed enough to score points
        # SHORT: pct_short must be elevated enough to score points
        has_pct_signal = (direction == 'LONG' and percentile_long <= 40) or \
                         (direction == 'SHORT' and percentile_short >= 60)
        if not (vol_grace or has_pct_signal):
            return None, None
        phase_mod = +1
        phase_reason = 'quiet-mean-reversion' if has_pct_signal else 'quiet-vol-surge'

    elif phase == 'extreme':
        if direction == 'LONG':
            return None, None   # never long in extreme zone
        phase_mod = +5
        phase_reason = 'extreme-short'

    elif phase == 'exhaustion':
        if direction == 'LONG':
            if percentile_long < 40:
                phase_mod = +3
                phase_reason = 'exhaustion-long-ok'
            else:
                return None, None  # BLOCK LONG in exhaustion unless deeply suppressed
        else:
            phase_mod = +5
            phase_reason = 'exhaustion-short'

    elif phase == 'accelerating':
        phase_mod = +5
        phase_reason = 'accelerating'

    elif phase == 'building':
        phase_mod = 0
        phase_reason = 'building'

    # ── Z-score contribution (0-60 pts) ─────────────────────────
    # Z-score directly indicates LONG vs SHORT opportunity
    # Negative z = below mean = good for LONG entry
    # Positive z = above mean = good for SHORT entry
    # Scale: z = ±1.5 → ±60 pts
    Z_SCALE = 20  # z=-1.5 → 30 pts for LONG (capped)
    if direction == 'LONG':
        z_score = min(30.0, max(0.0, -avg_z * Z_SCALE))  # neg z → positive score, cap at 30
    else:
        z_score = min(30.0, max(0.0, avg_z * Z_SCALE))   # pos z → positive score, cap at 30

    # ── Velocity contribution (0-20 pts) ────────────────────────
    # Velocity = change in z-score over time
    # Rising z = price reverting UP toward mean = GOOD for SHORT, BAD for LONG
    # Falling z = price reverting DOWN from mean = GOOD for LONG, BAD for SHORT
    VEL_SCALE = 100  # velocity = ±0.1 → ±10 pts (capped)
    if direction == 'LONG':
        # Negative velocity = z falling = price reverting down = good LONG entry
        vel_score = min(10.0, max(0.0, -velocity * VEL_SCALE))
    else:
        # Positive velocity = z rising = price reverting up = good SHORT entry
        vel_score = min(10.0, max(0.0, velocity * VEL_SCALE))

    # ── RSI mandatory gate (0-3 pts) ─────────────────────────────
    # LONG: RSI must be < 60 (not overbought) → returns None if RSI ≥ 60
    # SHORT: RSI must be > 40 (not oversold) → returns None if RSI ≤ 40
    rsi_val = rsi(prices) if len(prices) >= 30 else None
    rsi_score = 0.0
    rsi_reason = ''
    if rsi_val is not None:
        if direction == 'LONG':
            if rsi_val >= 60:
                return None, None   # BLOCK LONG — overbought
            if rsi_val < 50:
                rsi_score = W_RSI * (50 - rsi_val) / 30
                rsi_reason = f'RSI={rsi_val:.0f}(oversold)' if rsi_val < 40 else f'RSI={rsi_val:.0f}(ok)'
        elif direction == 'SHORT':
            if rsi_val <= 40:
                return None, None   # BLOCK SHORT — oversold
            if rsi_val > 50:
                rsi_score = W_RSI * (rsi_val - 50) / 30
                rsi_reason = f'RSI={rsi_val:.0f}(overbought)' if rsi_val > 60 else f'RSI={rsi_val:.0f}(ok)'

    # ── MACD confirmation (0-1 pts) ───────────────────────────
    _, hist = macd(prices) if len(prices) >= 40 else (None, None)
    macd_score = 0.0
    macd_reason = ''
    if hist is not None:
        hist_bps = abs(hist) / price * 10000
        if direction == 'LONG' and hist > 0:
            macd_score = W_MACD * min(hist_bps / 100, 1.0)
            macd_reason = f'MACD=+{hist:.6f}'
        elif direction == 'SHORT' and hist < 0:
            macd_score = W_MACD * min(hist_bps / 100, 1.0)
            macd_reason = f'MACD={hist:.6f}'

    # ── Regime multiplier (0-5 pts) ────────────────────────────
    regime_mult = long_mult if direction == 'LONG' else short_mult
    regime_mod = +5 if regime_mult > 1.0 else 0

    # ── 4h Trend Filter for SHORTs ────────────────────────────────
    # In a sustained uptrend, shorting a rising price = countertrend suicide.
    # Block SHORTs that have already run >20% in 4h. Reduce by 15pts if >10%.
    TREND_LOOKBACK = 240   # 240 × 1min = 4 hours
    trend_penalty = 0
    trend_reason = ''
    if direction == 'SHORT' and len(rows) >= TREND_LOOKBACK:
        price_4h_ago = float(rows[-TREND_LOOKBACK][1])
        if price_4h_ago and price_4h_ago > 0:
            chg_4h = (float(price) - price_4h_ago) / price_4h_ago * 100
            if chg_4h > 20:
                return None, None   # SHORT blocked — strong uptrend in progress
            elif chg_4h > 10:
                trend_penalty = 15
                trend_reason = f'+{chg_4h:.1f}% in 4h(short reduced)'
            elif chg_4h > 5:
                trend_penalty = 5
                trend_reason = f'+{chg_4h:.1f}% in 4h'

    # ── Score assembly ─────────────────────────────────────────
    # z_score: 0-30 | velocity: 0-10 | volume: 0-10 (or negative) | phase: 0-5 | regime: 0-5 | rsi: 0-3 | macd: 0-1 | trend_penalty: 0-15
    score = z_score + vel_score + vol_score + phase_mod + regime_mod + rsi_score + macd_score - trend_penalty
    score = min(99.0, max(0, round(score, 1)))

    if score < ENTRY_THRESHOLD:
        # Mean reversion bonus: extreme phase + good z + decent percentile
        z_bonus = 0
        if phase == 'extreme' and abs(avg_z) >= 1.0 and pct_score >= 50:
            z_bonus = 25
        elif phase == 'extreme' and abs(avg_z) >= 0.7:
            z_bonus = 15
        elif abs(avg_z) >= 1.5 and vol_score >= 3:
            z_bonus = 15
        elif abs(avg_z) >= 1.0 and vol_score >= 3:
            z_bonus = 8
        score = min(99.0, score + z_bonus)
        if score >= ENTRY_THRESHOLD:
            phase_reason += '-zbonus'
        if score < ENTRY_THRESHOLD:
            return None, None

    # ── Build signal reasons ───────────────────────────────────
    pct_dir = percentile_long if direction == 'LONG' else percentile_short
    reasons = [
        f'pct={pct_dir:.0f}%({phase_reason})',
        f'z={avg_z:+.2f}({mom["z_direction"]})',
        f'vel={velocity:+.3f}',
    ]
    if vol_reason:
        reasons.append(vol_reason)
    if rsi_reason:
        reasons.append(rsi_reason)
    if macd_reason:
        reasons.append(macd_reason)
    if trend_reason:
        reasons.append(trend_reason)

    signals = [('momentum', '1h', score, reasons[0])]
    if vol_reason:
        signals.append(('volume', '1m', vol_score, vol_reason))
    if rsi_reason:
        signals.append(('rsi', '1h', rsi_score, rsi_reason))
    if macd_reason:
        signals.append(('macd', '1h', macd_score, macd_reason))

    return score, signals


# ═══════════════════════════════════════════════════════════════
# Open Positions
# ═══════════════════════════════════════════════════════════════




# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def run():
    init_db()
    _ZSCORE_CACHE.clear()
    _VOL_CACHE.clear()
    prices_dict = get_all_latest_prices()
    regime, long_mult, short_mult, broad_trending_up, broad_z_avg = compute_regime()
    print(f'=== Signal Gen | Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | Broad BTC/ETH/SOL 4h z={broad_z_avg:+.2f} | {len(prices_dict)} tokens')
    log(f'REGIME: {regime.upper()} L:x{long_mult:.1f} S:x{short_mult:.1f} broad_z={broad_z_avg:+.2f} | {len(prices_dict)} tokens')

    from position_manager import get_open_positions as _get_open_pos
    open_pos = _get_open_pos()
    added    = 0
    blocked  = 0
    exits    = []
    active_tokens = set(prices_dict.keys())
    print(f'  Active universe: {len(active_tokens)} tokens (full universe)')

    # Volume data: skip background prefetch entirely.
    # signal_gen completes in <2s without it. Volume ROC is a minor bonus (0-10pts)
    # that builds up naturally across consecutive runs. If you want active volume
    # prefetching, move it to a separate cron job at a different schedule.
    # _VOL_CACHE persists across runs so consecutive pipelines still get volume data.
    # scan loop starts immediately — volume data fills in as HL allows

    for token, data in prices_dict.items():
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if get_cooldown(token):
            continue
        if token.upper() not in active_tokens:
            continue
        if is_delisted(token.upper()):
            continue

        # ── Per-token rate limiting ─────────────────────────
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue

        price = data['price']
        mom = get_momentum_stats(token)

        # ── LONG signals ──────────────────────────────────────
        if token not in open_pos or open_pos[token] != 'LONG':
            # Trend filter check
            long_ok, long_filter_reason = check_long_trend_filter(token)
            score, signals = compute_score(token, 'LONG', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                if not long_ok:
                    log(f'BLOCKED LONG: {token} @{price:.6f} {score:.1f}% [{long_filter_reason}]')
                    print(f'  LONG-B {token:8s} {score:5.1f}% [BLOCKED] {long_filter_reason}')
                    blocked += 1
                else:
                    # Pre-compute RSI/MACD for add_signal
                    prices_all = get_price_history(token, lookback_minutes=60480)
                    prices_list = [r[1] for r in prices_all] if prices_all else []
                    rsi_14_val = rsi(prices_list) if len(prices_list) >= 30 else None
                    macd_line_val, macd_hist_val = macd(prices_list) if len(prices_list) >= 40 else (None, None)
                    macd_sig_val = macd(prices_list)[0] if len(prices_list) >= 40 else None
                    if macd_sig_val and macd_hist_val:
                        macd_signal_val = macd_sig_val - macd_hist_val
                    else:
                        macd_signal_val = None
                    sources = '+'.join(sorted(set(s[0] for s in signals)))
                    reasons = ' | '.join(s[3] for s in signals[:4])
                    add_signal(
                        token=token, direction='LONG', signal_type='momentum',
                        source=f'mtf-{sources}', confidence=score,
                        value=score, price=price,
                        exchange='hyperliquid',
                        timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                        z_score=mom['avg_z'] if mom else None,
                        z_score_tier=mom['z_direction'] if mom else None,
                        rsi_14=rsi_14_val,
                        macd_value=macd_line_val,
                        macd_signal=macd_signal_val,
                        macd_hist=macd_hist_val,
                    )
                    if score >= AUTO_APPROVE:
                        approve_signal(token, 'LONG')
                        log_trade(token)
                        log(f'APPROVED: {token} LONG @{price:.6f} {score:.1f}% {reasons}')
                        print(f'  LONG  {token:8s} {score:5.1f}% [AUTO]  {reasons}')
                    else:
                        log(f'SIGNAL:  {token} LONG @{price:.6f} {score:.1f}% {reasons}')
                        print(f'  LONG  {token:8s} {score:5.1f}% [WAIT]  {reasons}')
                    set_cooldown(token, 'LONG', hours=1)
                    added += 1

        # ── SHORT signals ─────────────────────────────────────
        if token not in open_pos or open_pos[token] != 'SHORT':
            score, signals = compute_score(token, 'SHORT', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                sources = '+'.join(sorted(set(s[0] for s in signals)))
                reasons = ' | '.join(s[3] for s in signals[:4])
                add_signal(
                    token=token, direction='SHORT', signal_type='momentum',
                    source=f'mtf-{sources}', confidence=score,
                    value=score, price=price,
                    exchange='hyperliquid',
                    timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                    z_score=mom['avg_z'] if mom else None,
                    z_score_tier=mom['z_direction'] if mom else None,
                )
                if score >= AUTO_APPROVE:
                    approve_signal(token, 'SHORT')
                    log_trade(token)
                    log(f'APPROVED: {token} SHORT @{price:.6f} {score:.1f}% {reasons}')
                    print(f'  SHORT {token:8s} {score:5.1f}% [AUTO]  {reasons}')
                else:
                    log(f'SIGNAL:  {token} SHORT @{price:.6f} {score:.1f}% {reasons}')
                    print(f'  SHORT {token:8s} {score:5.1f}% [WAIT]  {reasons}')
                set_cooldown(token, 'SHORT', hours=1)
                added += 1

        # ── Exit signals (check open positions) ───────────────
        if token in open_pos:
            open_dir = open_pos[token]
            opp_dir  = 'SHORT' if open_dir == 'LONG' else 'LONG'
            opp_mult = short_mult if opp_dir == 'SHORT' else long_mult
            opp_score, _ = compute_score(token, opp_dir, long_mult, short_mult)
            if opp_score and opp_score >= EXIT_THRESHOLD:
                exits.append({
                    'token': token, 'open_dir': open_dir,
                    'opp_score': opp_score, 'opp_dir': opp_dir
                })
                log(f'EXIT ALERT: {token} {open_dir} → {opp_dir} {opp_score:.1f}%')

    print(f'=== Done: {added} signals | {blocked} blocked | {len(exits)} exit alerts ===')
    return added, exits


if __name__ == '__main__':
    # Prevent stdin deadlock when run as subprocess (hermes-pipeline calls signal_gen
    # via subprocess.run with capture_output=True). Redirect stdin to /dev/null so
    # any stdin-reading code in imported libs doesn't block waiting for input.
    import sys
    if sys.stdin is not None and hasattr(sys.stdin, 'fileno'):
        try:
            sys.stdin = open('/dev/null', 'r')
        except Exception:
            pass
    run()
