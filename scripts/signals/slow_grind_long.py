#!/usr/bin/env python3
"""
slow_grind_long — Catch slow, grinding uptrends with low volatility.

Thesis: Steady uptrends with consistent higher lows, price above EMAs,
        and low volatility are reliable LONG opportunities.
        These "slow grinds" have:
        - Consistent higher highs / higher lows
        - Low ATR (small daily ranges)
        - Price above key EMAs (EMA20, EMA50)
        - Positive but not extreme momentum (RSI 45-65)
        - High R² (clean trend, not choppy)

Pattern (mirrored from slow_grind_short + POL/backtest insights):
  1. R² >= 0.55 (confirmed uptrend, not chop)
  2. Slope > +0.0002 (meaningful uptrend)
  3. Price above EMA50 (bullish alignment)
  4. ATR% < 1.0% (low volatility = grinding)
  5. RSI between 45-65 (not overbought, room to grind higher)
  6. Higher lows confirmation (grinding up, not spiking)

Entry: Ride the slow grind up
Exit:  Trail stop or profit target 2-4%

Data: candles_1m and candles_5m from candles.db
"""

import sys, os, sqlite3, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    SLOW_GRIND_LONG_ENABLED,
    SLOW_GRIND_LONG_MIN_R2,
    SLOW_GRIND_LONG_MIN_SLOPE_PCT,
    SLOW_GRIND_LONG_MAX_ATR_PCT,
    SLOW_GRIND_LONG_RSI_MIN,
    SLOW_GRIND_LONG_RSI_MAX,
    SLOW_GRIND_LONG_MIN_EMA_SEPARATION,
    SLOW_GRIND_LONG_CONF_BASE,
    SLOW_GRIND_LONG_CONF_CAP,
    SLOW_GRIND_LONG_COOLDOWN_HOURS,
    SLOW_GRIND_LONG_R2_WINDOW,
    LONG_BLACKLIST,
)

# ── Signal Identity ──────────────────────────────────────────────────────
SIGNAL_TYPE = 'slow_grind_long'
SOURCE      = 'slow-grind+'

# ── Lookback Windows ─────────────────────────────────────────────────────
CANDLES_1M_LOOKBACK = 120   # 2 hours of 1m data
CANDLES_5M_LOOKBACK = 60    # 5 hours of 5m data
R2_WINDOW = SLOW_GRIND_LONG_R2_WINDOW  # bars for R² regression

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
    ema = sum(prices[:period]) / period
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
    trs = [abs(closes[i] - closes[i-1]) for i in range(1, len(closes))]
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    atr_pct = (atr / closes[-1] * 100) if closes[-1] > 0 else 0
    return atr_pct


# ── Detection Logic ──────────────────────────────────────────────────────

def detect_slow_grind_long(token):
    """
    Detect slow grinding uptrend on 1m candles.
    Returns signal dict or None.
    """
    if not SLOW_GRIND_LONG_ENABLED:
        return None

    # ── BTC Trend Filter (critical: 59% win rate when BTC UP, 9% when DOWN) ──
    try:
        btc_conn = sqlite3.connect(_CANDLES_DB, timeout=10)
        btc_cur = btc_conn.cursor()
        btc_cur.execute('SELECT close FROM candles_1h WHERE token=\"BTC\" ORDER BY ts DESC LIMIT 4')
        btc_rows = btc_cur.fetchall()
        btc_conn.close()
        if len(btc_rows) >= 4:
            btc_closes = [r[0] for r in reversed(btc_rows)]
            btc_4h_ago = btc_closes[-4]
            btc_now = btc_closes[-1]
            btc_trend_pct = (btc_now - btc_4h_ago) / btc_4h_ago * 100
            if btc_trend_pct < -0.1:
                return None  # BTC trending down — too risky for LONG
    except Exception:
        pass  # fail-open: don't block on DB error

    # Fetch 1m candles
    closes_1m = _get_closes(token, 'candles_1m', CANDLES_1M_LOOKBACK)
    if len(closes_1m) < R2_WINDOW * 2:
        return None

    # ── R² Regression (trend quality) ──────────────────────────────────
    y = closes_1m[-R2_WINDOW:]
    slope, intercept, r2 = _ols_params(y)

    slope_pct = slope / closes_1m[-1] if closes_1m[-1] > 0 else 0

    # Filter: need confirmed uptrend
    if r2 < SLOW_GRIND_LONG_MIN_R2:
        return None
    if slope_pct <= SLOW_GRIND_LONG_MIN_SLOPE_PCT:
        return None  # not rising fast enough

    # Price should be near or above regression line (not too far below)
    # Allow up to 0.5% below — pullback to trend line is a good entry
    regression_at_current = slope * (R2_WINDOW - 1) + intercept
    if regression_at_current > 0:
        below_pct = (regression_at_current - closes_1m[-1]) / regression_at_current * 100
        if below_pct > 0.5:
            return None  # too far below trend — trend may be breaking

    # ── EMA Check (bullish alignment) ──────────────────────────────────
    if len(closes_1m) < 50:
        return None

    ema20 = _compute_ema(closes_1m, 20)
    ema50 = _compute_ema(closes_1m, 50)

    if ema20 is None or ema50 is None:
        return None

    # Price must be above EMA50
    if closes_1m[-1] < ema50:
        return None

    ema_sep_50 = (closes_1m[-1] - ema50) / closes_1m[-1] * 100
    if ema_sep_50 < SLOW_GRIND_LONG_MIN_EMA_SEPARATION:
        return None

    # ── ATR Check (low volatility = grinding) ──────────────────────────
    closes_5m = _get_closes(token, 'candles_5m', CANDLES_5M_LOOKBACK)
    if len(closes_5m) < 15:
        return None

    atr_pct = _compute_atr(closes_5m, period=14)
    if atr_pct is None:
        return None

    if atr_pct > SLOW_GRIND_LONG_MAX_ATR_PCT:
        return None  # too volatile

    # ── RSI Check (not overbought) ─────────────────────────────────────
    rsi = _compute_rsi(closes_1m, period=14)
    if rsi is None:
        rsi = 50.0

    if rsi < SLOW_GRIND_LONG_RSI_MIN or rsi > SLOW_GRIND_LONG_RSI_MAX:
        return None

    # ── Higher Lows Confirmation ───────────────────────────────────────
    if len(closes_1m) >= 30:
        window1 = closes_1m[-30:-15]
        window2 = closes_1m[-15:]
        avg1 = sum(window1) / len(window1)
        avg2 = sum(window2) / len(window2)
        if avg2 <= avg1:
            return None  # not grinding up

    # ── Pre-Entry Move Filter ──────────────────────────────────────────
    # Block if price already rose too much from recent low (chasing)
    if len(closes_1m) >= 10:
        recent_low = min(closes_1m[-10:])
        if recent_low > 0:
            pre_entry_move_pct = (closes_1m[-1] - recent_low) / recent_low * 100
            if pre_entry_move_pct > 1.5:
                return None  # already up too much

    # ── Velocity Filter ────────────────────────────────────────────────
    # Allow small pullbacks (up to -0.5%) — enter during dips, not at top
    if len(closes_1m) >= 6:
        vel_5m = (closes_1m[-1] - closes_1m[-6]) / closes_1m[-6] * 100
        if vel_5m < -0.5:
            return None  # price declining too fast — trend may be breaking

    # ── Rise From Low Filter ───────────────────────────────────────────
    # Block if price has already risen too much from recent low (chasing tops)
    # Raised to 5% to allow strong trends (DASH was blocked at 5.0%)
    if len(closes_1m) >= 60:
        recent_low = min(closes_1m[-60:])
        if recent_low > 0:
            rise_from_low_pct = (closes_1m[-1] - recent_low) / recent_low * 100
            if rise_from_low_pct > 5.0:
                return None  # already up too much

    # ── Confidence Scoring ─────────────────────────────────────────────
    conf = SLOW_GRIND_LONG_CONF_BASE

    # Bonus: strong R²
    r2_bonus = min((r2 - SLOW_GRIND_LONG_MIN_R2) / (1.0 - SLOW_GRIND_LONG_MIN_R2) * 15, 15)
    conf += r2_bonus

    # Bonus: strong slope
    slope_bonus = min(slope_pct / 0.001 * 5, 10)
    conf += slope_bonus

    # Bonus: good EMA separation
    ema_bonus = min(ema_sep_50 / 0.5 * 5, 10)
    conf += ema_bonus

    # Bonus: low ATR (pure grind)
    if atr_pct < 0.5:
        conf += 3

    # Penalty: RSI getting overbought
    if rsi > 60:
        conf -= 5

    conf = max(60, min(conf, SLOW_GRIND_LONG_CONF_CAP))

    return {
        'direction': 'LONG',
        'confidence': int(conf),
        'value': float(conf),
        'price': closes_1m[-1],
        'r2': round(r2, 4),
        'slope_pct': round(slope_pct * 100, 4),
        'atr_pct': round(atr_pct, 4),
        'rsi': round(rsi, 2),
        'ema_sep_50': round(ema_sep_50, 4),
        'source': SOURCE,
        'signal_type': SIGNAL_TYPE,
    }


# ── Scanner ──────────────────────────────────────────────────────────────

def scan_signals():
    """Scan all tokens for slow_grind_long signals."""
    added = 0

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
        if price_age_minutes(token) > 10:
            continue
        if token.upper() in LONG_BLACKLIST:
            continue
        if get_cooldown(token, direction='LONG'):
            continue

        sig = detect_slow_grind_long(token)
        if sig is None:
            continue

        sid = add_signal(
            token=token.upper(),
            direction='LONG',
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
            set_cooldown(token, direction='LONG', hours=SLOW_GRIND_LONG_COOLDOWN_HOURS)
            print(f'  LONG  {token:8s} conf={sig["confidence"]:.0f}% '
                  f'r2={sig["r2"]:.3f} slope={sig["slope_pct"]:.4f}% '
                  f'atr={sig["atr_pct"]:.3f}% rsi={sig["rsi"]:.1f} '
                  f'ema_sep={sig["ema_sep_50"]:.3f}% '
                  f'price={sig["price"]:.6f} [{sig["source"]}]')

    return added


def run(prices_dict=None):
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    from signal_schema import init_db
    init_db()
    print("[slow_grind_long] Scanning for slow grind LONG signals...")
    n = scan_signals()
    print(f"[slow_grind_long] Done. {n} signals emitted.")
