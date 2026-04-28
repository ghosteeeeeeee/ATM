#!/usr/bin/env python3
"""
exhaustion_signals.py — Trend exhaustion counter-trend signal.

Fires when price has extended too far in one direction and snaps back.

Trigger logic:
  exhaustion SHORT:  price was ABOVE EMA for CONSEC_THRESH+ bars,
                     then crosses BELOW EMA on the current bar.
                     "Uptrend exhausted — reversal lower incoming."
  exhaustion LONG:   price was BELOW EMA for CONSEC_THRESH+ bars,
                     then crosses ABOVE EMA on the current bar.
                     "Downtrend exhausted — reversal higher incoming."

Key design decisions:
  - Uses consecutive-bar count as primary trigger (not purity/fraction)
  - Gap magnitude is secondary — must be meaningful (MIN_GAP_PCT)
  - Requires prior trend to be established before firing
  - signal_compactor handles penalization when co-occurring with trend signals

Architecture:
  - Reads 1m bars from signals_hermes.db price_history (always fresh)
  - EMA30 computed on the fly
  - CLI: python3 exhaustion_signals.py [--dry] [--token TOKEN] [--conf-min 70]
  - Called from signal_gen.py: scan_exhaustion_signals()
"""
import sys, os, argparse, sqlite3
sys.path.insert(0, os.path.dirname(__file__))
from signal_schema import add_signal

# ── Tunable params ──────────────────────────────────────────────────────────
EMA_PERIOD     = 30     # EMA period in bars
CONSEC_THRESH  = 15     # minimum consecutive bars on wrong side of EMA before firing
MIN_GAP_PCT_SHORT = 0.00  # SHORT: any cross after long grind fires — gap is secondary
MIN_GAP_PCT_LONG  = 0.20  # LONG:  gap must be meaningful to avoid chop
CONF_BASE      = 70     # base confidence for exhaustion signal
CONF_GAP_BONUS = 15     # bonus confidence when gap is very large (> 1.0%)
MAX_CONSEC     = 60     # if trend exceeds this many bars, trend is too old — skip
LOOKBACK       = 80     # bars to fetch for EMA warmup + consec check
DRY_RUN        = False

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


def detect_exhaustion(token: str, direction: str = None):
    """
    Detect exhaustion reversal signal for a token.

    exhaustion SHORT: prior CONSEC_THRESH+ bars above EMA, now crossed below.
    exhaustion LONG:  prior CONSEC_THRESH+ bars below EMA, now crossed above.

    Returns signal dict or None.
    """
    conn = sqlite3.connect(STATIC_DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")

    # Fetch enough bars for EMA warmup + consecutive check
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

    ema = _ema(prices)
    if ema is None:
        return None

    # Compute EMA for each bar
    ema_series = []
    ema_val = prices[0]
    k = 2 / (EMA_PERIOD + 1)
    for i, p in enumerate(prices):
        if i < EMA_PERIOD - 1:
            ema_series.append(None)
            ema_val = p  # seed with early prices
        else:
            ema_val = p * k + ema_val * (1 - k)
            ema_series.append(ema_val)

    # Work backwards from most recent bar to find consecutive counts
    # Start from the most recent bar (index -1)
    current_price = prices[-1]
    current_ema = ema_series[-1]
    current_gap = (current_price - current_ema) / current_ema * 100

    # At crossing: current bar (-1) just crossed. The prior bar (-2) tells us
    # whether the trend was established before the cross.
    # For exhaustion SHORT: prior bar above EMA + current bar below EMA
    # For exhaustion LONG:  prior bar below EMA + current bar above EMA
    prior_price = prices[-2]
    prior_ema   = ema_series[-2]
    prior_gap   = (prior_price - prior_ema) / prior_ema * 100

    # Consecutive bars from prior bar going back (not current bar — at crossing, current resets)
    consec_above_prior = 0
    for i in range(len(prices) - 2, -1, -1):  # start from -2 (prior bar)
        if ema_series[i] is not None and prices[i] >= ema_series[i]:
            consec_above_prior += 1
        else:
            break

    consec_below_prior = 0
    for i in range(len(prices) - 2, -1, -1):
        if ema_series[i] is not None and prices[i] <= ema_series[i]:
            consec_below_prior += 1
        else:
            break

    if direction is None:
        directions = ['LONG', 'SHORT']
    else:
        directions = [direction]

    signals = []
    for d in directions:
        if d == 'SHORT':
            # ── exhaustion SHORT ────────────────────────────────────────────────
            # Prior bar was above EMA for CONSEC_THRESH+ bars, now crossed below.
            # XLM case: 32 bars above → first bar below at 02:11 → exhaustion SHORT
            if consec_above_prior < CONSEC_THRESH:
                continue
            if consec_above_prior > MAX_CONSEC:
                continue
            # Cross check: prior bar above EMA, current bar below EMA
            if prior_ema is None or current_ema is None:
                continue
            if prior_price <= prior_ema or current_price >= current_ema:
                continue
            # Gap: SHORT fires on any cross after sustained grind (MIN_GAP_PCT_SHORT=0)
            if current_gap > -MIN_GAP_PCT_SHORT:
                continue

            # Confidence: base + how extended + how sharp the crack
            consec_score = min((consec_above_prior - CONSEC_THRESH) / (MAX_CONSEC - CONSEC_THRESH) * 20, 20)
            gap_score = min(abs(current_gap) / 1.0 * 10, 10) if abs(current_gap) > 0.0 else 0
            conf = min(CONF_BASE + consec_score + gap_score + CONF_GAP_BONUS * (1 if abs(current_gap) > 1.0 else 0), 99)

            signals.append({
                'token': token,
                'signal_type': 'exhaustion_short',
                'source': 'exhaustion+',
                'direction': 'SHORT',
                'confidence': round(conf),
                'gap_pct': round(current_gap, 4),
                'consec_above': consec_above_prior,
                'consec_threshold': CONSEC_THRESH,
                'ema': round(current_ema, 6),
                'price': round(current_price, 6),
            })

        elif d == 'LONG':
            # ── exhaustion LONG ─────────────────────────────────────────────────
            # Prior bar was below EMA for CONSEC_THRESH+ bars, now crossed above.
            # ZEN case: 15 bars below → first bar above at 04:01 → exhaustion LONG
            if consec_below_prior < CONSEC_THRESH:
                continue
            if consec_below_prior > MAX_CONSEC:
                continue
            # Cross check: prior bar below EMA, current bar above EMA
            if prior_ema is None or current_ema is None:
                continue
            if prior_price >= prior_ema or current_price <= current_ema:
                continue
            if current_gap < MIN_GAP_PCT_LONG:
                continue

            consec_score = min((consec_below_prior - CONSEC_THRESH) / (MAX_CONSEC - CONSEC_THRESH) * 20, 20)
            gap_score = min(abs(current_gap - MIN_GAP_PCT_LONG) / 0.8 * 10, 10) if current_gap > MIN_GAP_PCT_LONG else 0
            conf = min(CONF_BASE + consec_score + gap_score + CONF_GAP_BONUS * (1 if abs(current_gap) > 1.0 else 0), 99)

            signals.append({
                'token': token,
                'signal_type': 'exhaustion_long',
                'source': 'exhaustion-',
                'direction': 'LONG',
                'confidence': round(conf),
                'gap_pct': round(current_gap, 4),
                'consec_below': consec_below_prior,
                'consec_threshold': CONSEC_THRESH,
                'ema': round(current_ema, 6),
                'price': round(current_price, 6),
            })

    if len(directions) == 1:
        return signals[0] if signals else None
    return signals


def scan(conf_min: int = 70, token: str = None):
    """
    Scan all tokens (or single token) and emit exhaustion signals.

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
            sig = detect_exhaustion(tok, direction)
            if not sig:
                continue
            if sig['confidence'] < conf_min:
                continue
            if not DRY_RUN:
                add_signal(**sig)
            emitted += 1
            extra = f" consec={sig.get('consec_above', sig.get('consec_below', '?'))}"
            print(f"  {tok:8s} {sig['direction']:5s} conf={sig['confidence']} gap={sig['gap_pct']:+.3f}%{extra}")

    return emitted


def main():
    global DRY_RUN
    parser = argparse.ArgumentParser(description='exhaustion signals')
    parser.add_argument('--dry', action='store_true', help='dry run — do not write to DB')
    parser.add_argument('--token', type=str, default=None, help='scan single token')
    parser.add_argument('--conf-min', type=int, default=70, help='minimum confidence to emit')
    args = parser.parse_args()
    DRY_RUN = args.dry

    if args.token:
        print(f"Scanning {args.token}...")
        for direction in ['LONG', 'SHORT']:
            sig = detect_exhaustion(args.token, direction)
            if sig and sig['confidence'] >= args.conf_min:
                extra = f" consec={sig.get('consec_above', sig.get('consec_below', '?'))}"
                print(f"  {sig['direction']:5s} conf={sig['confidence']} gap={sig['gap_pct']:+.3f}%{extra}")
    else:
        emitted = scan(conf_min=args.conf_min)
        print(f"\nTotal exhaustion signals emitted: {emitted}")


if __name__ == '__main__':
    main()
