#!/usr/bin/env python3
"""
accel_300_signals.py — Persistent Gap Above EMA(300) Acceleration Signal.

Concept: price breaks above EMA300 (was below within last N bars), then
stays above for PERSISTENCE_BARS consecutive bars while the gap vs EMA300
is GROWING. The growing gap = accelerating momentum — the move isn't fading.

This catches "slow breakouts" that gap_300 misses — gap_300 fires on the
cross moment, accel_300 fires on the confirmation that momentum is persisting.

Signal logic:
  - LONG:  price was below EMA300 within last LOOKBACK bars,
            now above EMA300 for PERSISTENCE_BARS consecutive bars,
            and current gap_pct > gap_pct PERSISTENCE_BARS bars ago (gap is growing)
  - SHORT: mirror for downside

Architecture:
  price_history (1m closes, fresh every minute) → EMA(300) → gap analysis
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal types:
  - accel_300_long  : persistent above-EMA300 with growing gap — momentum accelerating long
  - accel_300_short : persistent below-EMA300 with growing gap — momentum accelerating short

Run:
    python3 accel_300_signals.py           # live scan
    python3 accel_300_signals.py --dry     # dry run (log only)
"""

import sys, os, sqlite3, time, datetime
from typing import Optional, List
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, price_age_minutes

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'   # price_history — live 1m prices

# ── Signal constants ──────────────────────────────────────────────────────────
PERIOD             = 300      # EMA(300) on 1m prices
LOOKBACK           = 30       # bars ago when price was on the other side of EMA300
PERSISTENCE_BARS   = 3        # must be persistently above/below EMA for this many bars
MIN_GAP_PCT        = 0.10     # minimum gap above EMA300 to fire (%)
MIN_GAP_GROWTH_PCT = 0.02     # gap must grow by at least this % vs PERSISTENCE_BARS ago
COOLDOWN_BARS      = 10       # dedup: only fire once per N bars per token+direction
LOOKBACK_1M        = 700      # 1m prices to fetch (warmup + detection window)
DRY_RUN            = '--dry' in sys.argv

SIGNAL_TYPE_LONG   = 'accel_300_long'
SIGNAL_TYPE_SHORT  = 'accel_300_short'
SOURCE_LONG        = 'accel-300+'
SOURCE_SHORT       = 'accel-300-'


# ═══════════════════════════════════════════════════════════════════════════════
# EMA helpers
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


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices — the ONLY reliable
    source for live signal generation. timestamps are in SECONDS (Unix time).

    Returns list of {timestamp, price} dicts, oldest first.
    Freshness guard: returns [] if most recent price is > 5 minutes old.
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

        most_recent_ts = rows[-1][0]
        if (time.time() - most_recent_ts) > 120:
            print(f"  [accel-300] {token}: stale price_history (last ts {most_recent_ts}), skipping")
            return []

        # Bar-to-bar gap guard — detect missing data
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        if bar_gaps:
            mean_gap = sum(bar_gaps) / len(bar_gaps)
            variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
            std_gap = variance ** 0.5
            threshold = max(150, mean_gap + 3.0 * std_gap)
            for i in range(1, len(rows)):
                if rows[i][0] - rows[i-1][0] > threshold:
                    print(f"  [accel-300] {token}: data gap, skipping")
                    return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        print(f"  [accel-300] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_accel_300(token: str, prices: list) -> Optional[dict]:
    """
    Detect persistent gap above EMA(300) with growing gap.

    Fire when ALL of these are true:
      1. Price was BELOW EMA300 at some point within last LOOKBACK bars
      2. Price is NOW above EMA300 with gap >= MIN_GAP_PCT
      3. Price has been above EMA300 for PERSISTENCE_BARS consecutive bars
      4. Current gap_pct > gap_pct PERSISTENCE_BARS bars ago (gap is GROWING)
      5. Not in cooldown window (tracked by caller via recent_trade_exists)

    Returns dict with direction, gap_pct, gap_growth, bars_since_cross, or None.
    """
    n = len(prices)
    if n < PERIOD + LOOKBACK + PERSISTENCE_BARS + 5:
        return None

    closes = [p['price'] for p in prices]
    ema300 = _ema_series(closes, PERIOD)

    # Build gap_pct series
    gap_pcts = []
    for i in range(len(closes)):
        if ema300[i] is None or ema300[i] == 0:
            gap_pcts.append(None)
        else:
            gap_pcts.append((closes[i] - ema300[i]) / ema300[i] * 100.0)

    # Walk through and detect
    # Start from index where we have enough history for all checks
    for i in range(PERIOD + LOOKBACK, len(closes) - 1):
        price = closes[i]
        ema_val = ema300[i]
        if ema_val is None:
            continue

        gap_now = gap_pcts[i]
        if gap_now is None:
            continue

        # ── Direction ────────────────────────────────────────────────────────────
        current_above = price > ema_val
        current_below = price < ema_val

        # ── Condition 1: Was on the other side within LOOKBACK bars? ─────────────
        was_above_recently = False
        was_below_recently = False
        for j in range(i - LOOKBACK, i):
            if j >= 0 and gap_pcts[j] is not None:
                if closes[j] > ema300[j]:
                    was_above_recently = True
                else:
                    was_below_recently = True

        if current_above and not was_below_recently:
            continue  # Never went below — not a fresh breakout
        if current_below and not was_above_recently:
            continue  # Never went above — not a fresh breakdown

        direction = 'LONG' if current_above else 'SHORT'

        # ── Condition 2: Gap >= MIN_GAP_PCT ────────────────────────────────────
        if gap_now < MIN_GAP_PCT:
            continue

        # ── Condition 3: Persistently above/below for PERSISTENCE_BARS bars ─────
        persistent = True
        for j in range(i - PERSISTENCE_BARS + 1, i + 1):
            if j < 0 or gap_pcts[j] is None:
                persistent = False
                break
            if direction == 'LONG' and closes[j] <= ema300[j]:
                persistent = False
                break
            if direction == 'SHORT' and closes[j] >= ema300[j]:
                persistent = False
                break

        if not persistent:
            continue

        # ── Condition 4: Gap is GROWING (current > PERSISTENCE_BARS ago) ────────
        gap_then_idx = i - PERSISTENCE_BARS
        if gap_then_idx < 0 or gap_pcts[gap_then_idx] is None:
            continue

        gap_then = gap_pcts[gap_then_idx]
        gap_growth = gap_now - gap_then

        if gap_growth <= MIN_GAP_GROWTH_PCT:
            continue  # Gap is not accelerating — stale signal

        # ── Cooldown: bars since last signal (checked by caller via recent_trade_exists) ──
        # We compute how many bars ago the breakout cross happened
        cross_bar = None
        for j in range(i - LOOKBACK, i + 1):
            if j < 0 or gap_pcts[j] is None:
                continue
            if direction == 'LONG' and closes[j] > ema300[j]:
                if j > 0 and closes[j-1] <= ema300[j-1]:
                    cross_bar = j  # found the cross
                    break
            if direction == 'SHORT' and closes[j] < ema300[j]:
                if j > 0 and closes[j-1] >= ema300[j-1]:
                    cross_bar = j
                    break

        bars_since_cross = i - cross_bar if cross_bar is not None else 0

        return {
            'direction': direction,
            'gap_pct': round(gap_now, 4),
            'gap_growth': round(gap_growth, 4),
            'gap_then': round(gap_then, 4),
            'bars_since_cross': bars_since_cross,
            'price': price,
        }

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_signals(prices_dict: dict) -> int:
    """
    Scan tokens for accel_300 signals.

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
        if not prices or len(prices) < PERIOD + LOOKBACK + PERSISTENCE_BARS + 5:
            continue

        sig = detect_accel_300(token, prices)
        if sig is None:
            continue

        # direction now known — apply direction-specific cooldown AFTER detecting signal
        from signal_schema import get_cooldown
        cd = get_cooldown(token) or {}
        if cd.get(f"{token.upper()}:{sig['direction']}"):
            continue

        direction = sig['direction']
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Confidence: base on gap strength + gap growth
        # MIN_GAP_PCT=0.10 → base 65, larger gap → up to 80
        # Bonus for strong gap growth (requires growth > 0.05% to earn bonus)
        gap_bonus = max(0, sig['gap_growth'] - 0.05) * 200  # max ~20 for 0.15%+ growth
        confidence = int(min(80, 65 + max(0, (sig['gap_pct'] - MIN_GAP_PCT) * 80) + gap_bonus))
        confidence = max(60, confidence)

        if DRY_RUN:
            print(f"  [DRY] {direction:5s}-accel-300 {token:8s} conf={confidence:.0f}% "
                  f"gap={sig['gap_pct']:.3f}% growth={sig['gap_growth']:.3f}% "
                  f"bars_since_cross={sig['bars_since_cross']} [{source}]")
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=float(sig['gap_growth']),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=None,
                z_score_tier=None,
            )
            if sid:
                added += 1
                # Set cooldown: don't re-fire for COOLDOWN_BARS bars (~10 minutes)
                set_cooldown(token, direction, hours=COOLDOWN_BARS / 60.0)
                print(f"  {direction:5s}-accel-300 {token:8s} conf={confidence:.0f}% "
                      f"gap={sig['gap_pct']:.3f}% growth={sig['gap_growth']:.3f}% "
                      f"bars_since_cross={sig['bars_since_cross']} [{source}]")
        except Exception as e:
            print(f"[accel-300] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import init_db

    # Build token list from price_history (live tokens only)
    conn = sqlite3.connect(_PRICE_DB, timeout=10)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT token FROM price_history
        WHERE timestamp > ?
        ORDER BY token
    """, (int(time.time()) - 600,))
    tokens = [r[0] for r in c.fetchall()]
    conn.close()

    # Test on a few tokens
    test_tokens = {k: {'price': None} for k in tokens
                   if k in ('BTC', 'ETH', 'SOL', 'AVAX', 'LINK', 'ARB', 'XMR', 'SNX')}
    if not test_tokens:
        test_tokens = {k: {'price': None} for k in tokens[:10]}

    # Fetch latest prices
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

    mode = "DRY" if DRY_RUN else "LIVE"
    print(f"[accel-300] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_signals(prices)
    print(f"[accel-300] Done. {n} signals emitted.")
