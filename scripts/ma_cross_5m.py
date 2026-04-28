#!/usr/bin/env python3
"""
ma_cross_5m.py — Per-token tuned EMA(10)×EMA(200) Crossover on 5m candles.

5m candles are aggregated on-the-fly from 1m candles in price_history.
Per-token tuned fast/slow periods for both LONG and SHORT directions.
Daily tuner sweep finds best params; scanner uses them live.

Architecture:
  price_history (1m) → aggregate to 5m → EMA(10) × EMA(200) → crossover signal
  tuner DB (ma_cross_5m_tuner.db) → per-token best params per direction

Signal types:
  - ma_cross_5m_long  : golden cross on 5m (fast EMA crosses above slow EMA)
  - ma_cross_5m_short : death cross on 5m  (fast EMA crosses below slow EMA)

Sources:
  - ma-5m-long
  - ma-5m-short
"""

import sys, os, sqlite3, time, statistics
from typing import Dict, List, Optional

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(os.path.dirname(SCRIPT_DIR), 'data')
sys.path.insert(0, SCRIPT_DIR)
from paths import CANDLES_DB   # price_history.db (candles.db is a symlink/alias)
_RUNTIME_DB = os.path.join(DATA_DIR, 'signals_hermes_runtime.db')
_TUNER_DB   = os.path.join(DATA_DIR, 'ma_cross_5m_tuner.db')

# ── Default params (used until token has >= MIN_SIGNALS_FOR_TUNED signals) ───
# Fast/slow are in CANDLE UNITS (5m candles here).
# Fixed defaults — golden/death cross on 5m:
#   fast=10 (50 min), slow=200 (~16.7 hours)
_DEFAULT_PARAMS = {
    'LONG':  {'fast': 10, 'slow': 200, 'wr': 55.0, 'n': 0},
    'SHORT': {'fast': 10, 'slow': 200, 'wr': 50.0, 'n': 0},
}
MIN_SIGNALS_FOR_TUNED = 15   # tokens with <15 historical signals use defaults

# ── Tuner grid ────────────────────────────────────────────────────────────────
# fast: 5-20 step 1  (5 to 20 candles = 25min to 100min)
# slow: 50-200 step 10 (250min to 1000min = ~4h to ~16.7h)
# Constraint: slow >= 2.5 * fast
FAST_RANGE = list(range(5, 21, 1))   # 5,6,7,...,20
SLOW_RANGE = list(range(50, 210, 10)) # 50,60,70,...,200
MIN_SLOW_FAST_RATIO = 2.5

# ── Signal metadata ───────────────────────────────────────────────────────────
SIGNAL_TYPE_LONG  = 'ma_cross_5m_long'
SIGNAL_TYPE_SHORT = 'ma_cross_5m_short'
SOURCE_LONG  = 'ma-cross-5m+'
SOURCE_SHORT = 'ma-cross-5m-'
LOOKBACK_CANDLES  = 600   # 5m candles to fetch (~2+ days)
COOLDOWN_HOURS    = 1.0
# Minimum EMA separation as % of price — crossovers below this are noise
MIN_SEP_PCT = 0.20   # 0.20% minimum separation required to fire


# ═══════════════════════════════════════════════════════════════════════════
# 5m aggregation from 1m candles
# ═══════════════════════════════════════════════════════════════════════════

def get_5m_candles(token: str, lookback: int = LOOKBACK_CANDLES) -> List[dict]:
    """
    Fetch 5m OHLCV candles from candles_5m table (oldest first).
    Falls back to aggregating from 1m if candles_5m is empty.
    Freshness guard: skip if latest candle older than 2 minutes.
    """
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        # Freshness check — verify data is not stale
        c.execute("SELECT MAX(ts) FROM candles_5m WHERE token = ?", (token.upper(),))
        row = c.fetchone()
        if row and row[0]:
            age_seconds = time.time() - row[0]
            if age_seconds > 120:  # 2 minutes
                print(f"[ma_cross_5m] Stale data for {token}: {age_seconds/60:.1f}m old — skipping")
                conn.close()
                return []
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_5m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback))
        rows = c.fetchall()
        conn.close()
        if rows:
            # Newest-first → oldest-first
            rows = list(reversed(rows))
            return [
                {'open': r[1], 'high': r[2], 'low': r[3],
                 'close': r[4], 'volume': r[5]}
                for r in rows
            ]
    except Exception as e:
        print(f"[ma_cross_5m] candles_5m error for {token}: {e}")

    # Fallback: aggregate from 1m
    return _aggregate_5m_from_1m(token, lookback * 5)


def _aggregate_5m_from_1m(token: str, lookback_1m: int) -> List[dict]:
    """Aggregate 1m candles into 5m OHLCV. Used as fallback when candles_5m is empty."""
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        # Staleness check on candles_1m before using them
        c.execute("SELECT MAX(ts) FROM candles_1m WHERE token = ?", (token.upper(),))
        row = c.fetchone()
        if row and row[0] and (time.time() - row[0]) > 120:
            conn.close()
            return []
        c.execute("""
            SELECT ts, open, high, low, close, volume
            FROM candles_1m
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), lookback_1m))
        rows = c.fetchall()
        conn.close()
        if not rows:
            return []
        rows = list(reversed(rows))
        bars = []
        for i in range(0, len(rows), 5):
            chunk = rows[i:i+5]
            if not chunk:
                continue
            open_, high, low, close, volume = (
                chunk[0][1], max(r[2] for r in chunk), min(r[3] for r in chunk),
                chunk[-1][4], sum(r[5] for r in chunk)
            )
            bars.append({'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume})
        return bars
    except Exception as e:
        print(f"[ma_cross_5m] 1m aggregation error for {token}: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════
# EMA helpers
# ═══════════════════════════════════════════════════════════════════════════

def _ema_series(values: List[float], period: int) -> List[Optional[float]]:
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


def _ema(values: List[float], period: int) -> Optional[float]:
    """Return most recent EMA value only."""
    series = _ema_series(values, period)
    for v in reversed(series):
        if v is not None:
            return v
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Cross detection (agnostic to period — works with any fast/slow)
# ═══════════════════════════════════════════════════════════════════════════

def detect_cross(closes: List[float], fast: int, slow: int) -> Optional[dict]:
    """
    Detect EMA(fast) × EMA(slow) crossover on a close price series.

    Fire when fast EMA crosses slow EMA AND the separation is STILL widening
    at the most recent bar vs. at the cross point.
    A contracting separation (ema_fast retreating toward ema_slow) should not fire.

    Pattern from gap300_signals.py (detect_gap_cross):
        - gap_pcts[-1] > gap_pcts[i]  means gap is still widening

    Returns dict with direction, bars_since, ema_fast, ema_slow, sep_pct
    or None if no widening cross detected.
    """
    if len(closes) < slow + 2:
        return None

    ema_fast_series = _ema_series(closes, fast)
    ema_slow_series = _ema_series(closes, slow)

    # Build aligned index list — only indices where both EMAs are valid
    ema_f_map = {i: v for i, v in enumerate(ema_fast_series) if v is not None}
    ema_s_map = {i: v for i, v in enumerate(ema_slow_series) if v is not None}
    common = sorted(set(ema_f_map.keys()) & set(ema_s_map.keys()))
    if len(common) < 2:
        return None

    # ── Step 1: Find the most recent cross ────────────────────────────────────
    # A cross occurs when ef_prev ≈ es_prev BUT ef_cur ≠ es_cur.
    # Using gap sign-change: (gap_prev < 0 AND gap_cur > 0) → LONG
    #                        (gap_prev > 0 AND gap_cur < 0) → SHORT
    cross_idx, cross_dir = None, None
    for j in range(1, len(common)):
        i_prev = common[j - 1]
        i_cur  = common[j]
        ef_prev, ef_cur = ema_f_map[i_prev], ema_f_map[i_cur]
        es_prev, es_cur = ema_s_map[i_prev], ema_s_map[i_cur]

        gap_prev = ef_prev - es_prev
        gap_cur  = ef_cur  - es_cur

        # Cross = sign change of gap between adjacent bars
        if gap_prev < 0 and gap_cur > 0:
            cross_idx, cross_dir = i_cur, 'LONG'
            break
        if gap_prev > 0 and gap_cur < 0:
            cross_idx, cross_dir = i_cur, 'SHORT'
            break

    if cross_idx is None:
        return None

    last_idx = common[-1]
    ef_last = ema_f_map[last_idx]
    es_last = ema_s_map[last_idx]
    raw_gap_now = ef_last - es_last

    # ── Step 2: Widening check (gap300 pattern) ───────────────────────────────
    # gap300 pattern: gap_pcts[-1] > gap_pcts[i]  at the cross bar i.
    # For MA cross, gap at the cross bar ≈ 0.  After a valid cross:
    #   LONG:  gap is positive after cross; need gap_now > gap_at_cross (>0)
    #   SHORT: gap is negative after cross; need gap_now < gap_at_cross (<0)
    # Comparing vs. the cross-bar gap (≈0):
    #   LONG:  gap_now > 0  (any positive gap means widening from 0)
    #   SHORT: gap_now < 0  (any negative gap means widening from 0)
    # This is already guaranteed by our sign-change detection.
    # BUT: the gap must also be GROWING after the cross, not just any positive value.
    # Check: compare gap_now against the FIRST bar after the cross.
    # If gap_now <= gap_first_bar_after_cross: gap has stalled → reject.
    ef_at_cross = ema_f_map[cross_idx]
    es_at_cross = ema_s_map[cross_idx]
    raw_gap_cross = ef_at_cross - es_at_cross  # ≈ 0

    # Find the first bar after the cross
    first_after_idx = None
    for ci in common:
        if ci > cross_idx:
            first_after_idx = ci
            break

    if first_after_idx is not None:
        ef_first = ema_f_map[first_after_idx]
        es_first = ema_s_map[first_after_idx]
        raw_gap_first = ef_first - es_first  # first non-zero gap after cross

        if cross_dir == 'LONG':
            # Gap must be growing: raw_gap_now must exceed first bar's gap
            if raw_gap_now <= raw_gap_first:
                return None
        elif cross_dir == 'SHORT':
            # Gap must be growing in negative direction: raw_gap_now < first bar's gap
            if raw_gap_now >= raw_gap_first:
                return None

    price   = closes[-1]
    sep_pct = abs(raw_gap_now) / price * 100.0
    bars_since = max(len(closes) - 1 - cross_idx, 0)

    return {
        'direction':  cross_dir,
        'bars_since': bars_since,
        'ema_fast':   round(ef_last, 6),
        'ema_slow':   round(es_last, 6),
        'sep_pct':    round(sep_pct, 4),
        'price':      price,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
# Tuner DB
# ═══════════════════════════════════════════════════════════════════════════

def init_tuner_db():
    """Create tuner table if it doesn't exist."""
    conn = sqlite3.connect(_TUNER_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ma_cross_5m_best (
            token       TEXT NOT NULL,
            direction   TEXT NOT NULL,
            fast        INTEGER NOT NULL,
            slow        INTEGER NOT NULL,
            win_rate    REAL NOT NULL,
            avg_pnl_pct REAL NOT NULL,
            signal_count INTEGER NOT NULL,
            total_long  INTEGER NOT NULL DEFAULT 0,
            total_short INTEGER NOT NULL DEFAULT 0,
            updated_at  INTEGER NOT NULL,
            PRIMARY KEY (token, direction)
        )
    """)
    conn.commit()
    conn.close()


def load_token_params() -> Dict:
    """Load per-token tuned params. Returns {TOKEN: {'LONG': {...}, 'SHORT': {...}}."""
    init_tuner_db()
    try:
        conn = sqlite3.connect(_TUNER_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            SELECT token, direction, fast, slow, win_rate, avg_pnl_pct, signal_count
            FROM ma_cross_5m_best
        """)
        rows = c.fetchall()
        conn.close()
        params = {}
        for token, direction, fast, slow, wr, ap, sc in rows:
            t = token.upper()
            if t not in params:
                params[t] = {}
            params[t][direction.upper()] = {
                'fast': fast, 'slow': slow,
                'wr': wr, 'n': sc,
            }
        return params
    except Exception as e:
        print(f"[ma_cross_5m] load_token_params error: {e}")
        return {}


def save_token_params(token: str, direction: str,
                      fast: int, slow: int,
                      win_rate: float, avg_pnl_pct: float,
                      signal_count: int,
                      total_long: int = 0, total_short: int = 0):
    """Save (or replace) best config for a token+direction."""
    init_tuner_db()
    try:
        conn = sqlite3.connect(_TUNER_DB, timeout=5)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO ma_cross_5m_best
              (token, direction, fast, slow, win_rate, avg_pnl_pct,
               signal_count, total_long, total_short, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (token.upper(), direction.upper(), fast, slow,
              win_rate, avg_pnl_pct, signal_count,
              total_long, total_short, int(time.time())))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ma_cross_5m] save_token_params error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# Backtest sweep — find best fast/slow per token+direction
# ═══════════════════════════════════════════════════════════════════════════

def _backtest_pair(closes: List[float], fast: int, slow: int, direction: str) -> Optional[dict]:
    """
    Backtest EMA(fast)×EMA(slow) crossover for one direction on historical closes.

    LONG:  buy when fast crosses above slow, hold for slow*2 bars max, sell at end.
    SHORT: sell when fast crosses below slow, hold for slow*2 bars max, cover at end.
    Exit early on opposite cross.

    Returns {win_rate, avg_pnl_pct, signal_count, total_long, total_short}.
    """
    if len(closes) < slow + 10:
        return None

    ema_fast_series = _ema_series(closes, fast)
    ema_slow_series = _ema_series(closes, slow)

    ema_f_map = {i: v for i, v in enumerate(ema_fast_series) if v is not None}
    ema_s_map = {i: v for i, v in enumerate(ema_slow_series) if v is not None}
    common = sorted(set(ema_f_map.keys()) & set(ema_s_map.keys()))
    if len(common) < 2:
        return None

    wins, total = 0, 0
    pnl_long, pnl_short = 0.0, 0.0
    total_long, total_short = 0, 0

    hold_max = slow * 2

    for j in range(1, len(common)):
        i_prev = common[j - 1]
        i_cur  = common[j]
        ef_prev, ef_cur  = ema_f_map[i_prev], ema_f_map[i_cur]
        es_prev, es_cur  = ema_s_map[i_prev], ema_s_map[i_cur]

        signal = None
        if direction == 'LONG':
            if ef_prev <= es_prev and ef_cur > es_cur:
                signal = 'LONG'
        elif direction == 'SHORT':
            if ef_prev >= es_prev and ef_cur < es_cur:
                signal = 'SHORT'

        if signal is None:
            continue

        entry_price = closes[i_cur]
        hold = min(hold_max, len(closes) - i_cur - 1)
        if hold < 1:
            continue
        exit_price = closes[i_cur + hold]

        if signal == 'LONG':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
            pnl_long += pnl_pct
            total_long += 1
            if pnl_pct > 0:
                wins += 1
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100
            pnl_short += pnl_pct
            total_short += 1
            if pnl_pct > 0:
                wins += 1
        total += 1

    if total == 0:
        return None

    return {
        'win_rate':    round(wins / total * 100, 2),
        'avg_pnl_pct': round((pnl_long + pnl_short) / total, 4),
        'signal_count': total,
        'total_long':  total_long,
        'total_short': total_short,
    }


def sweep_token(token: str, closes: List[float] = None) -> dict:
    """
    Run full param sweep for one token (all fast/slow combos).
    Returns dict of results per direction.
    If closes not provided, fetches 5m candles for that token.
    """
    if closes is None:
        bars = get_5m_candles(token, lookback=LOOKBACK_CANDLES)
        closes = [b['close'] for b in bars]
    if len(closes) < 200:
        return {}

    results = {'LONG': {}, 'SHORT': {}}
    for fast in FAST_RANGE:
        for slow in SLOW_RANGE:
            if slow < fast * MIN_SLOW_FAST_RATIO:
                continue
            for direction in ('LONG', 'SHORT'):
                res = _backtest_pair(closes, fast, slow, direction)
                if res is None:
                    continue
                key = (fast, slow)
                if key not in results[direction]:
                    results[direction][key] = res

    return results


def run_sweep_all_tokens() -> int:
    """Sweep all tokens in price_history. Returns number of tokens tuned."""
    init_tuner_db()
    tokens = []
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=10)
        c = conn.cursor()
        c.execute("SELECT DISTINCT token FROM candles_1m ORDER BY token")
        tokens = [r[0] for r in c.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[ma_cross_5m] sweep: token list error: {e}")
        return 0

    tuned = 0
    for token in tokens:
        bars = get_5m_candles(token, lookback=LOOKBACK_CANDLES)
        closes = [b['close'] for b in bars]
        if len(closes) < 200:
            continue

        sweep_results = sweep_token(token, closes)

        for direction in ('LONG', 'SHORT'):
            by_dir = sweep_results.get(direction, {})
            if not by_dir:
                continue

            # Score: primarily avg_pnl_pct, tiebreak by signal_count
            best = max(by_dir.items(),
                       key=lambda x: (x[1]['avg_pnl_pct'], x[1]['signal_count']))
            fast, slow = best[0]
            res = best[1]

            save_token_params(
                token=token,
                direction=direction,
                fast=fast, slow=slow,
                win_rate=res['win_rate'],
                avg_pnl_pct=res['avg_pnl_pct'],
                signal_count=res['signal_count'],
                total_long=res['total_long'],
                total_short=res['total_short'],
            )
            print(f"  {token:8s} {direction:5s} fast={fast:2d} slow={slow:3d} "
                  f"wr={res['win_rate']:.1f}% avg_pnl={res['avg_pnl_pct']:+.3f}% n={res['signal_count']}")
        tuned += 1

    print(f"[ma_cross_5m] Sweep complete. {tuned} tokens tuned.")
    return tuned


# ═══════════════════════════════════════════════════════════════════════════
# Scanner — emit signals using loaded params
# ═══════════════════════════════════════════════════════════════════════════

_TOKEN_CACHE: Optional[Dict] = None


def load_params() -> Dict:
    global _TOKEN_CACHE
    if _TOKEN_CACHE is not None:
        return _TOKEN_CACHE
    params = load_token_params()
    params['DEFAULT'] = _DEFAULT_PARAMS.copy()
    _TOKEN_CACHE = params
    print(f"[ma_cross_5m] Loaded params for {len(params)-1} tokens")
    return params


def reset_cache():
    global _TOKEN_CACHE
    _TOKEN_CACHE = None


def scan_ma_cross_5m_signals(prices_dict: dict) -> int:
    """
    Scan tokens for 5m MA crossover signals and write to DB.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written.
    """
    params = load_params()

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

        p = params.get(token.upper(), params['DEFAULT'])
        closes_5m = [b['close'] for b in get_5m_candles(token)]

        # Try SHORT first, then LONG (no dual fire)
        fired_short = False
        fired_long  = False

        for direction in ('SHORT', 'LONG'):
            p_dir = p.get(direction, _DEFAULT_PARAMS[direction])

            res = detect_cross(closes_5m, p_dir['fast'], p_dir['slow'])
            if res is None or res['direction'] != direction:
                continue

            # Reject shallow crossovers — noise
            if res['sep_pct'] < MIN_SEP_PCT:
                continue

            # Confidence: win_rate scaled, clamped 50-80
            wr = p_dir['wr']
            conf = min(80, max(50, round(wr * 1.10)))
            source = SOURCE_SHORT if direction == 'SHORT' else SOURCE_LONG
            sig_type = SIGNAL_TYPE_SHORT if direction == 'SHORT' else SIGNAL_TYPE_LONG

            try:
                sid = add_signal(
                    token=token.upper(),
                    direction=direction,
                    signal_type=sig_type,
                    source=source,
                    confidence=conf,
                    value=float(conf),
                    price=price,
                    exchange='hyperliquid',
                    timeframe='5m',
                    z_score=None,
                    z_score_tier=None,
                )
                if sid:
                    added += 1
                    set_cooldown(token, direction, hours=COOLDOWN_HOURS)
                    if direction == 'SHORT':
                        fired_short = True
                    else:
                        fired_long = True
                    print(f"  {direction:5s}-5m {token:8s} conf={conf:.0f}% "
                          f"fast={p_dir['fast']} slow={p_dir['slow']} "
                          f"sep={res['sep_pct']:.3f}% bars={res['bars_since']} [{source}]")
            except Exception as e:
                print(f"[ma_cross_5m] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='ma_cross_5m — tuner + scanner')
    parser.add_argument('--sweep', action='store_true', help='Run daily param sweep')
    parser.add_argument('--scan',  action='store_true', help='Run signal scanner')
    args = parser.parse_args()

    if args.sweep:
        run_sweep_all_tokens()
    elif args.scan:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from signal_schema import get_all_latest_prices
        prices = get_all_latest_prices()
        n = scan_ma_cross_5m_signals(prices)
        print(f"[ma_cross_5m] Done. {n} signals emitted.")
    else:
        parser.print_help()
