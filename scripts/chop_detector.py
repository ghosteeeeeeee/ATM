"""
chop_detector.py — Detect chop/transitions and gate signal execution.

Combines 4 existing systems to classify market regime:
  1. Market phase (market_phase_gate.py) — defensive/range = chop
  2. Volatility regime (volatility_gate_v2.py) — FLAT = chop
  3. Directional outcome (signal_compactor.py) — WR degradation = chop
  4. BTC momentum — flat/low = chop

Regime classification:
  TREND: momentum signals allowed, mean-reversion allowed
  CHOP:  momentum signals BLOCKED, mean-reversion ALLOWED
  CRISIS: all signals BLOCKed, tighten stops

Why this matters:
  During transitions, momentum signals (ema300-dip, accel-300) fail and their
  winrates collapse. The CEO kills them. When the next trend starts, the system
  has to rebuild its signal roster from scratch. By detecting chop and blocking
  momentum signals, we preserve their winrates for the next trend.

Usage:
  from chop_detector import get_regime, should_trade_signal
  regime = get_regime()
  if not should_trade_signal('ema300-dip', regime):
      # Block this signal — it's a momentum signal in chop
      pass
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import HERMES_DATA, CANDLES_DB
import sqlite3


# ── Cache ─────────────────────────────────────────────────────────────────────
_regime_cache = None
_regime_cache_time = 0


# ── Signal Family Classification ──────────────────────────────────────────────
# Which signals are momentum (fail in chop) vs mean-reversion (thrive in chop)?

MOMENTUM_FAMILIES = {
    'Momentum', 'Accelerate', 'Trend_MA', 'Trendline',
    'Mover', 'Wave', 'Continuation', 'MACD', 'R2',
}

MEAN_REVERSION_FAMILIES = {
    'Bollinger', 'Exhaustion', 'Range', 'ZScore', 'Squeeze',
    'Stop_Hunt', 'Volume', 'ATR', 'Confluence',
}

# Signal-specific overrides (for signals that don't fit neatly into families)
SIGNAL_OVERRIDES = {
    # Momentum signals — block in chop
    'ema300_dip': 'MOMENTUM',
    'ema300_dip_long': 'MOMENTUM',
    'ema300_dip_short': 'MOMENTUM',
    'accel_300': 'MOMENTUM',
    'accel_300_long': 'MOMENTUM',
    'accel_300_short': 'MOMENTUM',
    'continuation': 'MOMENTUM',
    'continuation_long': 'MOMENTUM',
    'continuation_short': 'MOMENTUM',
    'r2_trend_long': 'MOMENTUM',
    'r2_trend_short': 'MOMENTUM',
    'open_skies': 'MOMENTUM',              # breakout signal — fails in chop (reclassified 2026-09-17)
    'open_skies_long': 'MOMENTUM',         # breakout signal — fails in chop (reclassified 2026-09-17)

    # Mean-reversion signals — always allowed
    'bb_bounce_v2_long': 'MEAN_REVERSION',
    'bb_bounce_long': 'MEAN_REVERSION',
    'bb_bounce_short': 'MEAN_REVERSION',
    'range_reversion_long': 'MEAN_REVERSION',
    'return_exhaustion_long': 'MEAN_REVERSION',
    'return_exhaustion_short': 'MEAN_REVERSION',
    'coiled_spring': 'MEAN_REVERSION',
    'coil_spring': 'MEAN_REVERSION',           # source string variant (hyphenated)
    'coiled_spring_long': 'MEAN_REVERSION',
    'liquidation_hunt_long': 'MEAN_REVERSION',
    'liquidation_hunt_short': 'MEAN_REVERSION',
    'liq_hunt': 'MEAN_REVERSION',              # source string variant (abbreviated)
    'liq_hunt_long': 'MEAN_REVERSION',
    'liq_hunt_short': 'MEAN_REVERSION',
    'neutral_sniper': 'MEAN_REVERSION',       # StochRSI+CMF mean-reversion — fires in chop, not momentum
    'neutral_sniper_long': 'MEAN_REVERSION',
    'neutral_sniper_short': 'MEAN_REVERSION',
    'pullback_entry': 'MEAN_REVERSION',       # post-impulse consolidation — mean-reversion
    'pullback_entry_long': 'MEAN_REVERSION',
    'pullback_entry_short': 'MEAN_REVERSION',
    'doji_top': 'MEAN_REVERSION',            # doji exhaustion at top — mean-reversion
    'rr_structural_v2_long': 'MEAN_REVERSION',   # RR structural v2 — support/resistance structure, not momentum (2026-09-14)
    'rr_structural_v2_short': 'MEAN_REVERSION',
    'trend_purity': 'MEAN_REVERSION',       # structural trend confirmation — allowed in chop
    'trend_purity_long': 'MEAN_REVERSION',
    'trend_purity_short': 'MEAN_REVERSION',
    'doji_top_short': 'MEAN_REVERSION',
    'doji_top_exit': 'MEAN_REVERSION',
    'doji_bottom_long': 'MEAN_REVERSION',    # doji exhaustion at bottom — mean-reversion
    'ema300_breakthrough': 'MOMENTUM',        # EMA300 breakout — trend continuation, block in chop
    'ema300_breakthrough_long': 'MOMENTUM',
    'ema300_breakthrough_short': 'MOMENTUM',
    'grind_trend': 'MOMENTUM',               # accumulation grind — trend following, block in chop
    'grind_trend_long': 'MOMENTUM',
    'grind_trend_short': 'MOMENTUM',
    # pump-chain: chain-correlation signal, fires when coin is pumping — NOT BTC-dependent (2026-09-13)
    'pump_chain': 'MEAN_REVERSION',
    'pump_chain_long': 'MEAN_REVERSION',
    'pump_chain_short': 'MEAN_REVERSION',
    'pump-chain': 'MEAN_REVERSION',
    'pump-chain+': 'MEAN_REVERSION',
    'pump-chain-': 'MEAN_REVERSION',
}


def _get_token_momentum(token: str) -> float:
    """Get token's 1h momentum (% change). Returns positive if trending up."""
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = ? ORDER BY ts DESC LIMIT 60
        """, (token.upper(),))
        closes = [r[0] for r in cur.fetchall()]
        if len(closes) < 60:
            return 0.0
        return (closes[0] - closes[-1]) / closes[-1] * 100 if closes[-1] > 0 else 0.0
    except Exception:
        return 0.0
    finally:
        if conn:
            conn.close()


def _classify_signal(signal_type: str) -> str:
    """Classify a signal as MOMENTUM or MEAN_REVERSION."""
    # Check overrides first
    if signal_type in SIGNAL_OVERRIDES:
        return SIGNAL_OVERRIDES[signal_type]

    # Strip direction/confluence suffixes for family lookup
    base = signal_type.replace('+', '').replace('-', '').replace('_long', '').replace('_short', '')

    # Also try to extract bare signal type from chain data (e.g. "ADA(1.73x),pump-chain+" -> "pump-chain")
    # Chain data looks like "TOKEN(N.NNx)" — split on comma, find parts without parentheses
    parts = [p.strip() for p in signal_type.split(',')]
    for p in parts:
        if '(' in p:
            continue
        # Exact match
        if p in SIGNAL_OVERRIDES:
            return SIGNAL_OVERRIDES[p]
        # Normalize hyphens to underscores + strip suffixes (e.g. "bb-bounce-v2-long+" -> "bb_bounce_v2_long")
        p_normalized = p.replace('-', '_').replace('+', '').rstrip('_')
        if p_normalized in SIGNAL_OVERRIDES:
            return SIGNAL_OVERRIDES[p_normalized]
        # Also try stripped version (original behavior)
        p_stripped = p.replace('+', '').replace('-', '').replace('_long', '').replace('_short', '')
        if p_stripped in SIGNAL_OVERRIDES:
            return SIGNAL_OVERRIDES[p_stripped]

    # Try market_phase_gate family lookup
    try:
        from market_phase_gate import signal_family
        family = signal_family(base)
        if family in MOMENTUM_FAMILIES:
            return 'MOMENTUM'
        elif family in MEAN_REVERSION_FAMILIES:
            return 'MEAN_REVERSION'
    except ImportError:
        pass

    # Default: treat unknown signals as momentum (conservative — block in chop)
    return 'MOMENTUM'


# ── Regime Detection ──────────────────────────────────────────────────────────

def _check_directional_outcome() -> dict:
    """Check directional outcome WR degradation. Returns {direction: {wr, losses, total}}."""
    try:
        from signal_compactor import get_directional_outcome
        result = {}
        for direction in ['LONG', 'SHORT']:
            losses, total, wr = get_directional_outcome(direction)
            result[direction] = {'wr': wr, 'losses': losses, 'total': total}
        return result
    except Exception:
        return {}


def _check_btc_momentum() -> dict:
    """Check BTC 30m momentum. Returns {momentum_pct, is_flat}."""
    from hermes_constants import CHOP_DETECTOR_BTC_MOM_THRESHOLD
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_1m
            WHERE token = 'BTC' ORDER BY ts DESC LIMIT 30
        """)
        closes = [r[0] for r in cur.fetchall()]

        if len(closes) < 30:
            return {'momentum_pct': 0, 'is_flat': True}

        # 30m momentum: (current - 30 bars ago) / 30 bars ago * 100
        momentum = (closes[0] - closes[-1]) / closes[-1] * 100 if closes[-1] > 0 else 0
        return {'momentum_pct': round(momentum, 3), 'is_flat': abs(momentum) < CHOP_DETECTOR_BTC_MOM_THRESHOLD}
    except Exception:
        return {'momentum_pct': 0, 'is_flat': True}
    finally:
        if conn:
            conn.close()


def _check_volatility_regime() -> str:
    """Get volatility regime from gate v2. Returns FLAT/NORMAL/HIGH/EXTREME."""
    try:
        from volatility_gate_v2 import classify_volatility, get_atr_pct
        atr = get_atr_pct('BTC')
        if atr is not None:
            return classify_volatility(atr)
    except Exception:
        pass
    return 'NORMAL'


def _check_market_phase() -> str:
    """Get market phase from phase gate. Returns phase string."""
    try:
        from market_phase_gate import detect_phase
        phase_info = detect_phase(lookback_days=1)
        return phase_info.get('phase', 'quiet')
    except Exception:
        return 'quiet'


def get_regime() -> dict:
    """
    Classify current market regime by combining all 4 inputs.

    Returns:
        {
            'regime': 'TREND' | 'CHOP' | 'CRISIS',
            'reason': str,
            'momentum_allowed': bool,
            'mean_reversion_allowed': bool,
            'details': dict,
        }
    """
    global _regime_cache, _regime_cache_time

    from hermes_constants import CHOP_DETECTOR_CACHE_TTL
    now = time.time()
    if _regime_cache and (now - _regime_cache_time) < CHOP_DETECTOR_CACHE_TTL:
        return _regime_cache

    # Gather inputs
    dir_outcome = _check_directional_outcome()
    btc_momentum = _check_btc_momentum()
    vol_regime = _check_volatility_regime()
    market_phase = _check_market_phase()

    from hermes_constants import CHOP_DETECTOR_WR_THRESHOLD, CHOP_DETECTOR_BTC_MOM_THRESHOLD

    # Scoring: each input votes for TREND, CHOP, or CRISIS
    votes = {'TREND': 0, 'CHOP': 0, 'CRISIS': 0}

    # 1. Directional outcome: WR < threshold = chop signal
    for direction, data in dir_outcome.items():
        if data['total'] >= 3:
            if data['wr'] < CHOP_DETECTOR_WR_THRESHOLD - 15:
                votes['CRISIS'] += 2
            elif data['wr'] < CHOP_DETECTOR_WR_THRESHOLD:
                votes['CHOP'] += 1
            else:
                votes['TREND'] += 1

    # 2. BTC momentum: flat = chop, strong = trend
    if btc_momentum['is_flat']:
        votes['CHOP'] += 1
    elif abs(btc_momentum['momentum_pct']) > CHOP_DETECTOR_BTC_MOM_THRESHOLD * 2:
        votes['TREND'] += 2
    elif abs(btc_momentum['momentum_pct']) > CHOP_DETECTOR_BTC_MOM_THRESHOLD:
        votes['TREND'] += 1

    # 3. Volatility regime
    if vol_regime == 'FLAT':
        votes['CHOP'] += 2
    elif vol_regime == 'NORMAL':
        votes['TREND'] += 1
    elif vol_regime == 'HIGH':
        votes['TREND'] += 2  # volatile = trending
    elif vol_regime == 'EXTREME':
        votes['CRISIS'] += 2

    # 4. Market phase
    if market_phase in ('defensive', 'range', 'quiet'):
        votes['CHOP'] += 1
    elif market_phase in ('trend_building', 'explosion'):
        votes['TREND'] += 2
    elif market_phase == 'mover_hunting':
        votes['TREND'] += 1

    # 5. BTC 4h regime override (2026-09-18) — ignores short-term noise when macro trend is clear
    # When BTC 4h regime is LONG_BIAS or SHORT_BIAS with strong slope, override chop classification
    try:
        import psycopg2
        _pg_conn = psycopg2.connect(host='/var/run/postgresql', dbname='brain', user='postgres')
        _pg_cur = _pg_conn.cursor()
        _pg_cur.execute("SELECT regime_4h, slope_4h FROM momentum_cache WHERE token = 'BTC'")
        _btc_4h = _pg_cur.fetchone()
        _pg_conn.close()
        if _btc_4h and _btc_4h[0] and _btc_4h[1] is not None:
            _slope_4h = float(_btc_4h[1])
            if _btc_4h[0] == 'LONG_BIAS' and _slope_4h > 0.35:
                votes['TREND'] += 2  # strong bullish 4h — override chop
            elif _btc_4h[0] == 'SHORT_BIAS' and _slope_4h < -0.35:
                votes['TREND'] += 2  # strong bearish 4h — override chop (SHORT signals are momentum too)
    except Exception:
        pass  # if DB unavailable, fall through to existing votes

    # 6. BTC continuum override (2026-09-20) — structural regime from continuum oscillator
    # When continuum shows clear directional structure (not just velocity), override chop
    # Catches slow bleeds where BTC is drifting but structure is bearish
    try:
        _cont_db = os.path.join(HERMES_DATA, 'continuum.db')
        _cont_conn = sqlite3.connect(_cont_db, timeout=3)
        _cont_row = _cont_conn.execute(
            "SELECT market_phase, linreg_direction, ema300_position FROM continuum_states "
            "WHERE token='BTC' ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        _cont_conn.close()
        if _cont_row:
            _phase, _linreg, _ema_pos = _cont_row[0], _cont_row[1], _cont_row[2]
            # Bearish structure: DECLINING phase OR (CALM + LEAN_BEAR + BELOW EMA300)
            _bearish = (_phase in ('DECLINING', 'STRONG_DECLINING') or
                        (_phase in ('CALM', 'RECOVERY') and _linreg in ('LEAN_BEAR', 'BEAR') and _ema_pos == 'BELOW'))
            # Bullish structure: RALLYING phase OR (CALM + LEAN_BULL + ABOVE EMA300)
            _bullish = (_phase in ('RALLYING', 'STRONG_RALLYING', 'UP') or
                        (_phase in ('CALM', 'DISTRIBUTION') and _linreg in ('LEAN_BULL', 'BULL') and _ema_pos == 'ABOVE'))
            if _bearish or _bullish:
                votes['TREND'] += 5  # continuum overrides all — strongest structural indicator
    except Exception:
        pass  # if continuum unavailable, fall through to existing votes

    # Determine regime
    if votes['CRISIS'] >= 3:
        regime = 'CRISIS'
        reason = f"CRISIS: dir_outcome={dir_outcome}, vol={vol_regime}, btc_mom={btc_momentum['momentum_pct']:+.3f}%"
        momentum_allowed = False
        mean_reversion_allowed = False
    elif votes['CHOP'] >= 3:
        regime = 'CHOP'
        reason = f"CHOP: phase={market_phase}, vol={vol_regime}, btc_mom={btc_momentum['momentum_pct']:+.3f}%"
        momentum_allowed = False
        mean_reversion_allowed = True
    elif votes['TREND'] >= 3:
        regime = 'TREND'
        reason = f"TREND: phase={market_phase}, vol={vol_regime}, btc_mom={btc_momentum['momentum_pct']:+.3f}%"
        momentum_allowed = True
        mean_reversion_allowed = True
    else:
        # Ambiguous — default to CHOP (conservative)
        regime = 'CHOP'
        reason = f"AMBIGUOUS→CHOP: votes={votes}, phase={market_phase}, vol={vol_regime}"
        momentum_allowed = False
        mean_reversion_allowed = True

    result = {
        'regime': regime,
        'reason': reason,
        'momentum_allowed': momentum_allowed,
        'mean_reversion_allowed': mean_reversion_allowed,
        'details': {
            'dir_outcome': dir_outcome,
            'btc_momentum': btc_momentum,
            'vol_regime': vol_regime,
            'market_phase': market_phase,
            'votes': votes,
        },
    }

    _regime_cache = result
    _regime_cache_time = now
    return result


def should_trade_signal(signal_type: str, regime: dict = None, token: str = None) -> tuple:
    """
    Check if a signal should be allowed in the current regime.

    Returns: (allowed: bool, reason: str)
    """
    if regime is None:
        regime = get_regime()

    if regime['regime'] == 'CRISIS':
        return False, f"CRISIS — all signals blocked"

    signal_class = _classify_signal(signal_type)

    if signal_class == 'MOMENTUM' and not regime['momentum_allowed']:
        # Token-level check: if the token itself is trending strongly,
        # allow momentum signals even in CHOP. BTC flat ≠ COMP flat.
        if token:
            try:
                token_mom = _get_token_momentum(token)
                if abs(token_mom) > 0.5:  # token trending >0.5% in 1h
                    return True, f"CHOP bypass — {token} trending ({token_mom:+.2f}%), momentum OK"
            except Exception:
                pass
        return False, f"CHOP — momentum signal {signal_type} blocked (preserve winrate)"

    if signal_class == 'MEAN_REVERSION' and not regime['mean_reversion_allowed']:
        return False, f"Regime blocks mean-reversion"

    return True, f"OK ({signal_class} in {regime['regime']})"


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    regime = get_regime()
    print(f"=== Chop Detector ===")
    print(f"Regime: {regime['regime']}")
    print(f"Reason: {regime['reason']}")
    print(f"Momentum allowed: {regime['momentum_allowed']}")
    print(f"Mean-reversion allowed: {regime['mean_reversion_allowed']}")
    print(f"\nDetails:")
    for k, v in regime['details'].items():
        print(f"  {k}: {v}")

    # Test signal classification
    test_signals = [
        'ema300-dip', 'ema300-dip-short', 'accel-300', 'accel-300-long',
        'bb-bounce-v2-long+', 'bb-bounce-long+', 'open-skies+',
        'continuation+', 'r2-trend-long', 'return-exhaustion-long',
        'coil-spring+', 'liq-hunt+', 'range-reversion-long+',
    ]

    print(f"\n=== Signal Classification ===")
    for sig in test_signals:
        allowed, reason = should_trade_signal(sig, regime)
        sig_class = _classify_signal(sig)
        status = "✅" if allowed else "🚫"
        print(f"  {status} {sig:>30} [{sig_class:>15}] → {reason}")
