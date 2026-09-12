# Migrated from ../trend_purity_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
trend_purity_signals.py — Standalone trend purity signal.

Fires when price is consistently above (LONG) or below (SHORT) EMA30
with enough purity — measures how "clean" the trend is.

Designed as a confluence giver: other signals (gap300, gap300_5m, accel_300)
can use trend_purity as confirmation that the move has sustained direction,
not just momentary spike.

Architecture:
  - Reads 1m bars from signals_hermes.db price_history (always fresh)
  - EMA30 computed on the fly — no local candle tables needed
  - CLI: python3 trend_purity_signals.py [--dry] [--token TOKEN] [--conf-min 60]
  - Called from signal_gen.py: scan_trend_purity_signals()
"""
import sys, os, argparse, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
from signal_schema import add_signal
from hermes_constants import (
    TP_MIN_GAP_PCT,
    TP_PURITY_THRESH,
    TP_LOOKBACK,
    TP_SHORT_CRASH_THRESH,
    TP_SHORT_UPTREND_PURITY,
)

# ── Tunable params (sourced from hermes_constants.py) ─────────────────────────
EMA_PERIOD    = 30      # EMA period in bars
PURITY_THRESH = TP_PURITY_THRESH       # fraction of lookback bars must be above EMA
LOOKBACK      = TP_LOOKBACK            # bars to check for purity
MIN_GAP_PCT   = TP_MIN_GAP_PCT         # price must be at least this far from EMA to fire
CONF_BASE     = 65      # base confidence for a clean trend signal
CONF_GAP_BONUS = 20     # extra confidence when gap is large (> 1.0%)
DRY_RUN       = False

# ── DB paths ─────────────────────────────────────────────────────────────────
STATIC_DB = '/root/.hermes/data/signals_hermes.db'
RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'


def _ema(prices: list) -> float:
    """Compute EMA30 over a list of closing prices."""
    if len(prices) < EMA_PERIOD:
        return None
    k = 2 / (EMA_PERIOD + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def detect_trend_purity(token: str, direction: str = None):
    """
    Detect trend purity signal for a token.

    LONG:  price consistently above EMA30 with PURITY_THRESH fraction of bars above EMA
    SHORT: price consistently below EMA30

    Returns signal dict or None.
    """
    conn = None
    try:
        conn = sqlite3.connect(STATIC_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")

        # Fetch last LOOKBACK + EMA_PERIOD bars for warmup
        rows = conn.execute("""
            SELECT price FROM price_history
            WHERE token = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (token, LOOKBACK + EMA_PERIOD)).fetchall()
    finally:
        if conn:
            conn.close()

    if len(rows) < LOOKBACK + EMA_PERIOD:
        return None

    prices = [r[0] for r in reversed(rows)]  # oldest first
    lookback_prices = prices[-LOOKBACK:]

    ema = _ema(prices)
    if ema is None:
        return None

    current_price = lookback_prices[-1]
    gap_pct = (current_price - ema) / ema * 100

    # ── Momentum/speed guard — block stale, falling, or slow entries ────────
    # Root cause: KAS loss on 2026-09-11 — is_stale=true, wave_phase=falling,
    # speed_percentile=13.7. All three were red flags that should have blocked.
    _speed_data = None
    try:
        _spd_conn = sqlite3.connect(RUNTIME_DB, timeout=10)
        _spd_row = _spd_conn.execute(
            'SELECT speed_percentile, is_stale, momentum_score, price_acceleration, wave_phase '
            'FROM token_speeds WHERE token = ?', (token.upper(),)
        ).fetchone()
        _spd_conn.close()
        if _spd_row:
            _speed_data = {
                'speed_percentile': _spd_row[0],
                'is_stale': bool(_spd_row[1]),
                'momentum_score': _spd_row[2],
                'price_acceleration': _spd_row[3],
                'wave_phase': _spd_row[4],
            }
    except Exception:
        pass  # no speed data — don't block, just skip guard

    # ── BB position guard — block entries at resistance ceiling ────────────
    # Root cause: INJ LONG loss on 2026-09-12 — entered at bb_position=0.967
    # (stalling just below upper BB). Price had run up 1hr then crashed -6.75%.
    # Winners enter at bb<0.90 (room to run) or bb>1.0 (breakout above BB).
    _bb_position = None
    try:
        if len(prices) >= 20:
            _w = prices[-20:]
            _mean = sum(_w) / len(_w)
            _var = sum((p - _mean) ** 2 for p in _w) / len(_w)
            _std = _var ** 0.5
            if _std > 0:
                _bb_position = round((current_price - (_mean - 2 * _std)) / (4 * _std), 4)
    except Exception:
        pass

    if direction is None:
        directions = ['LONG', 'SHORT']
    else:
        directions = [direction]

    signals = []
    for d in directions:
        # ── Momentum/speed guards (LONG-specific) ──────────────────────────
        if d == 'LONG' and _speed_data:
            # Block if signal is stale (price flat, no directional movement)
            if _speed_data['is_stale']:
                continue
            # Block if speed is too low (price crawling — trend has no energy)
            if _speed_data['speed_percentile'] is not None and _speed_data['speed_percentile'] < 20:
                continue
            # Block if wave_phase is falling (price decelerating into entry)
            if _speed_data['wave_phase'] == 'falling':
                continue

        # ── BB position guard (LONG-specific) ──────────────────────────────
        # Block when price is stalling at resistance ceiling (0.90 < bb < 1.0).
        # Allow bb > 1.0 (breakout) and bb < 0.90 (room to run).
        if d == 'LONG' and _bb_position is not None:
            if 0.90 < _bb_position < 1.0:
                continue

        if d == 'LONG':
            if gap_pct < MIN_GAP_PCT:
                continue
            above = sum(1 for p in lookback_prices if p > ema)
            purity = above / LOOKBACK
            if purity < PURITY_THRESH:
                continue
            # Confidence: base + gap bonus + purity bonus
            conf = min(CONF_BASE + max(0, (gap_pct - MIN_GAP_PCT) * 25) + (purity - PURITY_THRESH) * 50, 99)
            signals.append({
                'token': token,
                'signal_type': 'trend_purity_long',
                'source': 'trend_purity+',
                'direction': 'LONG',
                'confidence': round(conf),
                'gap_pct': round(gap_pct, 4),
                'purity': round(purity, 3),
                'ema': round(ema, 6),
                'price': round(current_price, 6),
                'bars_above': above,
                'lookback': LOOKBACK,
                'bb_position': round(_bb_position, 4) if _bb_position is not None else None,
            })

        elif d == 'SHORT':
            # ── CRASH SHORT: "trend looked great till it didn't" ───────────────
            # An uptrend was in place (trend_purity LONG fires on the way up).
            # Price was persistently above EMA30 — then crashed below it.
            # This catches the breakdown SHORT, not the bounce.
            #
            # Logic:
            #   1. Prerequisite: price must be at least 1% below EMA (genuine crash)
            #   2. Uptrend was in place: most of the lookback window was ABOVE EMA
            #      (high LONG-side purity confirms the trend was established)
            #   3. Current bar is the one that cracked below EMA or widened the gap fast
            #
            #   1. Prerequisite: price must be at least TP_SHORT_CRASH_THRESH below EMA (genuine crash)
            if gap_pct >= TP_SHORT_CRASH_THRESH:
                continue
            # Confirm uptrend was in place: most of the lookback bars were ABOVE EMA
            above = sum(1 for p in lookback_prices if p > ema)
            above_purity = above / LOOKBACK
            if above_purity < TP_SHORT_UPTREND_PURITY:
                continue
            # The crash bar: current price is significantly worse than the window average
            recent_gaps = [(p - ema) / ema * 100 for p in lookback_prices]
            avg_gap = sum(recent_gaps) / len(recent_gaps)
            # path_a: violent crash — gap went from positive/flat to sharply negative
            path_a = gap_pct < avg_gap - 1.0
            # path_b: sustained crash — still below EMA but purity of prior uptrend is very high
            path_b = above_purity >= 0.75 and gap_pct < -1.0
            if not (path_a or path_b):
                continue
            # Confidence: boost when uptrend was strong (high above_purity) + crash is sharp
            conf = min(65 + (above_purity - 0.65) * 60 + max(0, (-gap_pct - 1.0) * 15), 99)
            signals.append({
                'token': token,
                'signal_type': 'trend_purity_short',
                'source': 'trend_purity-',
                'direction': 'SHORT',
                'confidence': round(conf),
                'gap_pct': round(gap_pct, 4),
                'above_purity': round(above_purity, 3),
                'ema': round(ema, 6),
                'price': round(current_price, 6),
                'bars_above': above,
                'lookback': LOOKBACK,
                'path': 'A' if path_a else 'B',
            })

    if len(directions) == 1:
        return signals[0] if signals else None
    return signals


def scan(conf_min: int = 60, token: str = None):
    from hermes_constants import TREND_PURITY_ENABLED
    if not TREND_PURITY_ENABLED:
        return 0
    """
    Scan all tokens (or single token) and emit trend_purity signals.

    Args:
        conf_min: minimum confidence to emit
        token: if set, only scan this token
    """
    conn = None
    try:
        conn = sqlite3.connect(STATIC_DB, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")

        if token:
            tokens = [token]
        else:
            rows = conn.execute("SELECT DISTINCT token FROM latest_prices").fetchall()
            tokens = [r[0] for r in rows]
    finally:
        if conn:
            conn.close()

    emitted = 0
    for tok in tokens:
        for direction in ['LONG', 'SHORT']:
            # ── Per-direction kill-switch ─────────────────────────────────────────
            from hermes_constants import TREND_PURITY_PLUS_ENABLED, TREND_PURITY_MINUS_ENABLED
            if direction == 'LONG' and not TREND_PURITY_PLUS_ENABLED:
                continue
            if direction == 'SHORT' and not TREND_PURITY_MINUS_ENABLED:
                continue
            sig = detect_trend_purity(tok, direction)
            if not sig:
                continue
            if sig['confidence'] < conf_min:
                continue
            if not DRY_RUN:
                add_signal(**sig)
            emitted += 1
            purity_key = 'purity' if sig.get('purity') is not None else 'above_purity'
            print(f"  {tok:8s} {sig['direction']:5s} conf={sig['confidence']} gap={sig['gap_pct']:.3f}% purity={sig[purity_key]:.2f}")

    return emitted


def run(prices_dict=None):
    """Entry point for signals_runner. Returns count of signals emitted."""
    result = scan(conf_min=60)
    if result is None:
        return 0
    return result if isinstance(result, int) else len(result)


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == '__main__':
    import argparse, sys
    parser = argparse.ArgumentParser(description='trend_purity signals')
    parser.add_argument('--dry', action='store_true', help='dry run')
    parser.add_argument('--token', type=str, default=None)
    parser.add_argument('--conf-min', type=int, default=60)
    args = parser.parse_args()
    DRY_RUN = args.dry

    if args.token:
        print(f"Scanning {args.token}...")
        for direction in ['LONG', 'SHORT']:
            sig = detect_trend_purity(args.token, direction)
            if sig and sig['confidence'] >= args.conf_min:
                purity_key = 'purity' if sig.get('purity') is not None else 'above_purity'
                print(f"  {sig['direction']:5s} conf={sig['confidence']} gap={sig['gap_pct']:.3f}% purity={sig[purity_key]:.2f}")
    else:
        emitted = scan(conf_min=args.conf_min)
        print(f"\nTotal trend_purity signals emitted: {emitted}")