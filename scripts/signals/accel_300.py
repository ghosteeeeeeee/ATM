# Migrated from ../accel_300_signals.py — see signals/__init__.py registry
#!/usr/bin/env python3
"""
accel_300_signals.py -- Persistent Gap Above EMA(300) Acceleration Signal.

LOG_FILE: /var/www/hermes/logs/signals.log
"""
import os

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)

def _log(msg):
    """Write to both stdout and signals.log."""
    import sys
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass

"""
Concept: price breaks above EMA300 (was below within last N bars), then
stays above for PERSISTENCE_BARS consecutive bars while the gap vs EMA300
is GROWING. The growing gap = accelerating momentum -- the move isn't fading.

This catches "slow breakouts" that gap_300 misses -- gap_300 fires on the
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
  - accel_300_long  : persistent above-EMA300 with growing gap -- momentum accelerating long
  - accel_300_short : persistent below-EMA300 with growing gap -- momentum accelerating short

Run:
    python3 accel_300_signals.py           # live scan
    python3 accel_300_signals.py --dry     # dry run (log only)
"""

import sys, os, sqlite3, time, datetime
from typing import Optional, List
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signal_schema import add_signal, get_cooldown, price_age_minutes

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'   # price_history -- live 1m prices

# ── Signal constants (from hermes_constants) ──────────────────────────────────
from hermes_constants import (
    ACCEL_300_PERIOD, ACCEL_300_LOOKBACK, ACCEL_300_PERSISTENCE_BARS,
    ACCEL_300_MIN_GAP_PCT, ACCEL_300_MIN_GAP_GROWTH, ACCEL_300_COOLDOWN_BARS,
    ACCEL_300_LOOKBACK_1M,
    ACCEL_300_MIN_GAP_PCT_LONG, ACCEL_300_MIN_GAP_PCT_SHORT,
    ACCEL_300_MIN_GAP_GROWTH_SHORT,
    ACCEL_300_STALE_BARS, ACCEL_300_STALE_BARS_SHORT,
    ACCEL_300_MARGINAL_ACCEL_BARS, ACCEL_300_BARS_UNKNOWN,
    ACCEL_300_BAR_GAP_THRESH_SEC,
)
# Alias local names for readability in detection logic
PERIOD          = ACCEL_300_PERIOD
LOOKBACK        = ACCEL_300_LOOKBACK
PERSISTENCE_BARS = ACCEL_300_PERSISTENCE_BARS
MIN_GAP_PCT     = ACCEL_300_MIN_GAP_PCT
MIN_GAP_GROWTH_PCT = ACCEL_300_MIN_GAP_GROWTH
COOLDOWN_BARS   = ACCEL_300_COOLDOWN_BARS
LOOKBACK_1M     = ACCEL_300_LOOKBACK_1M
STALE_BARS      = ACCEL_300_STALE_BARS
STALE_BARS_SHORT = ACCEL_300_STALE_BARS_SHORT
MARGINAL_ACCEL_BARS = ACCEL_300_MARGINAL_ACCEL_BARS
BARS_UNKNOWN     = ACCEL_300_BARS_UNKNOWN
BAR_GAP_THRESH_SEC = ACCEL_300_BAR_GAP_THRESH_SEC
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
# Data fetch -- LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int = LOOKBACK_1M) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.

    price_history is updated every minute with live prices -- the ONLY reliable
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

        # Bar-to-bar gap guard -- detect missing data
        bar_gaps = [rows[i][0] - rows[i-1][0] for i in range(1, len(rows))]
        if bar_gaps:
            mean_gap = sum(bar_gaps) / len(bar_gaps)
            variance = sum((g - mean_gap) ** 2 for g in bar_gaps) / len(bar_gaps)
            std_gap = variance ** 0.5
            threshold = max(BAR_GAP_THRESH_SEC, mean_gap + 3.0 * std_gap)
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
    from hermes_constants import (
        # Detection params (from top of file — originally hardcoded here)
        ACCEL_300_PERIOD, ACCEL_300_LOOKBACK, ACCEL_300_PERSISTENCE_BARS,
        ACCEL_300_MIN_GAP_PCT, ACCEL_300_MIN_GAP_GROWTH,
        # P0 gate constants
        ACCEL_300_STALE_BARS, ACCEL_300_STALE_LOOKBACK,
        ACCEL_300_MIN_GAP_EXPANSION,
        ACCEL_300_REGIME_SLOPE_PCT, ACCEL_300_SLOPE_WINDOW,
        ACCEL_300_STALE_GAP_DECAY_THRESHOLD,
        ACCEL_300_CHOP_CROSS_GAP_PCT, ACCEL_300_CHOP_EMA_ANGLE_PCT,
        ACCEL_300_CHOP_AVG_GAP_PCT, ACCEL_300_CHOP_LOOKBACK,
        ACCEL_300_CROSS_LOOKBACK,
        ACCEL_300_MARGINAL_ACCEL_BARS, ACCEL_300_BARS_UNKNOWN,
        ACCEL_300_BAR_GAP_THRESH_SEC,
    )
    # Alias short names for detection logic readability
    PERIOD           = ACCEL_300_PERIOD
    LOOKBACK         = ACCEL_300_LOOKBACK
    PERSISTENCE_BARS = ACCEL_300_PERSISTENCE_BARS
    MIN_GAP_PCT      = ACCEL_300_MIN_GAP_PCT
    MIN_GAP_GROWTH_PCT = ACCEL_300_MIN_GAP_GROWTH
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
            continue  # Never went below -- not a fresh breakout
        if current_below and not was_above_recently:
            continue  # Never went above -- not a fresh breakdown

        direction = 'LONG' if current_above else 'SHORT'

        # ── Condition 2: |gap| >= direction-specific MIN_GAP_PCT ───────────────
        # Per-direction thresholds: SHORT tighter (0.25) than LONG (0.20)
        # accel-300- has 40% WR vs 55% for accel-300+ — SHORT needs stronger confirmation
        min_gap_dir = ACCEL_300_MIN_GAP_PCT_SHORT if direction == 'SHORT' else ACCEL_300_MIN_GAP_PCT_LONG
        if abs(gap_now) < min_gap_dir:
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

        # ── Condition 4a: Average gap growth over PERSISTENCE_BARS window ─────────
        gap_then_idx = i - PERSISTENCE_BARS
        if gap_then_idx < 0 or gap_pcts[gap_then_idx] is None:
            continue

        gap_then = gap_pcts[gap_then_idx]
        avg_gap_growth = gap_now - gap_then

        # Per-direction gap growth: SHORT stricter (0.07) than LONG (0.05)
        # SHORT side gets more false breakouts that reverse — needs stronger growth
        min_gap_growth_dir = ACCEL_300_MIN_GAP_GROWTH_SHORT if direction == 'SHORT' else MIN_GAP_GROWTH_PCT
        if avg_gap_growth <= min_gap_growth_dir:
            continue  # Gap is not growing over the window -- stale signal

        # ── Condition 4b: MARGINAL ACCELERATION + TIMING ─────────────────────────
        # gap_now vs 1 bar ago must show INCREASING momentum, not just steady growth.
        # This catches early acceleration (good) vs late-stage extension (peak).
        #
        # TIMING FIX (2026-05-10): Fire EARLY when bars_since_cross <= 3 (near breakout).
        # Only enforce strict marginal acceleration when bars_since_cross > 3.
        # This solves the "firing too late at the peak" problem — entries close to
        # the EMA cross (bars=0,1,2) are the most profitable because the move just started.
        # Entries that have been above EMA for 10+ bars without our signal are stale.
        # ── Find cross bar — two-pass search ───────────────────────────────────────
        # Pass 1: primary window (ACCEL_300_CROSS_LOOKBACK bars before signal bar)
        # Pass 2: full fallback to index 0 (catches crosses far in the past)
        cross_bar = None
        for j in range(i - ACCEL_300_CROSS_LOOKBACK, i + 1):
            if j < 0 or gap_pcts[j] is None or ema300[j] is None:
                continue
            if direction == 'LONG' and closes[j] > ema300[j]:
                if j > 0 and ema300[j-1] is not None and closes[j-1] <= ema300[j-1]:
                    cross_bar = j
                    break
            if direction == 'SHORT' and closes[j] < ema300[j]:
                if j > 0 and ema300[j-1] is not None and closes[j-1] >= ema300[j-1]:
                    cross_bar = j
                    break
        # Pass 2: full fallback — search from signal bar back to earliest bar
        if cross_bar is None:
            for j in range(i - 1, -1, -1):
                if j < 0 or gap_pcts[j] is None or ema300[j] is None:
                    continue
                if direction == 'LONG' and closes[j] > ema300[j]:
                    if j > 0 and ema300[j-1] is not None and closes[j-1] <= ema300[j-1]:
                        cross_bar = j
                        break
                if direction == 'SHORT' and closes[j] < ema300[j]:
                    if j > 0 and ema300[j-1] is not None and closes[j-1] >= ema300[j-1]:
                        cross_bar = j
                        break

        bars_since_cross = i - cross_bar if cross_bar is not None else BARS_UNKNOWN

        # ── Gap expansion gate — price must be farther from EMA than at cross ───────
        # Prevents signals where price barely crossed EMA and is already fading back
        if cross_bar is not None and gap_pcts[cross_bar] is not None:
            gap_at_cross = gap_pcts[cross_bar]
            if direction == 'LONG' and gap_now < gap_at_cross - ACCEL_300_MIN_GAP_EXPANSION:
                continue  # gap contracting back toward EMA — stale
            if direction == 'SHORT' and gap_now > gap_at_cross + ACCEL_300_MIN_GAP_EXPANSION:
                continue  # gap contracting (less negative) back toward EMA — stale

        # Must have confirmed the cross (at least 1 bar has closed since the cross)
        if bars_since_cross < 1:
            continue

        # Too stale — price has been running without us for too long
        # Per-direction stale bars: SHORT stricter (55) than LONG (60)
        max_stale = STALE_BARS_SHORT if direction == 'SHORT' else STALE_BARS
        if bars_since_cross >= max_stale:
            continue

        # ── STALE GATE (FIX 2026-06-08): bars_since_cross is measured from
        # detection bar i, not from the latest bar. A signal can fire at i=344
        # (13:37) with bars_since_cross=1 (cross was at i-1), passing the stale
        # gate, but from the latest bar (18:02) the cross is 354 bars old.
        # Add absolute stale gate: detection bar must be within N bars of latest.
        bars_from_latest = len(closes) - 1 - i
        if bars_from_latest > ACCEL_300_STALE_LOOKBACK:
            continue

        # For bars 0-MARGINAL_ACCEL_BARS: fire on gap_growth alone (near the breakout, momentum is fresh)
        # For bars MARGINAL_ACCEL_BARS+: require marginal acceleration check too
        if bars_since_cross > MARGINAL_ACCEL_BARS:
            gap_1_idx = i - 1
            gap_2_idx = i - 2
            if gap_1_idx < 0 or gap_pcts[gap_1_idx] is None:
                continue
            if gap_2_idx < 0 or gap_pcts[gap_2_idx] is None:
                continue
            delta_last  = gap_pcts[i]      - gap_pcts[gap_1_idx]
            delta_prev  = gap_pcts[gap_1_idx] - gap_pcts[gap_2_idx]
            if direction == 'LONG' and delta_last <= delta_prev:
                continue
            if direction == 'SHORT' and delta_last >= delta_prev:
                continue

        # ── Regime slope check ─────────────────────────────────────────────────────
        # Market must be trending in the signal's direction (prevents trading chop)
        if len(closes) >= i + ACCEL_300_SLOPE_WINDOW:
            slope_chunk = closes[i:i + ACCEL_300_SLOPE_WINDOW]
            n_s = len(slope_chunk)
            # Simple linear regression: slope = sum((x-x̄)(y-ȳ)) / sum((x-x̄)²)
            x_mean = (n_s - 1) / 2.0
            y_mean = sum(slope_chunk) / n_s
            num = sum((j - x_mean) * (slope_chunk[j] - y_mean) for j in range(n_s))
            den = sum((j - x_mean) ** 2 for j in range(n_s))
            if den > 0:
                slope = num / den
                pct_slope = slope / y_mean * 100.0 if y_mean != 0 else 0.0
                if direction == 'LONG' and pct_slope <= ACCEL_300_REGIME_SLOPE_PCT:
                    continue  # market flat or falling — don't LONG
                if direction == 'SHORT' and pct_slope >= -ACCEL_300_REGIME_SLOPE_PCT:
                    continue  # market flat or rising — don't SHORT

        # ── Stale gap decay check ──────────────────────────────────────────────────
        # Newest bar's gap must be >= threshold fraction of signal bar's gap
        # (blocks stale pullback signals where gap collapsed after the signal fired)
        newest_idx = len(closes) - 2
        if newest_idx > i and gap_pcts[newest_idx] is not None:
            signal_gap = abs(gap_now)
            newest_gap = abs(gap_pcts[newest_idx])
            if signal_gap > 0 and newest_gap < signal_gap * ACCEL_300_STALE_GAP_DECAY_THRESHOLD:
                continue  # gap decayed — stale pullback, block

        # ── Chop filter — reject choppy / ranging markets ─────────────────────────
        # Applied at the cross bar to ensure the signal crossed through a meaningful move
        if cross_bar is not None and cross_bar >= ACCEL_300_CHOP_LOOKBACK:
            #1. Gap at cross bar must be meaningful
            cross_gap = gap_pcts[cross_bar]
            if cross_gap is None:
                continue
            if direction == 'LONG' and cross_gap < ACCEL_300_CHOP_CROSS_GAP_PCT:
                continue
            if direction == 'SHORT' and cross_gap > -ACCEL_300_CHOP_CROSS_GAP_PCT:
                continue

            # 2. EMA angle at cross bar
            if ema300[cross_bar] is not None and ema300[cross_bar - ACCEL_300_CHOP_LOOKBACK] is not None:
                dy = ema300[cross_bar] - ema300[cross_bar - ACCEL_300_CHOP_LOOKBACK]
                angle_pct = (dy / ema300[cross_bar - ACCEL_300_CHOP_LOOKBACK]) * 100.0 if ema300[cross_bar - ACCEL_300_CHOP_LOOKBACK] != 0 else 0.0
                if abs(angle_pct) < ACCEL_300_CHOP_EMA_ANGLE_PCT:
                    continue

            # 3. Average gap magnitude over the bars leading up to cross bar
            gap_slice = [abs(g) for g in gap_pcts[cross_bar - ACCEL_300_CHOP_LOOKBACK:cross_bar] if g is not None]
            if gap_slice:
                avg_gap = sum(gap_slice) / len(gap_slice)
                if avg_gap < ACCEL_300_CHOP_AVG_GAP_PCT:
                    continue

        return {
            'direction': direction,
            'gap_pct': round(gap_now, 4),
            'gap_growth': round(avg_gap_growth, 4),
            'gap_then': round(gap_then, 4),
            'bars_since_cross': bars_since_cross,
            'price': price,
        }

    return None


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_accel_300_signals(prices_dict: dict) -> int:
    from hermes_constants import ACCEL_300_ENABLED, ACCEL_300_TOKEN_ALLOWLIST
    if not ACCEL_300_ENABLED:
        return 0
    """
    Scan tokens for accel_300 signals.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    from signal_schema import add_signal, get_cooldown, price_age_minutes
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
        # ── Token allowlist: only fire on tokens with >=50% historical WR ─────────
        if ACCEL_300_TOKEN_ALLOWLIST and token.upper() not in ACCEL_300_TOKEN_ALLOWLIST:
            continue
        if price_age_minutes(token) > 10:
            continue

        prices = _get_1m_prices(token, lookback=LOOKBACK_1M)
        if not prices or len(prices) < PERIOD + LOOKBACK + PERSISTENCE_BARS + 5:
            continue

        sig = detect_accel_300(token, prices)
        if sig is None:
            continue

        direction = sig['direction']
        if get_cooldown(token, direction=direction):
            continue

        # ── Per-direction kill-switch ─────────────────────────────────────────
        from hermes_constants import ACCEL_300_PLUS_ENABLED, ACCEL_300_MINUS_ENABLED
        if direction == 'LONG' and not ACCEL_300_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ACCEL_300_MINUS_ENABLED:
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Confidence: base on gap strength + gap growth
        # MIN_GAP_PCT=0.10 → base 65, larger gap → up to 70 (cap lowered 2026-05-12 to reduce LONG bias)
        # Bonus for strong gap growth (requires growth > 0.05% to earn bonus)
        gap_bonus = max(0, sig['gap_growth'] - 0.05) * 200  # max ~20 for 0.15%+ growth
        confidence = int(min(70, 65 + max(0, (sig['gap_pct'] - MIN_GAP_PCT) * 80) + gap_bonus))
        confidence = max(60, confidence)

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-accel-300 {token:8s} conf={confidence:.0f}% "
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
                _log(f"  {direction:5s}-accel-300 {token:8s} conf={confidence:.0f}% "
                      f"gap={sig['gap_pct']:.3f}% growth={sig['gap_growth']:.3f}% "
                      f"bars_since_cross={sig['bars_since_cross']} [{source}]")
        except Exception as e:
            print(f"[accel-300] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point — used by signals_runner via getattr(mod, 'run')
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

    # Build prices dict for the scanner
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
        prices[row[0]] = {'price': row[1]}
    conn.close()

    mode = "DRY" if DRY_RUN else "LIVE"
    print(f"[accel-300] Testing on {len(prices)} tokens ({mode} mode)...")
    init_db()
    n = scan_accel_300_signals(prices)
    print(f"[accel-300] Done. {n} signals emitted.")

# ═══════════════════════════════════════════════════════════════════════════════
# signals_runner entry point — called by signals/__init__.py via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

def run(prices_dict=None):
    """Entry point for signals_runner.

    signals_runner calls this as: fn(prices)
    where prices = get_all_latest_prices() = {token: {'price': float}}

    The scanner handles all guards internally (allowlist, cooldown, blacklist, etc.)
    """
    if prices_dict is None:
        from signal_schema import get_all_latest_prices
        prices_dict = get_all_latest_prices()
    return scan_accel_300_signals(prices_dict)
