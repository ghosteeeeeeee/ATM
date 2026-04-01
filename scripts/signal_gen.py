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
from typing import Tuple, List, Optional
import sys, sqlite3, time, os, json, statistics, math
from functools import lru_cache
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_RUNTIME_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           os.pardir, 'data', 'signals_hermes_runtime.db')
from hermes_constants import SHORT_BLACKLIST, LONG_BLACKLIST


def _has_confluence_partners(token: str, direction: str, exclude_type: str = None) -> bool:
    """
    Check if there's at least one OTHER signal type for this token+direction
    in the last 60 minutes. Used to gate sub-threshold individual signals —
    we only want to emit RSI/MACD sub-signals when they're genuinely contributing
    to a potential confluence, not generating noise in a vacuum.
    """
    conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
    c = conn.cursor()
    try:
        if exclude_type:
            c.execute("""
                SELECT COUNT(DISTINCT signal_type) FROM signals
                WHERE token=? AND direction=? AND decision='PENDING'
                AND created_at > datetime('now', '-60 minutes')
                AND signal_type != ?
            """, (token.upper(), direction.upper(), exclude_type))
        else:
            c.execute("""
                SELECT COUNT(DISTINCT signal_type) FROM signals
                WHERE token=? AND direction=? AND decision='PENDING'
                AND created_at > datetime('now', '-60 minutes')
            """, (token.upper(), direction.upper()))
        return c.fetchone()[0] > 0
    finally:
        conn.close()


def _process_signal(sig_id: int, decision: str, reason: str = None) -> None:
    """
    Process a signal decision (called by external ai-decider pipeline).
    Increments review_count on SKIPPED/WAIT so the hot set can track survivors.
    """
    if decision in ('SKIPPED', 'WAIT'):
        from signal_schema import update_signal_review_count
        update_signal_review_count(sig_id)


def _load_hot_rounds() -> List[dict]:
    """
    Load tokens that have survived multiple ai-decider review passes.
    Uses review_count on signals table (incremented each time signal is reviewed
    without being executed or hard-skipped).
    """
    conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
    c = conn.cursor()
    try:
        rows = c.execute("""
            SELECT token, direction, MAX(review_count) as rounds
            FROM signals
            WHERE decision IN ('PENDING', 'APPROVED')
              AND review_count >= 2
              AND created_at > datetime('now', '-3 hours')
            GROUP BY token, direction
            HAVING COUNT(*) >= 1
        """).fetchall()
        return [{'token': r[0], 'direction': r[1], 'rounds': r[2]} for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def _persist_momentum_state(token, momentum_state, state_confidence,
                             pct_long, pct_short, avg_z, phase, z_direction):
    """Save momentum state to DB for tracking state transitions over time."""
    try:
        conn = sqlite3.connect(_RUNTIME_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO momentum_cache
              (token, phase, percentile_long, percentile_short, velocity, avg_z,
               z_direction, momentum_state, state_confidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(token) DO UPDATE SET
              momentum_state    = excluded.momentum_state,
              state_confidence  = excluded.state_confidence,
              percentile_long   = excluded.percentile_long,
              percentile_short  = excluded.percentile_short,
              avg_z            = excluded.avg_z,
              phase            = excluded.phase,
              z_direction      = excluded.z_direction,
              updated_at       = excluded.updated_at
        """, (token, phase, pct_long, pct_short, 0.0, avg_z,
              z_direction, momentum_state, state_confidence, int(time.time())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[signal_gen] _persist_momentum_state DB error: {e}")  # logged, not silently swallowed

from signal_schema import (
    init_db, get_all_latest_prices, get_price_history,
    expire_pending_signals,
    get_latest_price, add_signal, set_cooldown, get_cooldown,
    price_age_minutes, approve_signal, update_signal_decision,
    mark_signal_processed, add_confluence_signal, get_confluence_signals
)
from hyperliquid_exchange import is_delisted
from position_manager import get_open_positions as _get_open_pos, get_opposite_direction_cooldown_hours

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
ENTRY_THRESHOLD      = 65    # min score to add signal
AI_DECIDER_THRESHOLD  = 65    # ≥ this + < AUTO_APPROVE → pending → AI decider
AUTO_APPROVE          = 95    # ≥ this → auto-approve (momentum uses PENDING only; this is a safety cap)

# Confluence detection: require ≥2 agreeing signals before firing
CONFLUENCE_MIN_SIGNALS = 2   # minimum agreeing signals to trigger confluence
CONFLUENCE_BOOST_2     = 1.25 # 1.25x confidence boost for 2 signals
CONFLUENCE_BOOST_3PLUS = 1.50 # 1.5x confidence boost for 3+ signals
CONFLUENCE_AUTO_APPROVE = 75  # confluence signal ≥ this → auto-approve (no AI needed)

# Individual signal thresholds for confluence-ready signal table population
# These are LOWER than ENTRY_THRESHOLD so confluence can combine weak-but-aligned signals
CONFLUENCE_RSI_LOW   = 35   # RSI < this → LONG (oversold = potential reversal LONG)
CONFLUENCE_RSI_HIGH  = 65   # RSI > this → SHORT (overbought = bearish confirmation SHORT)
CONFLUENCE_MACD_HIST_THRESH = 0.000005  # MACD histogram magnitude to add individual signal

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

# ─── Trend Filter Thresholds ────────────────────────────────────────
# LONG: require longer TFs to be below these z-scores
LONG_1H_Z_MAX   = +0.5    # 1H z-score must be below this (negative = suppressed)
LONG_4H_Z_MAX   = +0.3    # 4H z-score must be below this
LONG_30M_Z_MAX  = +0.5    # 30m z-score must be below this
LONG_AGREE_TFS  = 2       # Require at least 2 of (1h, 4h, 30m) to agree

# SHORT: require longer TFs to be above these z-scores (elevated = ready to short)
SHORT_4H_Z_MAX  = +2.5    # BLOCK SHORT if 4h z > +2.5 (catching a falling knife)
SHORT_1H_Z_MAX  = +2.5
SHORT_30M_Z_MAX = +2.5
SHORT_AGREE_TFS = 2       # Require at least 2 of (1h, 4h, 30m) to be elevated

# Broad market: if BTC+ETH+SOL avg 4h z > 0 → block SHORTs (ride the wave, not against it)
BROAD_UPTEND_Z   = +0.0

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


_HEARTBEAT_FILE = '/var/www/hermes/data/pipeline_heartbeat.json'


def _update_heartbeat(stage: str):
    """Update the pipeline heartbeat file for a given stage."""
    try:
        data = {}
        if os.path.exists(_HEARTBEAT_FILE):
            try:
                with open(_HEARTBEAT_FILE) as f:
                    data = json.load(f)
            except Exception:
                pass
        data[stage] = {"timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), "status": "ok"}
        with open(_HEARTBEAT_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass  # Never crash on heartbeat failures


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
        # No pullbacks at all = can't compute meaningful RSI
        # Return a high-but-not-extreme value so confluence can still fire
        # but won't get auto-approved by RSI alone
        return 85.0
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
    Compute directional percentile ranks for the current price.
    Returns: (pct_rank, pct_long, pct_short)
      pct_rank   = z-score percentile (how unusual is current price vs rolling mean?)
      pct_long   = % of historical prices BELOW current price
                   HIGH pct_long = suppressed = good LONG entry
      pct_short  = % of historical prices ABOVE current price
                   HIGH pct_short = elevated = good SHORT entry
    """
    if len(prices) < 60:
        return 50.0, 50.0, 50.0

    lookback = prices[-window:] if len(prices) >= window else prices
    current_price = prices[-1]

    # True price percentile: compare each historical price to current price
    price_below  = sum(1 for p in lookback if p <= current_price)
    price_above  = sum(1 for p in lookback if p >= current_price)
    pct_long  = round((price_below  / len(lookback)) * 100, 1)
    pct_short = round((price_above  / len(lookback)) * 100, 1)

    # Z-score percentile: how unusual is the current price vs its rolling windows?
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

    if z_values:
        current_z = z_values[-1]
        below_z = sum(1 for z in z_values if z <= current_z)
        pct_rank = round((below_z / len(z_values)) * 100, 1)
    else:
        pct_rank = 50.0

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

    # ── Momentum state ─────────────────────────────────────────
    # Fine-grained: bullish / bearish / neutral
    #   bullish: z elevated (mean-reverting UP) OR suppressed price catching bid
    #   bearish: z elevated (elevated price ripe for SHORT) OR expanding down
    #   neutral: ranging, weak signals
    # Use pct_short (how elevated the price is) as primary signal
    #   pct_short HIGH → price elevated → bearish
    #   pct_short LOW  → price suppressed → bullish
    # Use avg_z direction for confirmation
    if pct_short >= 70 and avg_z > 0.2:
        momentum_state = 'bearish'
        state_confidence = min(1.0, (pct_short - 70) / 30 + max(0, avg_z - 0.2))
    elif pct_short >= 60 and avg_z > 0.3:
        momentum_state = 'bearish'
        state_confidence = min(1.0, (pct_short - 60) / 40 + max(0, avg_z - 0.3) * 0.5)
    elif pct_short <= 30 and avg_z < -0.2:
        momentum_state = 'bullish'
        state_confidence = min(1.0, (30 - pct_short) / 30 + max(0, abs(avg_z) - 0.2))
    elif pct_short <= 40 and avg_z < -0.3:
        momentum_state = 'bullish'
        state_confidence = min(1.0, (40 - pct_short) / 40 + max(0, abs(avg_z) - 0.3) * 0.5)
    elif z_direction == 'rising' and phase in ('accelerating', 'exhaustion'):
        momentum_state = 'bullish'
        state_confidence = 0.5
    elif z_direction == 'falling' and phase in ('accelerating',):
        momentum_state = 'bearish'
        state_confidence = 0.5
    else:
        momentum_state = 'neutral'
        state_confidence = 0.3

    # ── RSI and MACD (computed once, reused by compute_score and run loop) ──
    rsi_14_val = rsi(prices) if len(prices) >= 30 else None
    macd_line_val, macd_hist_val = macd(prices) if len(prices) >= 40 else (None, None)
    macd_sig_val = macd(prices)[0] if len(prices) >= 40 else None
    macd_signal_val = (macd_sig_val - macd_hist_val) if (macd_sig_val is not None and macd_hist_val is not None) else None

    result = {
        'percentile': percentile,
        'percentile_long': pct_long,
        'percentile_short': pct_short,
        'velocity':   velocity,
        'phase':     phase,
        'avg_z':     round(avg_z, 3),
        'max_z':     round(max_z, 3),
        'min_z':     round(min_z, 3),
        'z_direction': z_direction,
        'momentum_state': momentum_state,
        'state_confidence': round(state_confidence, 3),
        # RSI and MACD cached here to avoid recomputation
        'rsi_14': rsi_14_val,
        'macd_line': macd_line_val,
        'macd_hist': macd_hist_val,
        'macd_signal': macd_signal_val,
    }

    # Persist to DB
    _persist_momentum_state(token, momentum_state, state_confidence, pct_long, pct_short, avg_z, phase, z_direction)

    return result


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
        return 'bullish', 1.1, 0.95, broad_trending_up, broad_z_avg
    # Consensus overbought → bearish bias
    # NOTE: SHORT multiplier capped at 1.1. Historical data (2026-04-01) shows
    # LONG avg=+$3.38 vs SHORT avg=-$0.79 — letting signals compete on confidence
    # alone beats regime-driven directional bias.
    if avg_s > 1.5 and avg_m > 1.0:
        return 'bearish', 0.95, 1.1, broad_trending_up, broad_z_avg
    # Short mean-reverting UP from medium → bullish
    if avg_s < avg_m - 0.3:
        return 'bullish', 1.05, 1.0, broad_trending_up, broad_z_avg
    # Short mean-reverting DOWN from medium → bearish
    if avg_s > avg_m + 0.3:
        return 'bearish', 1.0, 1.05, broad_trending_up, broad_z_avg
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


def check_short_trend_filter(token):
    """
    Check if token passes the SHORT trend filter.
    Returns (passes, reason).
    BLOCKS SHORT if:
      1. Broad market (BTC/ETH/SOL) avg 4h z > 0 (don't short a rising market)
      2. Fewer than SHORT_AGREE_TFS of (1h, 4h, 30m) z-scores are elevated
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
            return False, f'broad_market_z={broad_avg:+.2f}>+{BROAD_UPTEND_Z} (rising market, no shorts)'

    # ── Token-specific multi-TF check ──────────────────────────────
    zscores = get_tf_zscores(token)
    elevated = 0
    if '1h'  in zscores and zscores['1h'][0]  is not None and zscores['1h'][0]  >= SHORT_1H_Z_MAX:  elevated += 1
    if '4h'  in zscores and zscores['4h'][0]  is not None and zscores['4h'][0]  >= SHORT_4H_Z_MAX:  elevated += 1
    if '30m' in zscores and zscores['30m'][0] is not None and zscores['30m'][0] >= SHORT_30M_Z_MAX: elevated += 1

    if elevated < SHORT_AGREE_TFS:
        z1h  = zscores.get('1h',  (None, None))[0]
        z4h  = zscores.get('4h',  (None, None))[0]
        z30m = zscores.get('30m', (None, None))[0]
        def fmt(z): return f'{z:+.2f}' if z is not None else 'N/A'
        return False, f'short_tfs={elevated}/{SHORT_AGREE_TFS} elevated (1h={fmt(z1h)} 4h={fmt(z4h)} 30m={fmt(z30m)})'

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
    if len(prices) < 30:
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
        # pct_short = % BELOW current price (same direction as pct_long)
        dir_percentile = percentile_short
        # At extreme suppression: never long, treat as extreme
        if percentile_short >= 80:
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
    # Target: suppressed pct_long=35 → ~50 pts + good phase/vel → hits 65+ (ENTRY_THRESHOLD)
    def pct_long_score_fn(pct):
        # pct_long = % BELOW current price
        # In BULL markets, price trending UP means pct_long stays elevated
        #   → pct_long=65 in a bull market = still valid long (suppressed vs recent pumps)
        #   → pct_long=40 = better long (more discounted)
        # In neutral/bear markets: pct_long elevated = bad (don't long near highs)
        #
        # SCORING (bull regime): pct_long=65 → 0pts, pct_long=50 → 30pts, pct_long=30 → 50pts
        # SCORING (bear/neutral): pct_long=50 → 0pts, pct_long=30 → 50pts, pct_long=20 → 60pts
        if pct >= 50:
            # Elevated — still give some score in bull regime (trend continuation)
            bull_mult = 1.5 if (phase == 'accelerating' and avg_z < 0) else 1.0
            return max(0.0, (50 - pct) / 20 * 15) * bull_mult  # 50→0pts, 65→0pts
        if pct <= 20:
            return min(60.0, (50 - pct) / 10 * 60)  # deeply suppressed = strong long
        return (50 - pct) / 30 * 50  # 50→0, 30→33, 20→50

    def pct_short_score_fn(pct):
        # pct_short = % BELOW current price
        # HIGH pct_short = suppressed price = bad for SHORT (price near highs = good SHORT)
        # pct_short=50 → 50% below → at median → neutral → 0 pts
        # pct_short=70 → 70% below → elevated → moderate SHORT signal → 27 pts
        # pct_short=85 → 85% below → very elevated → strong SHORT signal → 60 pts
        # pct_short=90 → 90% below → extreme elevation → capped at 60 pts
        if pct <= 50:
            return 0.0
        if pct <= 85:
            return (pct - 50) / 35 * 45   # 50→0pts, 70→26pts, 85→45pts
        return min(60.0, 45.0 + (pct - 85) / 15 * 15)  # 85→45pts, 100→60pts (hard cap)

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
        # Quiet = ranging/sideways = ideal mean reversion setup for BOTH directions
        # LONG:  pct_long must be <= 40 (suppressed enough to mean-revert up)
        # SHORT: pct_short must be >= 60 (elevated enough to mean-revert down)
        has_pct_signal = (direction == 'LONG' and percentile_long <= 40) or \
                         (direction == 'SHORT' and percentile_short >= 60)
        if not (vol_grace or has_pct_signal):
            return None, None
        # Give strong phase_mod for quiet mean reversion (vs +1 before)
        # Enough to let suppressed/elevated setups with good z hit 65+
        phase_mod = +5
        phase_reason = 'quiet-mean-reversion' if has_pct_signal else 'quiet-vol-surge'

    elif phase == 'extreme':
        if direction == 'LONG':
            return None, None   # never long in extreme zone
        # SHORT in extreme zone: cap boost at +3 (vs +5 for other phases)
        # Extreme = extreme elevation = very risky reversal candidate
        # We still allow it but don't reward disproportionately
        phase_mod = +3
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

    # ── RSI advisory (tiered penalty, not hard block) ─────────────
    # RSI informs confidence but doesn't hard-block. Extreme RSI penalizes heavily.
    # SHORT: RSI > 60 (overbought) = confirmed short, positive score
    # SHORT: RSI < 40 (oversold) = squeeze risk, heavy negative penalty
    # LONG:  RSI < 40 (oversold) = confirmed long, positive score
    # LONG:  RSI > 60 (overbought) = squeeze risk, heavy negative penalty
    # NOTE: RSI is cached in get_momentum_stats() — reuse it here
    rsi_val = mom.get('rsi_14')
    rsi_score = 0.0
    rsi_reason = ''
    if rsi_val is not None:
        if direction == 'SHORT':
            if rsi_val >= 70:   # overbought — confirmed SHORT
                rsi_score = +3.0
                rsi_reason = f'RSI={rsi_val:.0f}(overbought-confirm)'
            elif rsi_val >= 60:  # mildly overbought
                rsi_score = +1.0
                rsi_reason = f'RSI={rsi_val:.0f}(overbought)'
            elif rsi_val >= 40:  # neutral zone
                rsi_score = 0.0
                rsi_reason = f'RSI={rsi_val:.0f}(neutral)'
            elif rsi_val >= 30:  # oversold — squeeze risk for SHORT
                rsi_score = -5.0
                rsi_reason = f'RSI={rsi_val:.0f}(oversold-caution)'
            else:                # severely oversold — squeeze risk
                rsi_score = -20.0
                rsi_reason = f'RSI={rsi_val:.0f}(oversold-squeeze-risk)'
        elif direction == 'LONG':
            if rsi_val <= 30:    # oversold — confirmed LONG
                rsi_score = +3.0
                rsi_reason = f'RSI={rsi_val:.0f}(oversold-confirm)'
            elif rsi_val <= 40:  # mildly oversold
                rsi_score = +1.0
                rsi_reason = f'RSI={rsi_val:.0f}(oversold)'
            elif rsi_val <= 60:  # neutral zone
                rsi_score = 0.0
                rsi_reason = f'RSI={rsi_val:.0f}(neutral)'
            elif rsi_val <= 70:  # overbought — squeeze risk for LONG
                rsi_score = -5.0
                rsi_reason = f'RSI={rsi_val:.0f}(overbought-caution)'
            else:                 # severely overbought — squeeze risk
                rsi_score = -20.0
                rsi_reason = f'RSI={rsi_val:.0f}(overbought-squeeze-risk)'

    # ── MACD confirmation (0-1 pts) ───────────────────────────
    # NOTE: MACD is cached in get_momentum_stats() — reuse it here
    hist = mom.get('macd_hist')
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

    # ── 4h Trend Filter ─────────────────────────────────────────────
    # Block or penalize entries that are fighting a strong established trend.
    # SHORTs: block if +20% in 4h, -15 if +10%, -5 if +5%
    # LONGs:  block if -20% in 4h, -15 if -10%, -5 if -5%
    TREND_LOOKBACK = 240   # 240 × 1min = 4 hours
    trend_penalty = 0
    trend_reason = ''
    if len(rows) >= TREND_LOOKBACK:
        price_4h_ago = float(rows[-TREND_LOOKBACK][1])
        if price_4h_ago and price_4h_ago > 0:
            chg_4h = (float(price) - price_4h_ago) / price_4h_ago * 100
            if direction == 'SHORT':
                if chg_4h > 20:
                    return None, None
                elif chg_4h > 10:
                    trend_penalty = 15
                    trend_reason = f'+{chg_4h:.1f}% in 4h(short reduced)'
                elif chg_4h > 5:
                    trend_penalty = 5
                    trend_reason = f'+{chg_4h:.1f}% in 4h'
            else:  # LONG
                if chg_4h < -20:
                    return None, None
                elif chg_4h < -10:
                    trend_penalty = 15
                    trend_reason = f'{chg_4h:.1f}% in 4h(long reduced)'
                elif chg_4h < -5:
                    trend_penalty = 5
                    trend_reason = f'{chg_4h:.1f}% in 4h'

    # ── Cooldown expiry bonus ─────────────────────────────────────
    # If the opposing direction's cooldown is about to clear (within 30 min),
    # boost this direction's score. The opposing cooldown means that direction
    # was wrong — when it clears, the other side becomes the correct play.
    # Bonus: +15 if clearing within 15 min, +8 if within 30 min, else 0
    opp_cd_hours = get_opposite_direction_cooldown_hours(token, direction)
    cooldown_bonus = 15 if opp_cd_hours <= 0.25 else (8 if opp_cd_hours <= 0.5 else 0)
    cooldown_reason = f' opp_cd_clr+{cooldown_bonus}' if cooldown_bonus > 0 else ''

    # ── Score assembly ─────────────────────────────────────────
    # z_score: 0-30 | velocity: 0-10 | volume: 0-10 | phase: 0-5 | regime: 0-5 | rsi: 0-3 | macd: 0-1 | cooldown: 0-15 | trend_penalty: 0-15
    natural_score = z_score + vel_score + vol_score + phase_mod + regime_mod + rsi_score + macd_score
    score = natural_score + cooldown_bonus - trend_penalty
    score = min(99.0, max(0, round(score, 1)))

    # Mean reversion rescue: push borderline signals over threshold
    # REQUIREMENT: natural score (excl. cooldown bonus) must reach ENTRY_THRESHOLD before rescue applies.
    # Rescue only rescues borderline cases, not weak signals inflated by cooldown bonuses.
    # CAP: bonus max +3 pts (was +15 pts — too generous).
    if score < ENTRY_THRESHOLD and natural_score >= ENTRY_THRESHOLD:
        z_bonus = 0
        if phase == 'extreme' and abs(avg_z) >= 1.0 and pct_score >= 40:
            z_bonus = 3
        elif phase == 'extreme' and abs(avg_z) >= 0.7 and pct_score >= 40:
            z_bonus = 2
        elif abs(avg_z) >= 0.5 and pct_score >= 40:
            z_bonus = 1
        score = min(75.0, score + z_bonus)
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
    if cooldown_reason:
        reasons.append(cooldown_reason.lstrip())

    signals = [('momentum', '1h', score, reasons[0])]
    if vol_reason:
        signals.append(('volume', '1m', vol_score, vol_reason))
    if rsi_reason:
        signals.append(('rsi', '1h', rsi_score, rsi_reason))
    if macd_reason:
        signals.append(('macd', '1h', macd_score, macd_reason))

    return score, signals


# ═══════════════════════════════════════════════════════════════
# Spike Detection + Pump Mode
# ═══════════════════════════════════════════════════════════════
# A spike is a rapid intraday move (>3% in 15min) that means
# the signal is catching a top/bottom rather than riding a trend.
#
# BEHAVIOR:
# - SHORT fires on a coin that spiked +3-5% up → counter-spike LONG instead
# - SHORT fires on a coin that spiked +5%+     → PUMP mode LONG, tight SL/TP
# - LONG fires on a coin that spiked -3-5% down → counter-spike SHORT instead
# - LONG fires on a coin that spiked -5%+      → PUMP mode SHORT, tight SL/TP
#
# Pump mode: 1.5% SL, 2.5% TP, no trailing. Enter fast, exit fast.

PUMP_SL_PCT       = 0.015   # 1.5% stop loss
PUMP_TP_PCT       = 0.025   # 2.5% take profit
PUMP_MODE_THRESH  = 5.0    # >5% in 15min = pump mode
COUNTERSPIKE_THRESH = 3.0  # >3% in 15min = counter-spike (reverse)


def detect_spike(token: str, direction: str, current_price: float):
    """
    Check if a coin is mid-spike against our intended direction.

    Returns (spike_type, pct_change, reverse_signal, is_pump)

    spike_type:
      'up'   — price spiked up in last 15min
      'down' — price spiked down in last 15min
      None   — no significant spike
    pct_change: float (% change in 15min, positive=up)
    reverse_signal: True if counter-spike detected (should flip direction)
    is_pump: True if extreme spike (>5%) — enter tight, exit fast
    """
    rows = get_price_history(token, lookback_minutes=15)
    if not rows or len(rows) < 3:
        return None, 0.0, False, False

    recent_price = float(rows[-1][1])
    old_price = float(rows[0][1])

    if old_price <= 0:
        return None, 0.0, False, False

    pct_change = (recent_price - old_price) / old_price * 100

    if direction == 'SHORT':
        # Counter-spike SHORT: price spiked up (we'd be catching a top)
        if pct_change >= PUMP_MODE_THRESH:
            return 'up', pct_change, True, True    # pump mode LONG
        elif pct_change >= COUNTERSPIKE_THRESH:
            return 'up', pct_change, True, False   # counter-spike → reverse to LONG
    elif direction == 'LONG':
        # Counter-spike LONG: price spiked down (we'd be catching a bottom)
        if pct_change <= -PUMP_MODE_THRESH:
            return 'down', pct_change, True, True   # pump mode SHORT
        elif pct_change <= -COUNTERSPIKE_THRESH:
            return 'down', pct_change, True, False  # counter-spike → reverse to SHORT

    return None, pct_change, False, False


def _get_reverse_signal_name(direction: str) -> str:
    return 'LONG' if direction == 'SHORT' else 'SHORT'


def score_for_counter_spike(token: str, direction: str, long_mult: float, short_mult: float) -> Tuple[float, List, str]:
    """
    Score the reverse direction when a counter-spike is detected.
    Reuses the existing compute_score logic but for the OPPOSITE direction.

    Returns (score, signals, pump_reason)
    - score: signal confidence for the reverse direction
    - signals: formatted signal list for logging
    - pump_reason: e.g. 'pump-ctx-long' or 'ctx-long' (pump vs counter-spike)
    """
    opp_dir = _get_reverse_signal_name(direction)

    # Use a flat multiplier for the reverse direction (trend filter already applied to original signal)
    opp_mult_long = 1.0
    opp_mult_short = 1.0

    opp_score, opp_signals = compute_score(token, opp_dir, opp_mult_long, opp_mult_short)
    pump_reason = f'pump-{opp_dir.lower()}'
    return opp_score, opp_signals, pump_reason





# ═══════════════════════════════════════════════════════════════
# Main


# ═══════════════════════════════════════════════════════════════════════════
# Confluence helpers — defined BEFORE run() so they're in scope
# ═══════════════════════════════════════════════════════════════════════════
# ── RSI signals for confluence ────────────────────────────────────────────────
def _run_rsi_signals_for_confluence():
    """Add RSI as standalone signal — filtered to only fire when trend aligns."""
    from signal_schema import compute_rsi, compute_zscore
    prices_dict = get_all_latest_prices()
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    # Get broad market trend once
    broad_z_vals = []
    for tok in BROAD_MARKET_TOKENS:
        zs = get_tf_zscores(tok)
        if '4h' in zs and zs['4h'][0] is not None:
            broad_z_vals.append(zs['4h'][0])
    broad_avg = statistics.mean(broad_z_vals) if broad_z_vals else 0
    # SHORT_BLACKLIST is imported from hermes_constants at module level
    added = 0
    for token, data in prices_dict.items():
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue
        rsi = compute_rsi(token, lookback_minutes=60*4)
        if not rsi:
            continue
        z = compute_zscore(token)
        z_tier = 'suppressed' if z is not None and z < -0.5 else ('normal' if z is not None and abs(z) <= 0.5 else 'elevated') if z is not None else None
        price = data['price']
        if rsi < CONFLUENCE_RSI_LOW:
            # ── LONG: RSI oversold (below LOW threshold = deeply oversold) + z-score suppressed ──
            if broad_avg > BROAD_UPTEND_Z:
                continue  # broad market too bullish, skip LONG
            if z is None or z > LONG_1H_Z_MAX:
                continue  # token not suppressed enough
            conf = min(50, 30 + (CONFLUENCE_RSI_LOW - rsi) * 1.5)
            if conf < ENTRY_THRESHOLD and not (rsi < 15):
                continue  # weak signal, not extreme → skip entirely
            add_signal(token, 'LONG', 'rsi_confluence', 'rsi-confluence',
                       confidence=conf, value=rsi, price=price, exchange='hyperliquid',
                       z_score=z, z_score_tier=z_tier)
            added += 1
        elif rsi > CONFLUENCE_RSI_HIGH:
            # ── SHORT: RSI overbought (above HIGH threshold = overbought) ──
            # No z-score filter for SHORTs — elevated prices are valid short targets
            if token.upper() in SHORT_BLACKLIST:
                continue
            conf = min(50, 30 + (rsi - CONFLUENCE_RSI_HIGH) * 1.5)
            if conf < ENTRY_THRESHOLD and not (rsi > 85):
                continue  # weak signal, not extreme → skip entirely
            add_signal(token, 'SHORT', 'rsi_confluence', 'rsi-confluence',
                       confidence=conf, value=rsi, price=price, exchange='hyperliquid',
                       z_score=z, z_score_tier=z_tier)
            added += 1
    return added


# ── MTF-MACD: Multi-Timeframe MACD confirmation ───────────────────────────────
# Replaces the broken OpenClaw mtf_macd_signals.py pipeline.
# Detects when MACD is bullish/bearish across 4H+1H+15m timeframes.
# Writes as 'mtf_macd' signal_type so confluence detection can cross-match it.

def _run_mtf_macd_signals():
    """
    Native Hermes MTF-MACD: check if MACD histogram agrees across 4H/1H/15m.
    Replaces OpenClaw mtf_macd_signals.py which is broken (PENDING-duplicate blocker).

    Logic: for each token, fetch closes at 4H/1H/15m windows, compute MACD fast
    (12/26/9 equivalent), count bullish TFs (macd_line > 0).
    3/3 = STRONG, 2/3 = NORMAL, 1/3 = WEAK.
    """
    from signal_schema import compute_macd, compute_zscore

    prices_dict = get_all_latest_prices()
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    # SHORT_BLACKLIST is imported from hermes_constants at module level
    added = 0

    def _macd_crossover(token, minutes):
        """
        Compute MACD crossover for a token at given timeframe.
        Returns (histogram: float, macd_line: float, signal_line: float) or None.
        histogram > 0 means MACD line is ABOVE signal line → bullish  → LONG
        histogram < 0 means MACD line is BELOW signal line → bearish → SHORT
        """
        m = compute_macd(token, lookback_minutes=minutes)
        if not m:
            return None
        return (m.get('histogram', 0), m.get('macd', 0), m.get('signal', 0))

    # ── Individual RSI + MACD signals for sub-component confluence ──────────
    # These write to DB with distinct signal_types so confluence can cross-match.
    # Excluded from OC pipeline (source != 'mtf-*') — Hermes-only.

    for token, data in prices_dict.items():
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue

        price = data['price']
        mom = get_momentum_stats(token)
        if not mom:
            continue

        rsi_val  = mom.get('rsi_14')
        macd_val = mom.get('macd_line')
        macd_hist = mom.get('macd_hist')
        pct_long  = mom.get('percentile_long', 50)
        pct_short = mom.get('percentile_short', 50)
        velocity  = mom.get('velocity', 0)
        avg_z     = mom.get('avg_z', 0)
        phase     = mom.get('phase', 'quiet')
        z_dir     = mom.get('z_direction', 'neutral')

        # ── MTF MACD check ────────────────────────────────────────
        # Use histogram (MACD line - signal line) for direction, NOT raw MACD line.
        # histogram > 0 = MACD above signal = bullish → LONG
        # histogram < 0 = MACD below signal = bearish → SHORT
        xo_4h  = _macd_crossover(token, 60*4)
        xo_1h  = _macd_crossover(token, 60*1)
        xo_15m = _macd_crossover(token, 15)

        # Collect valid (histogram, macd, signal) tuples per TF
        valid = {}
        for tf, xo in [('4h', xo_4h), ('1h', xo_1h), ('15m', xo_15m)]:
            if xo is not None:
                valid[tf] = xo

        if len(valid) >= 2:
            # At least 2 TFs have MACD data → use crossover agreement across TFs
            bullish_tfs = sum(1 for tf, (h, m, s) in valid.items() if h > 0)
            total_tfs   = len(valid)
            direction   = 'LONG' if bullish_tfs >= total_tfs / 2 else 'SHORT'
            strength    = bullish_tfs  # how many TFs agree
            timeframe_str = f'{min(bullish_tfs, total_tfs)}tf+'
        elif len(valid) == 1:
            # Single TF → use histogram direction
            tf, (h, m, s) = next(iter(valid.items()))
            direction = 'LONG' if h > 0 else 'SHORT'
            strength  = 1
            timeframe_str = tf
        else:
            continue  # no MACD data at all

        # Blacklist + z-score filters
        if direction == 'LONG':
            if avg_z is None or avg_z > LONG_1H_Z_MAX:
                continue
        else:
            if token.upper() in SHORT_BLACKLIST:
                continue

        # Confidence based on TF agreement strength
        base_conf = 40 + strength * 15  # 2tf=70, 3tf=85, 1tf=55
        conf = min(95, base_conf)

        # ── Write mtf_macd signal ────────────────────────────────
        # Source = 'hmacd-' — prefixed so add_signal() merge combines
        # Hermes rows separately from OC 'mtf-macd' rows (different source string)
        add_signal(token, direction, 'mtf_macd', 'hmacd-',
                   confidence=conf, value=strength, price=price,
                   exchange='hyperliquid', timeframe=timeframe_str,
                   macd_value=macd_val, macd_hist=macd_hist,
                   z_score=avg_z, z_score_tier=z_dir,
                   rsi_14=rsi_val)

        # ── Individual RSI signal (Hermes-only, distinct signal_type) ────
        if rsi_val is not None:
            if rsi_val < 40:  # oversold → potential LONG
                if direction == 'LONG':  # only when aligned
                    rsi_conf = min(60, 30 + (40 - rsi_val) * 1.5)
                    add_signal(token, 'LONG', 'rsi_individual', 'rsi-hermes',
                                confidence=rsi_conf, value=rsi_val, price=price,
                                exchange='hyperliquid', timeframe='4h',
                                rsi_14=rsi_val, z_score=avg_z, z_score_tier=z_dir)
                    added += 1
            elif rsi_val > 65:  # overbought → potential SHORT
                if direction == 'SHORT':
                    rsi_conf = min(60, 30 + (rsi_val - 65) * 1.5)
                    add_signal(token, 'SHORT', 'rsi_individual', 'rsi-hermes',
                                confidence=rsi_conf, value=rsi_val, price=price,
                                exchange='hyperliquid', timeframe='4h',
                                rsi_14=rsi_val, z_score=avg_z, z_score_tier=z_dir)
                    added += 1

        # ── Percentile rank signal (Hermes-only) ──────────────────────────
        # Fires when price is at historical extreme (suppressed or elevated)
        pct_signal_dir = None
        if pct_long >= 85 or pct_short >= 85:
            pct_signal_dir = 'LONG' if pct_long >= 85 else 'SHORT'
            pct_val = max(pct_long, pct_short)
            # Normalize percentile_rank to signal-strength equivalent.
            # pct_val 85→15pts, pct_val 100→50pts. Cap at 50 so it contributes
            # proportionally to other signals (z_score: 0-30, velocity: 0-10).
            pct_conf = min(50, (pct_val - 70) * (50.0 / 30.0))
            add_signal(token, pct_signal_dir, 'percentile_rank', 'pct-hermes',
                        confidence=round(pct_conf, 1), value=pct_val, price=price,
                        exchange='hyperliquid', timeframe='4h',
                        z_score=avg_z, z_score_tier=z_dir,
                        rsi_14=rsi_val)
            added += 1

        # ── Velocity signal (rising/falling z-score) ──────────────────────
        # Fires when z-score momentum is strong and aligned with direction
        vel_signal_dir = None
        if abs(velocity) >= 0.03:  # meaningful momentum
            vel_signal_dir = 'SHORT' if velocity > 0 else 'LONG'
            if vel_signal_dir == direction:  # aligned
                vel_conf = min(65, 35 + abs(velocity) * 500)
                add_signal(token, vel_signal_dir, 'velocity', 'vel-hermes',
                            confidence=vel_conf, value=round(velocity, 4), price=price,
                            exchange='hyperliquid', timeframe='1h',
                            z_score=avg_z, z_score_tier=z_dir,
                            rsi_14=rsi_val)
                added += 1

        added += 1  # count mtf_macd

        # ── MTF Z-Score Agreement ────────────────────────────────
        # Fires when z-score agrees across multiple timeframes (4H/1H/15m)
        # All agreeing = strong momentum; mixed = weak signal; all disagree = skip
        zscores = get_tf_zscores(token)
        z_4h  = zscores.get('4h',  (None, None))[0]
        z_1h  = zscores.get('1h',  (None, None))[0]
        z_15m = zscores.get('15m', (None, None))[0]
        valid_z = [v for v in [z_4h, z_1h, z_15m] if v is not None]
        if len(valid_z) >= 2:
            agreeing = sum(1 for v in valid_z if v > 0)   # bullish TFs
            disagreeing = len(valid_z) - agreeing            # bearish TFs
            if agreeing >= 2:
                z_dir = 'LONG'
                z_conf = min(80, 45 + len(valid_z) * 8 + agreeing * 5)
                z_tf_str = f'{agreeing}z{len(valid_z)}'
            elif disagreeing >= 2:
                z_dir = 'SHORT'
                z_conf = min(80, 45 + len(valid_z) * 8 + disagreeing * 5)
                z_tf_str = f'{disagreeing}z{len(valid_z)}'
            else:
                z_tf_str = None  # mixed, skip

            if z_tf_str:
                add_signal(token, z_dir, 'mtf_zscore', 'hzscore',
                           confidence=z_conf, value=round(statistics.mean(valid_z), 3),
                           price=price, exchange='hyperliquid', timeframe=z_tf_str,
                           z_score=avg_z, z_score_tier=z_dir,
                           rsi_14=rsi_val)
                added += 1

    return added


# ── MACD signals for confluence (legacy — kept for signal_type compat) ───────
def _run_macd_signals_for_confluence():
    """Legacy MACD histogram signal — kept for confluence compatibility."""
    from signal_schema import compute_macd, compute_zscore
    prices_dict = get_all_latest_prices()
    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    # SHORT_BLACKLIST is imported from hermes_constants at module level
    added = 0
    for token, data in prices_dict.items():
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        macd = compute_macd(token, lookback_minutes=60*24)
        if not macd:
            continue
        h = macd['histogram']
        z = compute_zscore(token)
        z_tier = 'suppressed' if z is not None and z < -0.5 else ('normal' if z is not None and abs(z) <= 0.5 else 'elevated') if z is not None else None
        price = data['price']
        if abs(h) < CONFLUENCE_MACD_HIST_THRESH:
            continue
        direction = 'LONG' if h > 0 else 'SHORT'
        if direction == 'LONG':
            if z is None or z > LONG_1H_Z_MAX:
                continue
        else:
            if token.upper() in SHORT_BLACKLIST:
                continue
        conf = min(50, 30 + abs(h) * 300)
        has_partner = _has_confluence_partners(token, direction, exclude_type='macd_confluence')
        if conf < ENTRY_THRESHOLD and not (abs(h) > 0.05):
            continue
        add_signal(token, direction, 'macd_confluence', 'macd-confluence',
                   confidence=conf, value=h, price=price,
                   macd_value=macd.get('macd'), macd_signal=macd.get('signal'),
                   macd_hist=h, exchange='hyperliquid',
                   z_score=z, z_score_tier=z_tier)
        added += 1
    return added


# ── Confluence Detection ───────────────────────────────────────────────────────
# After all individual signals (momentum, RSI, MACD) are added to the DB,
# detect tokens where ≥2 signal types agree and add a boosted confluence signal.
# Confluence boosts: 2 agreeing signals → 1.25x, 3+ → 1.5x
# Auto-approve: ≥CONFLUENCE_AUTO_APPROVE (85%) → no AI decider needed
# This replicates the "conf-2s" / "conf-4s" / "conf-8s" pattern that OpenClaw
# used successfully to filter noise and improve hit rate.



def run_confluence_detection():
    """Check for tokens where ≥2 signal types agree, add boosted confluence signal."""
    # Query open positions locally (open_pos is in run() scope, not accessible here)
    open_pos_local = {t: d for t, d in [(p['token'], p['direction']) for p in _get_open_pos()]}

    # Get confluence groups: tokens with ≥2 PENDING signal types in last 60 min.
    # Includes ALL signal types — both Hermes (rsi_confluence, macd_confluence, momentum)
    # and OpenClaw (mtf_macd, rsi, z_score, mtf-momentum+rsi, etc).
    # The mtf- vs Hermes distinction is determined by source prefix, not signal_type.
    confluences = get_confluence_signals(hours=1, min_signals=CONFLUENCE_MIN_SIGNALS,
                                         signal_types=None)  # query all types

    confluences_added = 0
    for c in confluences:
        token = c['token']
        direction = c['direction']
        num_signals = c.get('num_types') or c.get('count')
        avg_conf = c['avg_conf']

        # Don't add confluence for tokens we already have a position on
        if token in open_pos_local:
            continue
        # Blacklist enforcement at confluence level
        if direction.upper() == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            continue
        if direction.upper() == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue

        # Rate limit
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue

        # Fetch per-source confidences from both DBs for accurate scoring.
        # OpenClaw mtf- signals are floored at 70%.
        # Hermes RSI/MACD contribute their actual confidence.
        conn = sqlite3.connect('/root/.hermes/data/signals_hermes_runtime.db')
        cc = conn.cursor()
        if os.path.exists('/root/.openclaw/workspace/data/signals.db'):
            try:
                cc.execute("ATTACH DATABASE '/root/.openclaw/workspace/data/signals.db' AS oc")
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"[signal_gen] Non-fatal error: {e}")
        cc.execute('''
            SELECT source, confidence FROM (
                SELECT source, confidence FROM signals
                WHERE token=? AND direction=? AND decision='PENDING'
                AND created_at > datetime('now','-60 minutes')
                AND source NOT LIKE 'mtf-%%'  -- Hermes signals only
                UNION ALL
                SELECT source, confidence FROM oc.signals
                WHERE token=? AND direction=? AND decision='PENDING'
                AND created_at > datetime('now','-30 minutes')  -- OC signals: stricter 30-min freshness
                AND source LIKE 'mtf-%%'  -- OpenClaw mtf signals only
            )
        ''', (token, direction, token, direction))
        all_rows = cc.fetchall()
        conn.close()
        if not all_rows:
            continue

        # Separate and score
        mtf_rows     = [(src, max(70, conf)) for src, conf in all_rows if src and src.startswith('mtf-')]
        hermes_rows  = [(src, conf) for src, conf in all_rows if src and not src.startswith('mtf-')]
        hermes_confs = [conf for _, conf in hermes_rows]
        mtf_confs    = [conf for _, conf in mtf_rows]
        hermes_avg   = statistics.mean(hermes_confs) if hermes_confs else 0
        mtf_avg      = statistics.mean(mtf_confs) if mtf_confs else 0
        # Take the HIGHER of hermes_avg vs mtf_avg, not the average.
        # If only Hermes signals exist: base = hermes_avg.
        # If only mtf signals exist: base = mtf_avg.
        # If both exist: base = max(hermes_avg, mtf_avg) — the stronger signal wins.
        base_avg     = max(hermes_avg, mtf_avg) if (hermes_avg or mtf_avg) else 0
        mtf_sources_str    = ','.join(sorted(set(src for src, _ in mtf_rows))) if mtf_rows else 'none'
        hermes_sources_str = ','.join(sorted(set(src for src, _ in hermes_rows))) if hermes_rows else 'none'

        if base_avg < 35:
            continue
        # Sanity cap: no more than 3 agreeing signal types can contribute to a confluence.
        # Any query returning >3 is a bug (OpenClaw ATTACH issue, stale archives, or
        # counting sources instead of signal_types). Cap at 3 to prevent conf-4s, conf-10s, etc.
        num_signals = min(num_signals, 3)

        if num_signals >= 3:
            boosted = min(99, base_avg * 1.5)
        else:
            boosted = min(99, base_avg * 1.25)

        mtf_sources    = mtf_sources_str
        hermes_sources = hermes_sources_str

        prices_dict = get_all_latest_prices()
        price = prices_dict.get(token, {}).get('price') if prices_dict else None
        if not price:
            continue

        sid = add_confluence_signal(
            token=token,
            direction=direction,
            confidence=boosted,
            num_signals=num_signals,
            price=price,
            z_score=c.get('z_score'),
            rsi_14=c.get('rsi_14'),
            macd_hist=c.get('macd_hist'),
        )

        # Log full source breakdown for post-trade study — which combo worked?
        log(f'CONFLUENCE: {token} {direction} @{price:.6f} '
            f'conf={boosted:.1f}% ({num_signals}s) '
            f'mtf=[{mtf_sources}] hermes=[{hermes_sources}] '
            f'mtf_avg={mtf_avg:.1f}% hermes_avg={hermes_avg:.1f}%')
        print(f'  CONFLUENCE {token:8s} {direction:5s} conf={boosted:5.1f}% ({num_signals}s) '
              f'mtf=[{mtf_sources}] hermes=[{hermes_sources}]')

        set_cooldown(token, direction, hours=1)
        confluences_added += 1

    print(f'  Confluence: {confluences_added} confluence signals added')
    return confluences_added


# ═══════════════════════════════════════════════════════════════

def run():
    init_db()
    expire_pending_signals(minutes=15)  # Reset stale PENDING signals each cycle
    _ZSCORE_CACHE.clear()
    _VOL_CACHE.clear()
    prices_dict = get_all_latest_prices()
    regime, long_mult, short_mult, broad_trending_up, broad_z_avg = compute_regime()
    print(f'=== Signal Gen | Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | Broad BTC/ETH/SOL 4h z={broad_z_avg:+.2f} | {len(prices_dict)} tokens')
    log(f'REGIME: {regime.upper()} L:x{long_mult:.1f} S:x{short_mult:.1f} broad_z={broad_z_avg:+.2f} | {len(prices_dict)} tokens')

    from position_manager import get_open_positions as _get_open_pos, get_opposite_direction_cooldown_hours
    open_pos = _get_open_pos()
    added    = 0
    blocked  = 0
    exits    = []
    active_tokens = set(prices_dict.keys())
    print(f'  Active universe: {len(active_tokens)} tokens (full universe)')

    # Volume prefetch DISABLED — HL rate limits aggressively on /info recentTrades.
    # Volume ROC is 0-10 bonus pts only. Cold cache means vol_score=0 for all tokens,
    # which is fine — the scoring model still works, just without the volume bonus.
    # To re-enable: fetch volume in a separate slower cron job (e.g. every 5 min).
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
                    # Use RSI/MACD cached in get_momentum_stats() (called at line 1349)
                    rsi_14_val = mom.get('rsi_14') if mom else None
                    macd_line_val = mom.get('macd_line') if mom else None
                    macd_hist_val = mom.get('macd_hist') if mom else None
                    macd_signal_val = mom.get('macd_signal') if mom else None
                    sources = '+'.join(sorted(set(s[0] for s in signals)))
                    reasons = ' | '.join(s[3] for s in signals[:4])

                    # ── Spike Detection ───────────────────────────────
                    spike_type, pct_chg, do_reverse, is_pump = detect_spike(token, 'LONG', price)
                    if do_reverse:
                        opp_score, opp_signals, pump_tag = score_for_counter_spike(
                            token, 'LONG', long_mult, short_mult)
                        opp_dir = _get_reverse_signal_name('LONG')
                        opp_sources = '+'.join(sorted(set(s[0] for s in opp_signals))) if opp_signals else 'momentum'
                        opp_reasons = ' | '.join(s[3] for s in opp_signals[:3]) if opp_signals else 'reverse'
                        if is_pump:
                            pump_tag = f'pump-{opp_dir.lower()}'
                            log(f'PUMP:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[spike{spike_type}+{pct_chg:.1f}%] {pump_tag} {opp_reasons}')
                            print(f'  PUMP  {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} spike-{spike_type}+{pct_chg:.1f}%]')
                        else:
                            log(f'REV:   {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[counter-spike{spike_type}+{pct_chg:.1f}%] {opp_reasons}')
                            print(f'  REV   {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} ctx-spike-{spike_type}+{pct_chg:.1f}%]')
                        if opp_score and opp_score >= ENTRY_THRESHOLD:
                            add_signal(
                                token=token, direction=opp_dir, signal_type='momentum',
                                source=f'mtf-{opp_sources}', confidence=opp_score,
                                value=opp_score, price=price,
                                exchange='hyperliquid',
                                timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                                z_score=mom['avg_z'] if mom else None,
                                z_score_tier=mom['z_direction'] if mom else None,
                                rsi_14=rsi_14_val,
                                macd_value=macd_line_val,
                                macd_signal=macd_signal_val,
                                macd_hist=macd_hist_val,
                            )
                            # All momentum signals → PENDING → decider-run (no auto-approve)
                            log(f'SIGNAL:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% [{pump_tag}] {opp_reasons}')
                            set_cooldown(token, opp_dir, hours=1)
                            added += 1
                    else:
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
                        # All momentum signals → PENDING → decider-run (no auto-approve)
                        log(f'SIGNAL:  {token} LONG @{price:.6f} {score:.1f}% {reasons}')
                        print(f'  LONG  {token:8s} {score:5.1f}% [AI-DECIDER]  {reasons}')
                        set_cooldown(token, 'LONG', hours=1)
                        added += 1

        # ── SHORT signals ─────────────────────────────────────
        if token not in open_pos or open_pos[token] != 'SHORT':
            score, signals = compute_score(token, 'SHORT', long_mult, short_mult)
            if score and score >= ENTRY_THRESHOLD:
                # ── Trend filter ────────────────────────────────
                short_ok, short_filter_reason = check_short_trend_filter(token)
                if not short_ok:
                    log(f'BLOCKED SHORT: {token} @{price:.6f} {score:.1f}% [{short_filter_reason}]')
                    print(f'  SHORT-B {token:8s} {score:5.1f}% [BLOCKED] {short_filter_reason}')
                    blocked += 1
                else:
                    sources = '+'.join(sorted(set(s[0] for s in signals)))
                    reasons = ' | '.join(s[3] for s in signals[:4])

                    # ── Spike Detection ───────────────────────────────
                    spike_type, pct_chg, do_reverse, is_pump = detect_spike(token, 'SHORT', price)
                    if do_reverse:
                        opp_score, opp_signals, pump_tag = score_for_counter_spike(
                            token, 'SHORT', long_mult, short_mult)
                        opp_dir = _get_reverse_signal_name('SHORT')
                        opp_sources = '+'.join(sorted(set(s[0] for s in opp_signals))) if opp_signals else 'momentum'
                        opp_reasons = ' | '.join(s[3] for s in opp_signals[:3]) if opp_signals else 'reverse'
                        if is_pump:
                            pump_tag = f'pump-{opp_dir.lower()}'
                            log(f'PUMP:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[spike-{spike_type}+{pct_chg:.1f}%] {pump_tag} {opp_reasons}')
                            print(f'  PUMP  {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} spike-{spike_type}+{pct_chg:.1f}%]')
                        else:
                            log(f'REV:   {token} {opp_dir} @{price:.6f} {opp_score:.1f}% '
                                f'[counter-spike{spike_type}+{pct_chg:.1f}%] {opp_reasons}')
                            print(f'  REV   {token:8s} {opp_score:5.1f}% [REVERSE->{opp_dir} ctx-spike-{spike_type}+{pct_chg:.1f}%]')
                        if opp_score and opp_score >= ENTRY_THRESHOLD:
                            add_signal(
                                token=token, direction=opp_dir, signal_type='momentum',
                                source=f'mtf-{opp_sources}', confidence=opp_score,
                                value=opp_score, price=price,
                                exchange='hyperliquid',
                                timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                                z_score=mom['avg_z'] if mom else None,
                                z_score_tier=mom['z_direction'] if mom else None,
                            )
                            # All momentum signals → PENDING → decider-run (no auto-approve)
                            log(f'SIGNAL:  {token} {opp_dir} @{price:.6f} {opp_score:.1f}% [{pump_tag}] {opp_reasons}')
                            set_cooldown(token, opp_dir, hours=1)
                            added += 1
                    else:
                        add_signal(
                            token=token, direction='SHORT', signal_type='momentum',
                            source=f'mtf-{sources}', confidence=score,
                            value=score, price=price,
                            exchange='hyperliquid',
                            timeframe=f'{mom["phase"][:3] if mom else "unk"}',
                            z_score=mom['avg_z'] if mom else None,
                            z_score_tier=mom['z_direction'] if mom else None,
                        )
                        # All momentum signals → PENDING → decider-run (no auto-approve)
                        log(f'SIGNAL:  {token} SHORT @{price:.6f} {score:.1f}% {reasons}')
                        print(f'  SHORT {token:8s} {score:5.1f}% [AI-DECIDER]  {reasons}')
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

    # ── Confluence Detection ────────────────────────────────────
    # FIXED: must run RSI and MACD individual signal generators FIRST,
    # THEN detect confluences. Previously the RSI/MACD functions were
    # defined but never called, so confluence detection always found 0.
    confluences_added = 0
    try:
        rsi_added   = _run_rsi_signals_for_confluence()
        macd_added  = _run_macd_signals_for_confluence()
        mtf_added   = _run_mtf_macd_signals()  # native MTF-MACD + sub-signal writers
        if rsi_added or macd_added:
            print(f'  RSI/MACD signals: {rsi_added} RSI + {macd_added} MACD + {mtf_added} MTF-MACD added')
        confluences_added = run_confluence_detection()
    except Exception as e:
        print(f'  Confluence detection error: {e}')
    print(f'  Confluence: {confluences_added} confluence signals added')

    # ── Pipeline heartbeat ─────────────────────────────────────────────────────
    _update_heartbeat('signal_gen')

    return added, exits

if __name__ == '__main__':
    import sys
    if sys.stdin is not None and hasattr(sys.stdin, 'fileno'):
        try:
            sys.stdin = open('/dev/null', 'r')
        except Exception:
            pass
    run()
