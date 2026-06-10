# Migrated from ../zscore_pump_hunter.py — standalone executor converted to pipeline signal
# See signals/__init__.py registry
#!/usr/bin/env python3
"""
zscore_pump.py — Z-Score Momentum Signal (pipeline-integrated).

Detects directional momentum via z-score of recent closes.
  - +z > threshold  →  strong upward momentum → LONG  (zscore-pump+)
  - -z < -threshold →  strong downward momentum → SHORT (zscore-pump-)

Philosophy: momentum, NOT mean-reversion. Ride the move, don't fade it.

Architecture:
  price_history (1m closes, fresh every minute) → z-score computation
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal types:
  - zscore_pump_long  : z > threshold — upward momentum riding
  - zscore_pump_short : z < -threshold — downward momentum riding

Run:
    python3 signals/zscore_pump.py           # live scan
    python3 signals/zscore_pump.py --dry     # dry run (log only)
"""

import os
import sys
import statistics
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from signal_schema import add_signal, get_cooldown, price_age_minutes
from signal_gen import MIN_TRADE_INTERVAL_MINUTES
from hermes_constants import (
    ZSCORE_PUMP_NEW_ENABLED,
    ZSCORE_PUMP_PLUS_ENABLED,
    ZSCORE_PUMP_MINUS_ENABLED,
    ZSCORE_PUMP_LOOKBACK,
    ZSCORE_PUMP_THRESHOLD,
    ZSCORE_PUMP_COOLDOWN_BARS,
    ZSCORE_PUMP_MIN_SIGNALS_FOR_TUNED,
    ZSCORE_PUMP_USE_TUNER,
    ZSCORE_PUMP_DIVERGENCE_ENABLED,
    ZSCORE_PUMP_DIVERGENCE_LOOKBACK,
    ZSCORE_PUMP_DIVERGENCE_EXTREME_Z,
    ZSCORE_PUMP_DIVERGENCE_VEL_THD,
    ZSCORE_PUMP_DIVERGENCE_BARS,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'   # price_history — live 1m prices
_TUNER_DB   = '/root/.hermes/data/zscore_momentum_tuner.db'

# ── Logging ───────────────────────────────────────────────────────────────────
SIGNAL_LOG = '/var/www/hermes/logs/signals.log'
os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)

def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass

DRY_RUN = '--dry' in sys.argv

# Signal type/source names
SIGNAL_TYPE_LONG  = 'zscore_pump_long'
SIGNAL_TYPE_SHORT = 'zscore_pump_short'
SOURCE_LONG       = 'zscore-pump+'
SOURCE_SHORT      = 'zscore-pump-'


# ═══════════════════════════════════════════════════════════════════════════════
# Core z-score computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_zscore(values):
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return None
    return (values[-1] - mean) / std


def _check_divergence(prices: list, lookback: int, direction: str) -> bool:
    """
    Detect negative divergence: z-score was extremely elevated then CRASHING
    while price made marginal new highs = imminent reversal trap.

    Uses a SHORT lookback (ZSCORE_PUMP_DIVERGENCE_LOOKBACK, default 30) for the
    spot momentum check, independent of the signal's longer trend lookback.

    LONG:  catches the VVV pattern — z spiked to +3.5+ then collapsed for
           5+ bars while price made marginal new highs = reversal trap.
    SHORT: catches the blow-off bottom — z crashed to -3.5+ then recovering
           for 5+ bars = reversal imminent, not continuation.

    Returns True if divergence DETECTED (signal should be REJECTED).
    Returns False if no divergence (signal passes).
    """
    if not ZSCORE_PUMP_DIVERGENCE_ENABLED:
        return False

    spot_lookback = ZSCORE_PUMP_DIVERGENCE_LOOKBACK
    min_required = spot_lookback + ZSCORE_PUMP_DIVERGENCE_BARS + 2

    if len(prices) < min_required:
        return False

    closes = [p['price'] for p in prices]

    # Compute spot z-score series using the SHORT divergence lookback
    recent_zs = []
    for i in range(spot_lookback, len(closes) + 1):
        chunk = closes[i - spot_lookback:i]
        z = compute_zscore(chunk)
        recent_zs.append(z)

    if not recent_zs or None in recent_zs:
        return False

    # Check: was z above extreme threshold recently?
    peak_z = max(recent_zs)
    nadir_z = min(recent_zs)

    # ── LONG divergence ─────────────────────────────────────────────────────
    # Catches: z=+4.16 peak → dropping for 8+ bars while price makes new highs
    if direction == 'LONG' and peak_z >= ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
        peak_idx = max(idx for idx, z in enumerate(recent_zs) if z == peak_z)
        bars_since_peak = len(recent_zs) - 1 - peak_idx
        if bars_since_peak >= ZSCORE_PUMP_DIVERGENCE_BARS:
            neg_vel_bars = 0
            for i in range(peak_idx + 1, len(recent_zs)):
                vel = recent_zs[i] - recent_zs[i - 1]
                if vel < ZSCORE_PUMP_DIVERGENCE_VEL_THD:
                    neg_vel_bars += 1
                elif vel > 0:
                    neg_vel_bars = 0
            if neg_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
                return True  # LONG divergence — REJECT

    # ── SHORT divergence ────────────────────────────────────────────────────
    # Pattern: z was extremely negative (blow-off bottom), now recovering
    # Catches: z=-5.77 crash → turning back up = reversal, not continuation
    # This is what killed STRK and PROVE
    if direction == 'SHORT' and nadir_z <= -ZSCORE_PUMP_DIVERGENCE_EXTREME_Z:
        nadir_idx = min(idx for idx, z in enumerate(recent_zs) if z == nadir_z)
        bars_since_nadir = len(recent_zs) - 1 - nadir_idx
        if bars_since_nadir >= ZSCORE_PUMP_DIVERGENCE_BARS:
            pos_vel_bars = 0
            for i in range(nadir_idx + 1, len(recent_zs)):
                vel = recent_zs[i] - recent_zs[i - 1]
                if vel > -ZSCORE_PUMP_DIVERGENCE_VEL_THD:  # z rising (less negative)
                    pos_vel_bars += 1
                elif vel < 0:
                    pos_vel_bars = 0  # reset if z keeps falling (still crashing)
            if pos_vel_bars >= ZSCORE_PUMP_DIVERGENCE_BARS:
                return True  # SHORT divergence — REJECT

    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Tuner params cache (loaded once per process)
# ═══════════════════════════════════════════════════════════════════════════════

_cached_token_params = None

def _load_tuner_params():
    global _cached_token_params
    if _cached_token_params is not None:
        return _cached_token_params
    try:
        conn = sqlite3.connect(_TUNER_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT token, lookback, threshold, win_rate, signal_count
            FROM token_best_zscore_config
        """)
        rows = cur.fetchall()
        conn.close()
        _cached_token_params = {
            r[0]: {'lookback': r[1], 'threshold': r[2], 'win_rate': r[3], 'signal_count': r[4]}
            for r in rows
        }
        return _cached_token_params
    except Exception:
        _cached_token_params = {}
        return _cached_token_params


# ═══════════════════════════════════════════════════════════════════════════════
# Data fetch — LIVE prices from price_history (signals_hermes.db)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_1m_prices(token: str, lookback: int) -> list:
    """Fetch 1m close prices from price_history (signals_hermes.db), oldest first.
    Timestamps in SECONDS (Unix time).
    Returns list of {timestamp, price} dicts, oldest first.
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
            _log(f"  [zscore-pump] {token}: stale price_history (last ts {most_recent_ts}), skipping")
            return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        _log(f"  [zscore-pump] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Detection
# ═══════════════════════════════════════════════════════════════════════════════

def detect_zscore_pump(token: str, prices: list, lookback: int, threshold: float) -> dict | None:
    """
    Detect z-score momentum signal given pre-fetched price history.

    Fire when:
      - |z_score| > threshold
      - z > 0 → LONG
      - z < 0 → SHORT

    Returns dict with direction, z_score, lookback, threshold, price, or None.
    """
    if not prices or len(prices) < lookback + 2:
        return None

    closes = [p['price'] for p in prices]
    latest_price = closes[-1]

    if latest_price <= 0:
        return None

    chunk = closes[-lookback:]
    z = compute_zscore(chunk)
    if z is None:
        return None

    if abs(z) < threshold:
        return None

    # Direction: positive z = upward momentum → LONG, negative z = downward momentum → SHORT
    direction = 'LONG' if z > 0 else 'SHORT'

    # ── Divergence gate ───────────────────────────────────────────────────────
    # Reject if z was extremely elevated then crashing (negative divergence).
    # This catches the VVV pattern: z=+4.16 peak then collapsing for 8+ bars
    # while price makes marginal new highs = imminent reversal trap.
    #
    # The caller passes the FULL history window (2x lookback), so we examine
    # ALL of it — not just the last N bars. The extreme at bar ~115 (VVV spike
    # to $14.138) was 23 bars before the last-25-bar window would start.
    if ZSCORE_PUMP_DIVERGENCE_ENABLED and len(prices) >= ZSCORE_PUMP_DIVERGENCE_LOOKBACK + ZSCORE_PUMP_DIVERGENCE_BARS + 2:
        # Pass the full wide window; _check_divergence examines ALL of it
        if _check_divergence(prices, lookback, direction):
            _log(f"  [zscore-pump] {token}: REJECTED — negative divergence detected "
                 f"(z={z:.3f}, was extreme then collapsing)")
            return None

    return {
        'token': token.upper(),
        'direction': direction,
        'z_score': round(z, 3),
        'lookback': lookback,
        'threshold': threshold,
        'entry_price': latest_price,
        'price': latest_price,
        'timestamp': int(time.time()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_zscore_pump_signals(prices_dict: dict) -> int:
    """
    Scan tokens for z-score momentum signals.

    All guards (blacklists, open positions, cooldowns, price age) must be
    applied by the caller before passing prices_dict here.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    if not ZSCORE_PUMP_NEW_ENABLED:
        return 0

    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import (
        recent_trade_exists, is_delisted, SHORT_BLACKLIST, LONG_BLACKLIST,
    )

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    token_params = _load_tuner_params()
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

        # Blacklist checks
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Price age check
        if price_age_minutes(token) > 10:
            continue

        # ── Resolve per-token lookback + threshold ─────────────────────────────
        # ZSCORE_PUMP_USE_TUNER=False → always use hermes_constants defaults
        if not ZSCORE_PUMP_USE_TUNER:
            lookback = ZSCORE_PUMP_LOOKBACK
            threshold = ZSCORE_PUMP_THRESHOLD
            confidence = 80.0
        else:
            p = token_params.get(token.upper())
            tok_signal_count = p.get('signal_count', 0) if p else 0

            if p is None or tok_signal_count < ZSCORE_PUMP_MIN_SIGNALS_FOR_TUNED:
                lookback = ZSCORE_PUMP_LOOKBACK
                threshold = ZSCORE_PUMP_THRESHOLD
                confidence = 80.0
            else:
                lookback = p.get('lookback', ZSCORE_PUMP_LOOKBACK)
                threshold = p.get('threshold', ZSCORE_PUMP_THRESHOLD)
                wr = p.get('win_rate', 50.0)
                confidence = min(95.0, max(80.0, wr))

        # Fetch enough bars for the lookback window
        prices = _get_1m_prices(token, lookback=lookback + 50)
        if not prices or len(prices) < lookback + 2:
            continue

        sig = detect_zscore_pump(token, prices, lookback, threshold)
        if sig is None:
            continue

        direction = sig['direction']

        # LONG_BLACKLIST — only checked for LONG direction
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue

        # Per-direction kill-switch
        if direction == 'LONG' and not ZSCORE_PUMP_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not ZSCORE_PUMP_MINUS_ENABLED:
            continue

        # Cooldown check
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Confidence: stronger z = higher confidence, capped at 95
        z_abs = abs(sig['z_score'])
        conf_bonus = min(15, (z_abs - threshold) * 5)
        confidence = int(min(95, max(confidence, confidence + conf_bonus)))

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-zscore-pump {token:8s} z={sig['z_score']:+.3f} "
                 f"conf={confidence:.0f}% lookback={lookback} [{source}]")
            continue

        try:
            sid = add_signal(
                token=token.upper(),
                direction=direction,
                signal_type=sig_type,
                source=source,
                confidence=confidence,
                value=float(sig['z_score']),
                price=price,
                exchange='hyperliquid',
                timeframe='1m',
                z_score=sig['z_score'],
                z_score_tier=None,
            )
            if sid:
                added += 1
                # Set cooldown: don't re-fire for COOLDOWN_BARS bars (~10 minutes)
                from signal_gen import set_cooldown
                set_cooldown(token, direction, hours=ZSCORE_PUMP_COOLDOWN_BARS / 60.0)
                _log(f"  {direction:5s}-zscore-pump {token:8s} z={sig['z_score']:+.3f} "
                     f"conf={confidence:.0f}% lookback={lookback} [{source}]")
        except Exception as e:
            _log(f"[zscore-pump] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point — used by signals_runner via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from signal_schema import init_db
    init_db()

    # Build a minimal prices_dict from price_history for standalone run
    prices = {}
    try:
        conn = sqlite3.connect('/root/.hermes/data/signals_hermes.db', timeout=10)
        c = conn.cursor()
        c.execute("""
            SELECT token, price, timestamp FROM price_history ph1
            WHERE timestamp = (
                SELECT MAX(timestamp) FROM price_history ph2 WHERE ph2.token = ph1.token
            )
        """)
        rows = c.fetchall()
        conn.close()
        for token, price, ts in rows:
            prices[token] = {'price': price}
    except Exception as e:
        print(f"[zscore-pump] Failed to load prices: {e}")

    n = scan_zscore_pump_signals(prices)
    print(f'zscore_pump: {n} signals emitted')