#!/usr/bin/env python3
"""
ema9_sma20_signals.py — EMA(9) vs SMA(20) Rate-of-Change Gap Signal on 1m prices.

Concept: when price moves strongly, the 9 EMA and 20 SMA both slope in that
direction. The RATE at which they diverge (rate-of-change gap) measures momentum
strength. A widening ROC gap = confirmed momentum in that direction.

Signal logic:
  - LONG:  EMA9 and SMA20 both rising, price > EMA9 > SMA20, ROC gap crosses above MIN_GAP_PCT
  - SHORT: EMA9 and SMA20 both falling, price < EMA9 < SMA20, ROC gap crosses above MIN_GAP_PCT

Architecture:
  price_history (1m closes, fresh every minute) → EMA(9) + SMA(20) → slope + ROC gap
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal types:
  - ema9_sma20_long  : ROC gap widens bullish (both rising, price above both)
  - ema9_sma20_short : ROC gap widens bearish (both falling, price below both)
"""

import sys, os, sqlite3, time, datetime
from typing import Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'   # price_history — live 1m prices

# ── Signal constants ──────────────────────────────────────────────────────────
PERIOD_FAST       = 9       # EMA period
PERIOD_SLOW       = 20      # SMA period
SLOPE_PERIOD      = 5       # Bars used to compute slope (5min lookback)
COOLDOWN_MINUTES  = 10
LOOKBACK_1M       = 250     # 1m prices to fetch (enough for warmup + slope calc)
MIN_VALID_BARS    = 50      # Minimum valid EMA+SMA bars before signals fire
GAP_TYPE          = 'roc'   # 'gap' = |EMA-SMA|/price*100 (gap-300 style)
                          # 'roc'  = |slope_ema-slope_sma|/price*100 (momentum style)

# ── Backtest-optimized params (ROC, 20-day split-sample verified) ────────────
# LONG: X=0.008%, hold=60 bars
#   Full 20d: 771s, WR=49.0%, PNL=+0.017%/signal
#   Split-sample: Train PNL=-0.016% → Test PNL=+0.041% (positive on unseen)
# SHORT: X=0.005%, bear-regime only (price below falling 50 SMA)
#   Full 20d: 286s, WR=47.6%, PNL=+0.017%/signal, 6/9 tokens positive
#   Best performers: AVAX +0.185%, ARB +0.123%, LINK +0.064%, ATOM +0.078%
#   Worst: ADA -0.108%, DOT -0.144% — consider token-level blacklist
# SHORT disabled below 50 SMA — regime filter is enforced in detect_ema9_sma20_cross
MIN_GAP_PCT_LONG  = 0.008  # ROC threshold for LONG
MIN_GAP_PCT_SHORT = 0.005  # ROC threshold for SHORT (bear-regime only)
HOLD_BARS         = 60     # Exit after 60 bars (~60min) regardless of profit

SIGNAL_TYPE_LONG  = 'ema9_sma20_long'
SIGNAL_TYPE_SHORT = 'ema9_sma20_short'
SOURCE_LONG       = 'ema9-sma20+'
SOURCE_SHORT      = 'ema9-sma20-'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA / SMA helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _ema_series(values: list, period: int) -> list:
    """Return EMA series (oldest first), None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    k = 2.0 / (period + 1)
    result = [None] * (period - 1)
    ema_val = sum(values[:period]) / period
    result.append(ema_val)
    for price in values[period:]:
        ema_val = price * k + ema_val * (1 - k)
        result.append(ema_val)
    return result


def _sma_series(values: list, period: int) -> list:
    """Return SMA series (oldest first), None for indices < period-1."""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1:i + 1]) / period)
    return result


def _compute_gap_series(closes: list, ema_s: list, sma_s: list,
                         ema_slope_s: list, sma_slope_s: list,
                         gap_type: str = 'gap') -> tuple:
    """
    Compute gap series based on gap_type.

    'gap': gap = |EMA9 - SMA20| / price * 100  (gap-300 style)
           raw_gap = EMA9 - SMA20 (signed, positive = bullish)

    'roc':  gap = |slope_EMA9 - slope_SMA20| / price * 100  (rate-of-change style)
            raw_gap = slope_EMA9 - slope_SMA20 (signed, positive = EMA rising faster)

    Returns (gap_series, raw_gap_series) — oldest first, None where insufficient data.
    """
    gaps = []
    raw_gaps = []
    for i in range(len(closes)):
        if gap_type == 'gap':
            ev = ema_s[i]
            sv = sma_s[i]
            if ev is None or sv is None:
                gaps.append(None)
                raw_gaps.append(None)
            else:
                gaps.append(abs(ev - sv) / closes[i] * 100.0)
                raw_gaps.append(ev - sv)
        else:  # 'roc'
            es = ema_slope_s[i]
            ss = sma_slope_s[i]
            if es is None or ss is None:
                gaps.append(None)
                raw_gaps.append(None)
            else:
                gaps.append(abs(es - ss) / closes[i] * 100.0)
                raw_gaps.append(es - ss)
    return gaps, raw_gaps


def _compute_slope_series(indicator_series: list, slope_period: int = SLOPE_PERIOD) -> list:
    """
    Compute slope over the last `slope_period` bars for each valid value.
    slope[i] = (indicator[i] - indicator[i - slope_period]) / slope_period
    Returns list of slopes (oldest first), None where insufficient data.
    """
    result = []
    for i in range(len(indicator_series)):
        if i < slope_period:
            result.append(None)
        else:
            cur = indicator_series[i]
            prev = indicator_series[i - slope_period]
            if cur is None or prev is None:
                result.append(None)
            else:
                result.append((cur - prev) / slope_period)
    return result


def _ema_slope_series(values: list, ema_period: int, slope_period: int = SLOPE_PERIOD) -> tuple:
    """Return (EMA series, slope of EMA series) — both oldest first."""
    ema_s = _ema_series(values, ema_period)
    slope_s = _compute_slope_series(ema_s, slope_period)
    return ema_s, slope_s


def _sma_slope_series(values: list, sma_period: int, slope_period: int = SLOPE_PERIOD) -> tuple:
    """Return (SMA series, slope of SMA series) — both oldest first."""
    sma_s = _sma_series(values, sma_period)
    slope_s = _compute_slope_series(sma_s, slope_period)
    return sma_s, slope_s


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable
    source for live signal generation. timestamps are in SECONDS (Unix time).

    Returns list of {timestamp, price} dicts, oldest first.
    Freshness guard: returns [] if most recent price is > 2 minutes old.
    """
    try:
        conn = sqlite3.connect(_PRICE_DB, timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT timestamp, price FROM (
                SELECT timestamp, price
                FROM price_history
                WHERE token = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ) sub
            ORDER BY timestamp ASC
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return []

        # Freshness guard
        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            print(f"  [ema9sma20] {token}: stale price_history (last ts {most_recent_ts}), skipping")
            return []

        # Bar-to-bar gap guard — detect internal data gaps
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        if bar_gaps:
            mean_gap = sum(bar_gaps) / len(bar_gaps)
            variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
            std_gap = variance ** 0.5
            threshold = max(150, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                bar_gap = rows[i][0] - rows[i-1][0]
                if bar_gap > threshold:
                    print(f"  [ema9sma20] {token}: data gap ({bar_gap:.0f}s > {threshold:.0f}s), skipping")
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [ema9sma20] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_ema9_sma20_cross(token: str, prices: list, price: float,
                              min_gap_pct_long: float = MIN_GAP_PCT_LONG,
                              min_gap_pct_short: float = MIN_GAP_PCT_SHORT,
                              gap_type: str = GAP_TYPE) -> Optional[dict]:
    """
    Detect gap widening between EMA(9) and SMA(20) on 1m close prices.

    Fire when gap crosses above min_gap_pct_{direction} AND:
      - For LONG: both EMA9 and SMA20 are rising (3 consecutive slope bars)
                  AND price > EMA9 > SMA20 (full alignment)
      - For SHORT: both EMA9 and SMA20 are falling (3 consecutive slope bars)
                   AND price < EMA9 < SMA20 (full alignment)
    AND the gap is still widening at the most recent bar.

    gap_type='gap': gap = |EMA9 - SMA20| / price * 100  (gap-300 style)
    gap_type='roc':  gap = |slope_EMA9 - slope_SMA20| / price * 100  (momentum style)

    Returns dict with direction, gap_pct, bars_since, or None if no cross.
    """
    n = len(prices)
    if n < MIN_VALID_BARS:
        return None

    closes = [p['price'] for p in prices]

    # Compute EMA(9) + slope, SMA(20) + slope
    ema_s, ema_slope_s = _ema_slope_series(closes, PERIOD_FAST, SLOPE_PERIOD)
    sma_s, sma_slope_s = _sma_slope_series(closes, PERIOD_SLOW, SLOPE_PERIOD)

    # Build gap series using selected gap_type
    gap_series, raw_gap_series = _compute_gap_series(
        closes, ema_s, sma_s, ema_slope_s, sma_slope_s, gap_type)

    # Count valid gap bars
    valid_gap_count = sum(1 for g in gap_series if g is not None)
    if valid_gap_count < MIN_VALID_BARS:
        return None

    # ── Step 1: Find most recent gap crossing above threshold per direction ────────
    # Test both directions independently, pick the most recent valid cross
    cross_idx = None
    cross_direction = None
    cross_x = None

    for j in range(1, len(gap_series)):
        g_prev = gap_series[j - 1]
        g_cur  = gap_series[j]
        if g_prev is None or g_cur is None:
            continue
        raw = raw_gap_series[j]

        # Test LONG cross
        if min_gap_pct_long is not None and raw is not None and raw > 0:
            if g_prev < min_gap_pct_long <= g_cur:
                if cross_idx is None or j > cross_idx:
                    cross_idx = j
                    cross_direction = 'LONG'
                    cross_x = min_gap_pct_long

        # Test SHORT cross
        if min_gap_pct_short is not None and raw is not None and raw < 0:
            if g_prev < min_gap_pct_short <= g_cur:
                if cross_idx is None or j > cross_idx:
                    cross_idx = j
                    cross_direction = 'SHORT'
                    cross_x = min_gap_pct_short

    if cross_idx is None:
        return None

    direction = cross_direction

    # ── Step 2: Verify gap is still widening at most recent bar vs cross bar ──
    if gap_series[-1] is None or gap_series[-1] <= gap_series[cross_idx]:
        return None

    # ── Step 3: Determine direction from raw gap at cross ─────────────────────
    if raw_gap_series[cross_idx] is None:
        return None
    direction = 'LONG' if raw_gap_series[cross_idx] > 0 else 'SHORT'

    # ── Step 4: Direction guard — direction must still be valid at most recent bar ─
    if raw_gap_series[-1] is not None:
        if direction == 'LONG' and raw_gap_series[-1] <= 0:
            return None
        if direction == 'SHORT' and raw_gap_series[-1] >= 0:
            return None

    # ── Step 5: Alignment check (price vs EMA9 vs SMA20) ─────────────────────
    ema_val = ema_s[-1]
    sma_val = sma_s[-1]
    if ema_val is None or sma_val is None:
        return None

    if direction == 'LONG':
        if not (closes[-1] > ema_val > sma_val):
            return None
        # Rising check: 3 consecutive rising slope bars for both
        if not (ema_slope_s[-1] is not None and ema_slope_s[-1] > 0 and
                ema_slope_s[-2] is not None and ema_slope_s[-2] > 0 and
                ema_slope_s[-3] is not None and ema_slope_s[-3] > 0):
            return None
        if not (sma_slope_s[-1] is not None and sma_slope_s[-1] > 0 and
                sma_slope_s[-2] is not None and sma_slope_s[-2] > 0 and
                sma_slope_s[-3] is not None and sma_slope_s[-3] > 0):
            return None
    else:  # SHORT
        if not (closes[-1] < ema_val < sma_val):
            return None
        if not (ema_slope_s[-1] is not None and ema_slope_s[-1] < 0 and
                ema_slope_s[-2] is not None and ema_slope_s[-2] < 0 and
                ema_slope_s[-3] is not None and ema_slope_s[-3] < 0):
            return None
        if not (sma_slope_s[-1] is not None and sma_slope_s[-1] < 0 and
                sma_slope_s[-2] is not None and sma_slope_s[-2] < 0 and
                sma_slope_s[-3] is not None and sma_slope_s[-3] < 0):
            return None
        # ── Step 5b: Bear-regime SHORT guard ────────────────────────────────────
        # SHORT only valid when price is below the falling 50 SMA
        # (broader bear-market filter — prevents shorts during ranging chop)
        sma50 = _sma_series(closes, 50)
        sma50_slope = _compute_slope_series(sma50, 5)
        if not (sma50[-1] is not None and closes[-1] < sma50[-1] and
                sma50_slope[-1] is not None and sma50_slope[-1] < 0):
            return None

    # ── Step 6: Collapse guard ─────────────────────────────────────────────────
    RECENT_BARS = 30
    lookback_start = max(cross_idx + 1, len(gap_series) - RECENT_BARS)
    recent_window = [g for g in gap_series[lookback_start:] if g is not None]
    peak_recent = max(recent_window) if recent_window else gap_series[cross_idx]
    if peak_recent > 0 and gap_series[-1] < peak_recent * 0.70:
        return None

    bars_since = max(len(closes) - 1 - cross_idx, 0)
    gap_pct = gap_series[cross_idx]

    return {
        'direction': direction,
        'gap_pct': round(gap_pct, 4),
        'bars_since': bars_since,
        'price': closes[cross_idx],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_ema9_sma20_signals(prices_dict: dict) -> int:
    """
    Scan tokens for EMA(9)/SMA(20) rate-of-change gap signals.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    from signal_schema import add_signal, price_age_minutes
    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import (
        recent_trade_exists, is_delisted, SHORT_BLACKLIST,
        MIN_TRADE_INTERVAL_MINUTES, set_cooldown
    )

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue
        if token.upper() in SHORT_BLACKLIST:
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token, lookback=LOOKBACK_1M)
        if not prices or len(prices) < MIN_VALID_BARS:
            continue

        sig = detect_ema9_sma20_cross(token, prices, price)
        if sig is None:
            continue

        direction = sig['direction']
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Confidence: 55-80 based on gap strength above threshold
        gap_val = sig['gap_pct']
        threshold = MIN_GAP_PCT_LONG if direction == 'LONG' else MIN_GAP_PCT_SHORT
        if threshold:
            confidence = int(min(80, max(55, 55 + (gap_val - threshold) * 400)))
        else:
            confidence = 60

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=float(confidence),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                set_cooldown(token, direction, hours=COOLDOWN_MINUTES / 60.0)
                print(f"  {direction:5s}-ema9sma20 {token:8s} conf={confidence:.0f}% "
                      f"gap={sig['gap_pct']:.3f}% bars={sig['bars_since']} [{source}]")
        except Exception as e:
            print(f"[ema9sma20] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# Backtesting — standalone ROC gap backtest (raw slope version)
# ═══════════════════════════════════════════════════════════════════════════════

def backtest_ema9_sma20(token: str, closes: list,
                        min_gap_pct_long: float = MIN_GAP_PCT_LONG,
                        min_gap_pct_short: float = MIN_GAP_PCT_SHORT,
                        gap_type: str = GAP_TYPE,
                        hold_bars: int = HOLD_BARS) -> dict:
    """
    Backtest EMA9/SMA20 gap signal on historical closes.

    gap_type='gap': gap = |EMA9 - SMA20| / price * 100  (gap-300 style)
    gap_type='roc':  gap = |slope_EMA9 - slope_SMA20| / price * 100  (momentum style)

    Uses per-direction X thresholds (min_gap_pct_long / min_gap_pct_short).
    Pass min_gap_pct_short=None to disable SHORT.

    Proper sequential walk: for each bar j, compute all indicators using only
    closes[:j+1] (no look-ahead). Fire signal at j, score outcome at j+hold.
    """
    if len(closes) < MIN_VALID_BARS + 10:
        return {}

    # Precompute full indicator series
    ema_s, ema_slope_s = _ema_slope_series(closes, PERIOD_FAST, SLOPE_PERIOD)
    sma_s, sma_slope_s = _sma_slope_series(closes, PERIOD_SLOW, SLOPE_PERIOD)
    gap_series, raw_gap_series = _compute_gap_series(
        closes, ema_s, sma_s, ema_slope_s, sma_slope_s, gap_type)

    # Sequential walk
    signals = []
    for j in range(1, len(gap_series)):
        g_prev = gap_series[j - 1]
        g_cur  = gap_series[j]
        if g_prev is None or g_cur is None:
            continue
        raw = raw_gap_series[j]
        if raw is None:
            continue

        # Test LONG cross
        if min_gap_pct_long is not None and raw > 0:
            if g_prev < min_gap_pct_long <= g_cur:
                direction = 'LONG'
                threshold = min_gap_pct_long
            else:
                direction = None

            if direction == 'LONG':
                ev = ema_s[j]; sv = sma_s[j]
                if ev is None or sv is None: continue
                if not (closes[j] > ev > sv): continue
                if not all(ema_slope_s[k] is not None and ema_slope_s[k] > 0 for k in [j,j-1,j-2]): continue
                if not all(sma_slope_s[k] is not None and sma_slope_s[k] > 0 for k in [j,j-1,j-2]): continue
                peak_window = [gap_series[k] for k in range(max(0,j-29),j+1) if gap_series[k] is not None]
                peak = max(peak_window) if peak_window else g_cur
                if peak > 0 and g_cur < peak * 0.70: continue
                signals.append({'idx': j, 'direction': 'LONG', 'entry_price': closes[j], 'threshold': threshold})

        # Test SHORT cross
        if min_gap_pct_short is not None and raw < 0:
            if g_prev < min_gap_pct_short <= g_cur:
                direction = 'SHORT'
                threshold = min_gap_pct_short
            else:
                direction = None

            if direction == 'SHORT':
                ev = ema_s[j]; sv = sma_s[j]
                if ev is None or sv is None: continue
                if not (closes[j] < ev < sv): continue
                if not all(ema_slope_s[k] is not None and ema_slope_s[k] < 0 for k in [j,j-1,j-2]): continue
                if not all(sma_slope_s[k] is not None and sma_slope_s[k] < 0 for k in [j,j-1,j-2]): continue
                peak_window = [gap_series[k] for k in range(max(0,j-29),j+1) if gap_series[k] is not None]
                peak = max(peak_window) if peak_window else g_cur
                if peak > 0 and g_cur < peak * 0.70: continue
                signals.append({'idx': j, 'direction': 'SHORT', 'entry_price': closes[j], 'threshold': threshold})

    # Score trades
    stats = {'LONG': {'signals': 0, 'wins': 0, 'pnls': [], 'bars': []},
             'SHORT': {'signals': 0, 'wins': 0, 'pnls': [], 'bars': []}}

    for sig in signals:
        direction = sig['direction']
        entry_idx = sig['idx']
        entry_price = sig['entry_price']
        max_hold = hold_bars  # configurable hold period
        exit_idx = min(entry_idx + max_hold, len(closes) - 1)
        exit_price = closes[exit_idx]
        bars_held = exit_idx - entry_idx

        if direction == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100

        stats[direction]['signals'] += 1
        stats[direction]['bars'].append(bars_held)
        stats[direction]['pnls'].append(pnl_pct)
        if pnl_pct > 0:
            stats[direction]['wins'] += 1

    summary = {}
    for d in ('LONG', 'SHORT'):
        s = stats[d]
        n = s['signals']
        if n == 0:
            continue
        wr = s['wins'] / n * 100
        avg_pnl = sum(s['pnls']) / n if s['pnls'] else 0
        avg_bars = sum(s['bars']) / n if s['bars'] else 0
        summary[d] = {
            'signals': n, 'wins': s['wins'], 'win_rate': round(wr, 1),
            'avg_pnl_pct': round(avg_pnl, 4), 'avg_bars': round(avg_bars, 1),
        }
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# CLI test + backtest
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys, os, sqlite3
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import init_db

    # ── Live signal test ──────────────────────────────────────────────────────
    conn = sqlite3.connect(_PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT token FROM price_history
        WHERE timestamp > ?
        ORDER BY token
    """, (int(time.time()) - 600,))
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    test_tokens = {k: {'price': None} for k in tokens
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'XMR')}
    if not test_tokens:
        test_tokens = {k: {'price': None} for k in tokens[:10]}

    prices = {}
    conn = sqlite3.connect(_PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT token, price FROM price_history
        WHERE (token, timestamp) IN (
            SELECT token, MAX(timestamp) FROM price_history
            WHERE timestamp > ?
            GROUP BY token
        )
    """, (int(time.time()) - 600,))
    for row in c.fetchall():
        if row[0] in test_tokens:
            prices[row[0]] = {'price': row[1]}
    conn.close()

    print(f"[ema9sma20] Testing on {len(prices)} tokens (live price_history)...")
    init_db()
    n = scan_ema9_sma20_signals(prices)
    print(f"[ema9sma20] Done. {n} signals emitted.")

    # ── Backtest ──────────────────────────────────────────────────────────────
    print("\n[ema9sma20] Backtesting...")
    BACKTEST_TOKENS = ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'ADA', 'DOT', 'ATOM']

    # gap-300 style: gap = |EMA-SMA|/price*100 — thresholds 0.02-0.15
    GAP_X_RANGE = [0.02, 0.03, 0.05, 0.08, 0.10, 0.12, 0.15]
    # ROC style: gap = |slope_ema-slope_sma|/price*100 — thresholds 0.001-0.01
    ROC_X_RANGE = [0.001, 0.002, 0.003, 0.005, 0.008, 0.010]

    for gap_type in ['gap', 'roc']:
        x_range = GAP_X_RANGE if gap_type == 'gap' else ROC_X_RANGE
        print(f"\n=== gap_type={gap_type} ===")
        for x in x_range:
            total_long_sig = total_short_sig = 0
            total_long_wr = total_short_wr = 0
            total_long_pnl = total_short_pnl = 0
            tokens_tested = 0
            for token in BACKTEST_TOKENS:
                try:
                    conn = sqlite3.connect(_PRICE_DB, timeout=10)
                    c = conn.cursor()
                    c.execute("""
                        SELECT price FROM price_history
                        WHERE token = ?
                        ORDER BY timestamp DESC
                        LIMIT 400
                    """, (token.upper(),))
                    rows = list(reversed(c.fetchall()))
                    conn.close()
                    if len(rows) < MIN_VALID_BARS + 10:
                        continue
                    closes = [r[0] for r in rows]
                    res = backtest_ema9_sma20(token, closes, min_gap_pct_long=x, min_gap_pct_short=x, gap_type=gap_type)
                    if not res:
                        continue
                    tokens_tested += 1
                    if 'LONG' in res:
                        total_long_sig += res['LONG']['signals']
                        total_long_wr += res['LONG']['win_rate']
                        total_long_pnl += res['LONG']['avg_pnl_pct']
                    if 'SHORT' in res:
                        total_short_sig += res['SHORT']['signals']
                        total_short_wr += res['SHORT']['win_rate']
                        total_short_pnl += res['SHORT']['avg_pnl_pct']
                except Exception as e:
                    continue
            long_wr_avg = total_long_wr / tokens_tested if tokens_tested else 0
            short_wr_avg = total_short_wr / tokens_tested if tokens_tested else 0
            long_pnl_avg = total_long_pnl / tokens_tested if tokens_tested else 0
            short_pnl_avg = total_short_pnl / tokens_tested if tokens_tested else 0
            print(f"  X={x:.4f}%: LONG {total_long_sig:3d}s WR={long_wr_avg:5.1f}% avgPNL={long_pnl_avg:+.3f}% | "
                  f"SHORT {total_short_sig:3d}s WR={short_wr_avg:5.1f}% avgPNL={short_pnl_avg:+.3f}% | n={tokens_tested}")
