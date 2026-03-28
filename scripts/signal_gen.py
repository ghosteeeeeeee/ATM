#!/usr/bin/env python3
"""
signal_gen.py — Hermes signal generation with momentum-based z-score analysis.

Architecture:
  - Multi-TF z-score (1m, 5m, 15m, 30m, 1h, 4h) from local price history
  - Z-score percentile rank: how unusual is this z for THIS token? (rolling 500-bar)
  - Z-score velocity: is z rising or falling? (momentum direction)
  - Phase detection: quiet | building | accelerating | exhaustion | extreme
  - LONG: rising z + moderate-high percentile rank
  - SHORT: falling z from exhaustion zone + confirmation
  - Entry: >=65 | Auto-approve: >=85
"""
import sys, sqlite3, time, os, json, statistics, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import (
    init_db, DB_PATH, get_all_latest_prices, get_price_history,
    get_latest_price, add_signal, set_cooldown, get_cooldown,
    price_age_minutes, approve_signal, update_signal_decision,
    mark_signal_processed
)

LOG_FILE = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ─── Momentum phase thresholds ─────────────────────────────────
# Based on z-score percentile rank (how unusual for this token)
PHASE_BUILDING    = 60    # percentile ≥60 → momentum starting
PHASE_ACCELERATING= 75    # percentile ≥75 → strong momentum
PHASE_EXHAUSTION  = 88    # percentile ≥88 → late phase, watch for exit
PHASE_EXTREME     = 95    # percentile ≥95 → exhaustion/mean-reversion territory

# Entry score thresholds
ENTRY_THRESHOLD   = 65    # min score to add signal
AUTO_APPROVE      = 85    # ≥ this → auto-approve
EXIT_THRESHOLD    = 55    # opposite signal ≥ this → consider closing

# Z-score lookback for percentile ranking (in price rows, ~1 row/min)
ZSCORE_HISTORY    = 500   # compute percentile from last 500 bars

# ─── Scoring weights ────────────────────────────────────────────
W_PERCENTILE      = 3.0   # percentile rank is primary signal
W_VELOCITY        = 2.0   # momentum direction (rising/falling z)
W_RSI             = 1.0   # RSI confirmation
W_MACD            = 0.8   # MACD confirmation

# ─── Timeframe windows ──────────────────────────────────────────
TF_WINDOWS = [
    ('1m',  20),   # 20 minutes
    ('5m',  60),   # 1 hour
    ('15m', 120),  # 2 hours
    ('30m', 240),  # 4 hours
    ('1h',  480),  # 8 hours
    ('4h', 1440),  # 24 hours
]

TOP_TOKENS = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'AVAX', 'LINK',
              'DOGE', 'DOT', 'ATOM', 'UNI', 'MATIC', 'FIL']

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

    # Directional percentiles
    # pct_long: what % of historical z-scores are BELOW current z?
    #   if current_z is very negative → pct_long is high
    # pct_short: what % of historical z-scores are ABOVE current z?
    #   if current_z is very positive → pct_short is high
    above = sum(1 for z in z_values if z >= current_z)
    pct_long  = round((below / len(z_values)) * 100, 1)
    pct_short = round((above / len(z_values)) * 100, 1)

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
# Z-Score Multi-Timeframe Analysis
# ═══════════════════════════════════════════════════════════════

def get_tf_zscores(token, max_rows=60480):
    """Z-score across all timeframes. Returns {tf_name: (z, tier)}."""
    rows = get_price_history(token, lookback_minutes=max_rows)
    if len(rows) < 60:
        return {}
    prices = [r[1] for r in rows]
    results = {}
    for tf_name, window in TF_WINDOWS:
        window_prices = prices[-window:] if len(prices) >= window else prices
        z, tier = zscore(window_prices)
        if z is not None:
            results[tf_name] = (z, tier)
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
    for tok in TOP_TOKENS:
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
    phase            = mom['phase']
    avg_z            = mom['avg_z']

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
        # Give positive score for suppressed prices, 0 for elevated
        # Threshold: pct_long < 50 = suppressed (below median), score based on depth
        # pct 50→0pts, pct 35→60pts, pct 20→120pts (capped)
        if pct >= 50:
            return 0.0
        return max(0.0, (50 - pct) / 15 * 60)

    def pct_short_score_fn(pct):
        # pct_short = % above current → HIGH = elevated = good for SHORT
        # Give positive score for elevated prices, 0 for suppressed
        # Threshold lowered to 35 (moderate elevation triggers shorts)
        # pct 35→0pts, pct 50→60pts, pct 65→120pts (capped)
        if pct <= 35:
            return 0.0
        return max(0.0, (pct - 35) / 15 * 60)

    p_long  = pct_long_score_fn(percentile_long)
    p_short = pct_short_score_fn(percentile_short)
    pct_score = p_long if direction == 'LONG' else p_short

    # ── Phase filter ──────────────────────────────────────────
    if phase == 'quiet':
        return None, None

    elif phase == 'extreme':
        if direction == 'LONG':
            return None, None   # never long in extreme zone
        # Shorts in extreme get full score
        phase_mod = +5
        phase_reason = 'extreme-short'

    elif phase == 'exhaustion':
        if direction == 'LONG':
            phase_mod = -5
            phase_reason = 'exhaustion-partial'
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
    Z_SCALE = 40  # z=-1.5 → 60 pts for LONG
    if direction == 'LONG':
        z_score = max(0.0, -avg_z * Z_SCALE)  # neg z → positive score
    else:
        z_score = max(0.0, avg_z * Z_SCALE)   # pos z → positive score

    # ── Velocity contribution (0-20 pts) ────────────────────────
    # Rising z = recovering = good for LONG
    # Falling z = declining = good for SHORT
    VEL_SCALE = 200  # velocity = ±0.1 → ±20 pts
    if direction == 'LONG':
        vel_score = max(0.0, velocity * VEL_SCALE)
    else:
        vel_score = max(0.0, -velocity * VEL_SCALE)

    # ── RSI confirmation (0-3 pts) ─────────────────────────────
    rsi_val = rsi(prices) if len(prices) >= 30 else None
    rsi_score = 0.0
    rsi_reason = ''
    if rsi_val is not None:
        if direction == 'LONG' and rsi_val < 50:
            rsi_score = W_RSI * (50 - rsi_val) / 30
            if rsi_val < 40:
                rsi_reason = f'RSI={rsi_val:.0f}(oversold)'
        elif direction == 'SHORT' and rsi_val > 50:
            rsi_score = W_RSI * (rsi_val - 50) / 30
            if rsi_val > 60:
                rsi_reason = f'RSI={rsi_val:.0f}(overbought)'

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

    # ── Score assembly ─────────────────────────────────────────
    # z_score: 0-60 | velocity: 0-20 | phase: ±5 | regime: 0-5 | rsi: 0-3 | macd: 0-1
    score = z_score + vel_score + phase_mod + regime_mod + rsi_score + macd_score
    score = min(99.0, max(0, round(score, 1)))

    if score < ENTRY_THRESHOLD:
        return None, None

    # ── Build signal reasons ───────────────────────────────────
    pct_dir = percentile_long if direction == 'LONG' else percentile_short
    reasons = [
        f'pct={pct_dir:.0f}%({phase_reason})',
        f'z={avg_z:+.2f}({mom["z_direction"]})',
        f'vel={velocity:+.3f}',
    ]
    if rsi_reason:
        reasons.append(rsi_reason)
    if macd_reason:
        reasons.append(macd_reason)

    signals = [('momentum', '1h', score, reasons[0])]
    if rsi_reason:
        signals.append(('rsi', '1h', rsi_score, rsi_reason))
    if macd_reason:
        signals.append(('macd', '1h', macd_score, macd_reason))

    return score, signals


# ═══════════════════════════════════════════════════════════════
# Open Positions
# ═══════════════════════════════════════════════════════════════

def get_open_positions():
    """Return {token: direction} for all open Hermes positions."""
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain',
                                user='postgres', password='Brain123')
        cur = conn.cursor()
        cur.execute("SELECT token, direction FROM trades WHERE server='Hermes' AND status='open'")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return {r[0]: r[1] for r in rows}
    except:
        return {}


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def run():
    init_db()
    prices_dict = get_all_latest_prices()
    regime, long_mult, short_mult, broad_trending_up, broad_z_avg = compute_regime()

    trend_flag = ' [BROAD UPTREND]' if broad_trending_up else ''
    print(f'=== Signal Gen | Regime: {regime.upper()} (L:x{long_mult:.1f} S:x{short_mult:.1f}) | Broad BTC/ETH/SOL 4h z={broad_z_avg:+.2f}{trend_flag} | {len(prices_dict)} tokens')
    log(f'REGIME: {regime.upper()} L:x{long_mult:.1f} S:x{short_mult:.1f} broad_z={broad_z_avg:+.2f}{trend_flag} | {len(prices_dict)} tokens')

    open_pos = get_open_positions()
    added    = 0
    blocked  = 0
    exits    = []

    for token, data in prices_dict.items():
        if price_age_minutes(token) > 10:
            continue
        if not data.get('price') or data['price'] <= 0:
            continue
        if get_cooldown(token):
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
                    )
                    if score >= AUTO_APPROVE:
                        mark_signal_processed(token, 'LONG')
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
                    mark_signal_processed(token, 'SHORT')
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
    run()
