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

# ── Tunable params ──────────────────────────────────────────────────────────
EMA_PERIOD    = 30      # EMA period in bars
PURITY_THRESH = 0.55    # fraction of lookback bars that must be on the right side of EMA
LOOKBACK      = 20      # bars to check for purity (20 × 1m = 20 min)
MIN_GAP_PCT   = 0.30    # price must be at least this far from EMA (% of price) to fire
CONF_BASE     = 60      # base confidence for a clean trend signal
CONF_GAP_BONUS = 20     # extra confidence when gap is large (> 1.0%)
DRY_RUN       = False

# ── DB paths ─────────────────────────────────────────────────────────────────
STATIC_DB = '/root/.hermes/data/signals_hermes.db'


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
    conn = sqlite3.connect(STATIC_DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")

    # Fetch last LOOKBACK + EMA_PERIOD bars for warmup
    rows = conn.execute("""
        SELECT price FROM price_history
        WHERE token = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (token, LOOKBACK + EMA_PERIOD)).fetchall()

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

    if direction is None:
        directions = ['LONG', 'SHORT']
    else:
        directions = [direction]

    signals = []
    for d in directions:
        if d == 'LONG':
            if gap_pct < MIN_GAP_PCT:
                continue
            above = sum(1 for p in lookback_prices if p > ema)
            purity = above / LOOKBACK
            if purity < PURITY_THRESH:
                continue
            # Confidence: base + gap bonus
            conf = min(CONF_BASE + max(0, (gap_pct - MIN_GAP_PCT) * 10) + (purity - PURITY_THRESH) * 40, 99)
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
            # Pattern: grinding up, then violent breakdown. Mean-reversion on the short side.
            if gap_pct >= -1.0:  # must be >= 1% below EMA to be a crash
                continue
            # Confirm uptrend was in place: most of the lookback bars were ABOVE EMA
            above = sum(1 for p in lookback_prices if p > ema)
            above_purity = above / LOOKBACK
            if above_purity < 0.65:  # uptrend wasn't established — don't catch random drops
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
    """
    Scan all tokens (or single token) and emit trend_purity signals.

    Args:
        conf_min: minimum confidence to emit
        token: if set, only scan this token
    """
    conn = sqlite3.connect(STATIC_DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")

    if token:
        tokens = [token]
    else:
        rows = conn.execute("SELECT DISTINCT token FROM latest_prices").fetchall()
        tokens = [r[0] for r in rows]

    conn.close()

    emitted = 0
    for tok in tokens:
        for direction in ['LONG', 'SHORT']:
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


def main():
    global DRY_RUN
    parser = argparse.ArgumentParser(description='trend_purity signals')
    parser.add_argument('--dry', action='store_true', help='dry run — do not write to DB')
    parser.add_argument('--token', type=str, default=None, help='scan single token')
    parser.add_argument('--conf-min', type=int, default=60, help='minimum confidence to emit')
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


if __name__ == '__main__':
    main()
