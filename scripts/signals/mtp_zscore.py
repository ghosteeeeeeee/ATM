#!/usr/bin/env python3
"""
mtp_zscore.py — Multi-Timeperiod Z-Score Signal (pipeline-integrated).

Detects directional trend via simultaneous z-score analysis across 3 lookback
periods: short (50-bar), medium (100-bar), long (150-bar).

Philosophy: TREND-FOLLOWING only. Ride momentum, no mean-reversion, no
divergence gate. abs(z) used ONLY for bounds comparison; direction always
from sign (z>0=LONG, z<0=SHORT).

Fire condition: ALL 3/3 periods must agree on direction AND each period's
|z| must fall within its Z_MIN/Z_MAX bounds. If any period fails bounds or
returns None → no signal.

Architecture:
  price_history (1m closes, fresh every minute) → per-period z-score computation
  → signal_schema.add_signal() → signals_hermes_runtime.db
  → signal_compactor → hotset.json → guardian → HL

Signal types:
  - mtp_zscore_long  : all 3 periods agree upward → LONG  (mtp-zscore+)
  - mtp_zscore_short : all 3 periods agree downward → SHORT (mtp-zscore-)

Run:
    python3 signals/mtp_zscore.py           # live scan
    python3 signals/mtp_zscore.py --dry     # dry run (log only)
"""

import os
import sys
import statistics
import sqlite3
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Also add parent (scripts/) so signal_schema/hermes_constants are found when
# running as __main__ directly from signals/ directory.
# When imported as a module via signals/__init__.py this is already on path.
_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from signal_schema import add_signal, get_cooldown, price_age_minutes
from signal_gen import MIN_TRADE_INTERVAL_MINUTES
from hermes_constants import (
    MTP_ZSCORE_ENABLED,
    MTP_ZSCORE_PLUS_ENABLED,
    MTP_ZSCORE_MINUS_ENABLED,
    MTP_ZSCORE_LB_SHORT,
    MTP_ZSCORE_LB_MID,
    MTP_ZSCORE_LB_LONG,
    Z_SHORT_Z_MIN,  Z_SHORT_Z_MAX,
    Z_MID_Z_MIN,    Z_MID_Z_MAX,
    Z_LONG_Z_MIN,   Z_LONG_Z_MAX,
    MTP_ZSCORE_MIN_AGREE,
    MTP_ZSCORE_BASE_CONF,
    MTP_ZSCORE_CONF_BONUS,
    MTP_ZSCORE_COOLDOWN_BARS,
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_RUNTIME_DB = '/root/.hermes/data/signals_hermes_runtime.db'
_PRICE_DB   = '/root/.hermes/data/signals_hermes.db'   # price_history — live 1m prices

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
SIGNAL_TYPE_LONG  = 'mtp_zscore_long'
SIGNAL_TYPE_SHORT = 'mtp_zscore_short'
SOURCE_LONG       = 'mtp-zscore+'
SOURCE_SHORT      = 'mtp-zscore-'


# ═══════════════════════════════════════════════════════════════════════════════
# Core z-score computation (identical to zscore_pump)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_zscore(values):
    """Compute z-score of the last value in the series.
    Returns None if stddev==0 (flat series) or insufficient data."""
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return None
    return (values[-1] - mean) / std


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
            _log(f"  [mtp-zscore] {token}: stale price_history (last ts {most_recent_ts}), skipping")
            return []

        return [{'timestamp': r[0], 'price': r[1]} for r in rows]

    except Exception as e:
        _log(f"  [mtp-zscore] price_history error for {token}: {e}")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Detection — multi-period z-score analysis
# ═══════════════════════════════════════════════════════════════════════════════

def detect_mtp_zscore(token: str, prices: list) -> dict | None:
    """
    Detect multi-timeperiod z-score signal given pre-fetched price history.

    Fire when ALL 3/3 periods (50/100/150-bar) agree on direction AND each
    period's |z| falls within its Z_MIN/Z_MAX bounds.

    Direction: z > 0 → LONG, z < 0 → SHORT (abs(z) is for bounds ONLY)

    Returns dict with direction, z_score (avg of 3 periods), per-period z values,
    lookbacks, and price, or None if not all 3/3 agree.
    """
    if not prices:
        return None

    # Need enough bars for the longest lookback + buffer
    max_lookback = MTP_ZSCORE_LB_LONG
    if len(prices) < max_lookback + 2:
        return None

    closes = [p['price'] for p in prices]
    latest_price = closes[-1]

    if latest_price <= 0:
        return None

    # ── Per-period z-score computation ─────────────────────────────────────────
    periods = [
        {'name': 'short', 'lookback': MTP_ZSCORE_LB_SHORT,  'z_min': Z_SHORT_Z_MIN,  'z_max': Z_SHORT_Z_MAX},
        {'name': 'mid',   'lookback': MTP_ZSCORE_LB_MID,   'z_min': Z_MID_Z_MIN,    'z_max': Z_MID_Z_MAX},
        {'name': 'long',  'lookback': MTP_ZSCORE_LB_LONG,  'z_min': Z_LONG_Z_MIN,   'z_max': Z_LONG_Z_MAX},
    ]

    vote_count = 0
    period_results = []

    for p in periods:
        chunk = closes[-p['lookback']:]
        z = compute_zscore(chunk)

        # Reject period if stddev==0 (flat series) → cannot vote
        if z is None:
            period_results.append({'name': p['name'], 'z': None, 'vote': None})
            continue

        z_abs = abs(z)

        # Reject if |z| below Z_MIN (not meaningful enough for this period)
        if z_abs < p['z_min']:
            period_results.append({'name': p['name'], 'z': z, 'vote': None})
            continue

        # Reject if |z| above Z_MAX (too extended for this period's trend)
        if z_abs > p['z_max']:
            period_results.append({'name': p['name'], 'z': z, 'vote': None})
            continue

        # Period passes bounds → vote
        vote = 'LONG' if z > 0 else 'SHORT'
        period_results.append({'name': p['name'], 'z': z, 'vote': vote})
        vote_count += 1

    # ── Min-agree gate: ALL 3/3 must vote same direction ─────────────────────
    if vote_count < MTP_ZSCORE_MIN_AGREE:
        return None

    # Check all voted periods agree on direction
    votes = [r['vote'] for r in period_results if r['vote'] is not None]
    if not votes:
        return None
    first_vote = votes[0]
    if not all(v == first_vote for v in votes):
        # Direction disagreement among voting periods → no signal
        return None

    direction = first_vote

    # Collect z-scores for averaging and JSON tier
    z_values = [r['z'] for r in period_results if r['vote'] is not None]
    z_avg = statistics.mean(z_values)

    z_short = next((r['z'] for r in period_results if r['name'] == 'short'), None)
    z_mid   = next((r['z'] for r in period_results if r['name'] == 'mid'),   None)
    z_long  = next((r['z'] for r in period_results if r['name'] == 'long'),  None)

    return {
        'token': token.upper(),
        'direction': direction,
        'z_score': round(z_avg, 3),
        'z_short': round(z_short, 3) if z_short is not None else None,
        'z_mid':   round(z_mid,   3) if z_mid   is not None else None,
        'z_long':  round(z_long,  3) if z_long  is not None else None,
        'entry_price': latest_price,
        'price': latest_price,
        'timestamp': int(time.time()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Scanner
# ═══════════════════════════════════════════════════════════════════════════════

def scan_mtp_zscore_signals(prices_dict: dict) -> int:
    """
    Scan tokens for multi-timeperiod z-score momentum signals.

    All guards (blacklists, open positions, cooldowns, price age) applied here.
    Does NOT call HL API — reads local price_history only.

    Args:
        prices_dict: token -> {'price': float, ...} from signal_gen

    Returns:
        Number of signals written to DB.
    """
    if not MTP_ZSCORE_ENABLED:
        return 0

    from position_manager import get_open_positions as _get_open_pos
    from signal_gen import (
        recent_trade_exists, is_delisted, SHORT_BLACKLIST, LONG_BLACKLIST,
    )

    open_pos = {p['token']: p['direction'] for p in _get_open_pos()}
    added = 0

    for token, data in prices_dict.items():
        if token.startswith('@'):
            continue
        price = data.get('price')
        if not price or price <= 0:
            continue

        # ── Pre-filter guards ───────────────────────────────────────────────
        if token.upper() in open_pos:
            continue
        if recent_trade_exists(token, MIN_TRADE_INTERVAL_MINUTES):
            continue
        if is_delisted(token.upper()):
            continue

        # SHORT_BLACKLIST blocks ALL directions for a token
        if token.upper() in SHORT_BLACKLIST:
            continue

        # Scanner-level price age check (secondary guard)
        if price_age_minutes(token) > 10:
            continue

        # ── Fetch price history ──────────────────────────────────────────────
        # Need max lookback + buffer for the longest period
        lookback = MTP_ZSCORE_LB_LONG + 50   # 150+50 = 200 bars
        prices = _get_1m_prices(token, lookback=lookback)
        if not prices or len(prices) < MTP_ZSCORE_LB_LONG + 2:
            continue

        # ── Detect ──────────────────────────────────────────────────────────
        sig = detect_mtp_zscore(token, prices)
        if sig is None:
            continue

        direction = sig['direction']

        # LONG_BLACKLIST — only checked for LONG direction
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            continue

        # Per-direction kill-switch
        if direction == 'LONG' and not MTP_ZSCORE_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not MTP_ZSCORE_MINUS_ENABLED:
            continue

        # Cooldown check
        if get_cooldown(token, direction=direction):
            continue

        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source   = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT

        # Confidence: base + tier bonus (reserved for future 2/3 vs 3/3 differentiation)
        confidence = MTP_ZSCORE_BASE_CONF + MTP_ZSCORE_CONF_BONUS

        if DRY_RUN:
            _log(f"  [DRY] {direction:5s}-mtp-zscore {token:8s} "
                 f"z={sig['z_score']:+.3f} (S:{sig['z_short']:+.2f} M:{sig['z_mid']:+.2f} L:{sig['z_long']:+.2f}) "
                 f"conf={confidence:.0f}% [{source}]")
            continue

        # ── Write signal ────────────────────────────────────────────────────
        try:
            z_score_tier = json.dumps({
                'z_short': sig['z_short'],
                'z_mid':   sig['z_mid'],
                'z_long':  sig['z_long'],
                'agree_count': 3,   # always 3 at fire (3/3 agree), future-proofs for 2/3 mode
            })

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
                z_score_tier=z_score_tier,
            )
            if sid:
                added += 1
                # Set cooldown: don't re-fire for MTP_ZSCORE_COOLDOWN_BARS bars (~20 min)
                from signal_gen import set_cooldown
                set_cooldown(token, direction, hours=int(MTP_ZSCORE_COOLDOWN_BARS / 60.0))
                _log(f"  {direction:5s}-mtp-zscore {token:8s} "
                     f"z={sig['z_score']:+.3f} (S:{sig['z_short']:+.2f} M:{sig['z_mid']:+.2f} L:{sig['z_long']:+.2f}) "
                     f"conf={confidence:.0f}% [{source}]")
        except Exception as e:
            _log(f"[mtp-zscore] add_signal error for {token}: {e}")

    return added


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry point — used by signals_runner via getattr(mod, 'run')
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys as _sys
    import os as _os
    # Add scripts/ parent (for signal_schema, hermes_constants) to path
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

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
        print(f"[mtp-zscore] Failed to load prices: {e}")

    n = scan_mtp_zscore_signals(prices)
    print(f'mtp_zscore: {n} signals emitted')