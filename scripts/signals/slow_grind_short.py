#!/usr/bin/env python3
"""
slow_grind_short — Catch slow, grinding downtrends with low volatility.

Thesis: Some of the best SHORT trades are gradual declines, not sharp drops.
        These "slow grinds" have:
        - Consistent lower highs/lower lows
        - Low ATR (small daily ranges)
        - Price below key EMAs (EMA20, EMA50)
        - Negative but not extreme momentum (RSI 40-55)
        - High R² (clean trend, not choppy)

Pattern (from GMT and HBAR slow-grind trades):
  1. R² >= 0.55 (confirmed trend, not chop)
  2. Slope < -0.0002 (meaningful downtrend)
  3. Price below EMA20 and EMA50 (bearish alignment)
  4. ATR% < 0.8% (low volatility = grinding)
  5. RSI between 35-55 (not oversold, room to grind lower)

Entry: Ride the slow grind down
Exit:  Trail stop or profit target 2-4%

Data: candles_1m and candles_5m from candles.db
"""

import sys, os, sqlite3, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    SLOW_GRIND_SHORT_ENABLED,
    SLOW_GRIND_SHORT_MIN_R2,
    SLOW_GRIND_SHORT_MIN_SLOPE_PCT,
    SLOW_GRIND_SHORT_MAX_ATR_PCT,
    SLOW_GRIND_SHORT_RSI_MIN,
    SLOW_GRIND_SHORT_RSI_MAX,
    SLOW_GRIND_SHORT_MIN_EMA_SEPARATION,
    SLOW_GRIND_SHORT_CONF_BASE,
    SLOW_GRIND_SHORT_CONF_CAP,
    SLOW_GRIND_SHORT_COOLDOWN_HOURS,
    SLOW_GRIND_SHORT_R2_BONUS_MAX,
    SLOW_GRIND_SHORT_SLOPE_BONUS_MAX,
    SLOW_GRIND_SHORT_SLOPE_NORM,
    SLOW_GRIND_SHORT_EMA_BONUS_MAX,
    SLOW_GRIND_SHORT_EMA_NORM,
    SLOW_GRIND_SHORT_ATR_LOW_THRESHOLD,
    SLOW_GRIND_SHORT_ATR_LOW_BONUS,
    SLOW_GRIND_SHORT_RSI_OVERSOLD_PENALTY_THRESHOLD,
    SLOW_GRIND_SHORT_RSI_OVERSOLD_PENALTY,
    SLOW_GRIND_SHORT_MAX_PRE_ENTRY_MOVE_PCT,
    SLOW_GRIND_SHORT_REQUIRE_NEGATIVE_5M_VEL,
    SLOW_GRIND_SHORT_MAX_DECLINE_FROM_HIGH_PCT,
    SHORT_BLACKLIST,
)

# ── Signal Identity ──────────────────────────────────────────────────────
SIGNAL_TYPE = 'slow_grind_short'
SOURCE      = 'slow-grind-'

# ── Lookback Windows ─────────────────────────────────────────────────────
CANDLES_1M_LOOKBACK = 120   # 2 hours of 1m data
CANDLES_5M_LOOKBACK = 60    # 5 hours of 5m data
R2_WINDOW = 10              # bars for R² regression (was 20, shortened to catch trends earlier)

# ── DB Path ──────────────────────────────────────────────────────────────
_CANDLES_DB = os.path.join(HERMES_DATA, 'candles.db')


# ── Helper Functions ─────────────────────────────────────────────────────

def _get_closes(token, table, limit):
    """Fetch closing prices from candle table. Returns oldest-first list."""
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute(f"""
            SELECT close FROM {table}
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT ?
        """, (token.upper(), limit))
        rows = c.fetchall()
        if not rows:
            return []
        return [r[0] for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _ols_params(y_vals):
    """Compute OLS regression: slope, intercept, R²."""
    n = len(y_vals)
    if n < 3:
        return 0.0, y_vals[-1] if y_vals else 0.0, 0.0
    
    x = list(range(n))
    xm = (n - 1) / 2.0
    ym = sum(y_vals) / n
    
    num = sum((xi - xm) * (yi - ym) for xi, yi in zip(x, y_vals))
    den = sum((xi - xm) ** 2 for xi in x)
    
    if den == 0:
        return 0.0, ym, 0.0
    
    b = num / den
    a = ym - b * xm
    
    ss_res = sum((yi - (b * xi + a)) ** 2 for xi, yi in zip(x, y_vals))
    ss_tot = sum((yi - ym) ** 2 for yi in y_vals)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    return b, a, r2


def _compute_ema(prices, period):
    """Compute EMA over price series."""
    if len(prices) < period:
        return None
    
    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period  # seed with SMA
    
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    
    return ema


def _compute_rsi(prices, period=14):
    """Compute RSI."""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _compute_atr(closes, period=14):
    """Compute ATR as percentage of price using close-to-close volatility."""
    if len(closes) < period + 1:
        return None
    
    # True Range approximation using close-to-close
    trs = []
    for i in range(1, len(closes)):
        tr = abs(closes[i] - closes[i-1])
        trs.append(tr)
    
    if len(trs) < period:
        return None
    
    atr = sum(trs[-period:]) / period
    atr_pct = (atr / closes[-1] * 100) if closes[-1] > 0 else 0
    
    return atr_pct


# ── Detection Logic ──────────────────────────────────────────────────────

def detect_slow_grind_short(token):
    """
    Detect slow grinding downtrend on 1m candles.
    
    Returns signal dict or None.
    """
    if not SLOW_GRIND_SHORT_ENABLED:
        return None
    
    # Fetch 1m candles
    closes_1m = _get_closes(token, 'candles_1m', CANDLES_1M_LOOKBACK)
    if len(closes_1m) < R2_WINDOW * 2:
        return None
    
    # ── R² Regression (trend quality) ──────────────────────────────────
    y = closes_1m[-R2_WINDOW:]
    slope, intercept, r2 = _ols_params(y)
    
    # Normalize slope by price
    slope_pct = slope / closes_1m[-1] if closes_1m[-1] > 0 else 0
    
    # Filter: need confirmed downtrend with meaningful slope
    if r2 < SLOW_GRIND_SHORT_MIN_R2:
        return None
    if slope_pct >= -SLOW_GRIND_SHORT_MIN_SLOPE_PCT:
        return None  # not declining fast enough
    
    # Price must be below regression line at current point (bearish alignment)
    # intercept is at x=0 (start of window), regression at current point is lower
    regression_at_current = slope * (R2_WINDOW - 1) + intercept
    if closes_1m[-1] >= regression_at_current:
        return None
    
    # ── EMA Check (bearish alignment) ──────────────────────────────────
    if len(closes_1m) < 50:
        return None
    
    ema20 = _compute_ema(closes_1m, 20)
    ema50 = _compute_ema(closes_1m, 50)
    
    if ema20 is None or ema50 is None:
        return None
    
    # Price must be below EMA50 (relaxed from EMA20+EMA50 to catch moves earlier)
    if closes_1m[-1] > ema50:
        return None

    # Minimum separation from EMA50 (not just barely below)
    ema_sep_50 = (ema50 - closes_1m[-1]) / closes_1m[-1] * 100

    if ema_sep_50 < SLOW_GRIND_SHORT_MIN_EMA_SEPARATION:
        return None
    
    # ── ATR Check (low volatility = grinding) ──────────────────────────
    # Use 5m candles for ATR (better representation of grinding)
    closes_5m = _get_closes(token, 'candles_5m', CANDLES_5M_LOOKBACK)
    
    if len(closes_5m) < 15:
        return None  # insufficient data to verify volatility
    
    atr_pct = _compute_atr(closes_5m, period=14)
    if atr_pct is None:
        return None  # can't compute ATR — don't fire without volatility confirmation
    
    # Filter: need low volatility (grinding, not spiking)
    if atr_pct > SLOW_GRIND_SHORT_MAX_ATR_PCT:
        return None  # too volatile — this is a spike, not a grind
    
    # ── RSI Check (not oversold) ───────────────────────────────────────
    rsi = _compute_rsi(closes_1m, period=14)
    if rsi is None:
        rsi = 50.0
    
    # Filter: RSI must be in continuation zone (not oversold)
    if rsi < SLOW_GRIND_SHORT_RSI_MIN or rsi > SLOW_GRIND_SHORT_RSI_MAX:
        return None
    
    # ── Lower Highs Confirmation ───────────────────────────────────────
    # Check that recent highs are declining (grinding pattern)
    if len(closes_1m) >= 30:
        # Split into two 15-bar windows
        window1 = closes_1m[-30:-15]
        window2 = closes_1m[-15:]
        avg1 = sum(window1) / len(window1)
        avg2 = sum(window2) / len(window2)

        # Recent average should be lower (grinding down)
        if avg2 >= avg1:
            return None

    # ── Pre-Entry Move Filter ──────────────────────────────────────────
    # Block if price already rose too much from recent low (chasing)
    if len(closes_1m) >= 10:
        recent_low = min(closes_1m[-10:])
        if recent_low > 0:
            pre_entry_move_pct = (closes_1m[-1] - recent_low) / recent_low * 100
            if pre_entry_move_pct > SLOW_GRIND_SHORT_MAX_PRE_ENTRY_MOVE_PCT:
                return None  # price already rising — don't chase

    # ── Velocity Filter ────────────────────────────────────────────────
    # Require negative 5m velocity (price declining, not rising)
    if SLOW_GRIND_SHORT_REQUIRE_NEGATIVE_5M_VEL and len(closes_1m) >= 6:
        vel_5m = (closes_1m[-1] - closes_1m[-6]) / closes_1m[-6] * 100
        if vel_5m > 0:
            return None  # price rising on 5m — don't short into strength

    # ── Decline From High Filter ───────────────────────────────────────
    # Block if price has already declined too much from recent high (shorting bottoms)
    # GRAM trade: entry at -2.38% from high — trend was exhausted
    if len(closes_1m) >= 60:
        recent_high = max(closes_1m[-60:])
        if recent_high > 0:
            decline_from_high_pct = (recent_high - closes_1m[-1]) / recent_high * 100
            if decline_from_high_pct > SLOW_GRIND_SHORT_MAX_DECLINE_FROM_HIGH_PCT:
                return None  # price already declined too much — don't short the bottom

    # ── Confidence Scoring ─────────────────────────────────────────────
    conf = SLOW_GRIND_SHORT_CONF_BASE
    
    # Bonus: strong R² (clean trend)
    r2_bonus = min((r2 - SLOW_GRIND_SHORT_MIN_R2) / (1.0 - SLOW_GRIND_SHORT_MIN_R2) * SLOW_GRIND_SHORT_R2_BONUS_MAX, SLOW_GRIND_SHORT_R2_BONUS_MAX)
    conf += r2_bonus
    
    # Bonus: strong slope (meaningful decline)
    slope_bonus = min(abs(slope_pct) / SLOW_GRIND_SHORT_SLOPE_NORM * 5, SLOW_GRIND_SHORT_SLOPE_BONUS_MAX)
    conf += slope_bonus
    
    # Bonus: good EMA separation (clear bearish alignment)
    ema_bonus = min(ema_sep_20 / SLOW_GRIND_SHORT_EMA_NORM * 5, SLOW_GRIND_SHORT_EMA_BONUS_MAX)
    conf += ema_bonus
    
    # Bonus: low ATR (pure grind)
    if atr_pct < SLOW_GRIND_SHORT_ATR_LOW_THRESHOLD:
        conf += SLOW_GRIND_SHORT_ATR_LOW_BONUS
    
    # Penalty: RSI getting oversold (near bounce zone)
    if rsi < SLOW_GRIND_SHORT_RSI_OVERSOLD_PENALTY_THRESHOLD:
        conf -= SLOW_GRIND_SHORT_RSI_OVERSOLD_PENALTY
    
    conf = max(50, min(conf, SLOW_GRIND_SHORT_CONF_CAP))
    
    return {
        'direction': 'SHORT',
        'confidence': int(conf),
        'value': float(conf),
        'price': closes_1m[-1],
        'r2': round(r2, 4),
        'slope_pct': round(slope_pct * 100, 4),
        'atr_pct': round(atr_pct, 4),
        'rsi': round(rsi, 2),
        'ema_sep_20': round(ema_sep_20, 4),
        'source': SOURCE,
        'signal_type': SIGNAL_TYPE,
    }


# ── Scanner ──────────────────────────────────────────────────────────────

def scan_signals():
    """Scan all tokens for slow_grind_short signals."""
    if not SLOW_GRIND_SHORT_ENABLED:
        return 0
    
    added = 0
    
    # Get token universe from candles.db
    conn = None
    try:
        conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT token FROM candles_1m
            WHERE ts > strftime('%s', 'now') - 3600
        """)
        tokens = [r[0] for r in cur.fetchall()]
    except Exception:
        return 0
    finally:
        if conn:
            conn.close()
    
    for token in tokens:
        if token.startswith('@'):
            continue
        
        # Staleness check
        if price_age_minutes(token) > 10:
            continue
        
        # Blacklist check
        if token.upper() in SHORT_BLACKLIST:
            continue
        
        # Cooldown check
        if get_cooldown(token, direction='SHORT'):
            continue
        
        # Detect signal
        sig = detect_slow_grind_short(token)
        if sig is None:
            continue
        
        # Add signal
        sid = add_signal(
            token=token.upper(),
            direction='SHORT',
            signal_type=SIGNAL_TYPE,
            source=SOURCE,
            confidence=sig['confidence'],
            value=sig['value'],
            price=sig['price'],
            exchange='hyperliquid',
            timeframe='1m',
            z_score=None,
            z_score_tier=None,
        )
        
        if sid:
            added += 1
            set_cooldown(token, direction='SHORT', hours=SLOW_GRIND_SHORT_COOLDOWN_HOURS)
            print(f'  SHORT {token:8s} conf={sig["confidence"]:.0f}% '
                  f'r2={sig["r2"]:.3f} slope={sig["slope_pct"]:.4f}% '
                  f'atr={sig["atr_pct"]:.3f}% rsi={sig["rsi"]:.1f} '
                  f'ema_sep={sig["ema_sep_20"]:.3f}% '
                  f'price={sig["price"]:.6f} [{sig["source"]}]')
    
    return added


# ── Entry Point ──────────────────────────────────────────────────────────

def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import get_all_latest_prices, init_db
    init_db()
    print("[slow_grind_short] Scanning for slow grind SHORT signals...")
    n = scan_signals()
    print(f"[slow_grind_short] Done. {n} signals emitted.")
