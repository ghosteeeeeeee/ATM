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
    'ema300_dip_short': 'MOMENTUM',
    'accel_300': 'MOMENTUM',
    'accel_300_long': 'MOMENTUM',
    'accel_300_short': 'MOMENTUM',
    'continuation': 'MOMENTUM',
    'continuation_long': 'MOMENTUM',
    'continuation_short': 'MOMENTUM',
    'r2_trend_long': 'MOMENTUM',
    'r2_trend_short': 'MOMENTUM',

    # Mean-reversion signals — always allowed
    'bb_bounce_v2_long': 'MEAN_REVERSION',
    'bb_bounce_long': 'MEAN_REVERSION',
    'bb_bounce_short': 'MEAN_REVERSION',
    'open_skies': 'MEAN_REVERSION',
    'open_skies_long': 'MEAN_REVERSION',
    'range_reversion_long': 'MEAN_REVERSION',
    'return_exhaustion_long': 'MEAN_REVERSION',
    'return_exhaustion_short': 'MEAN_REVERSION',
    'coiled_spring': 'MEAN_REVERSION',
    'coiled_spring_long': 'MEAN_REVERSION',
    'liquidation_hunt_long': 'MEAN_REVERSION',
    'liquidation_hunt_short': 'MEAN_REVERSION',
    'neutral_sniper': 'MEAN_REVERSION',       # StochRSI+CMF mean-reversion — fires in chop, not momentum
    'neutral_sniper_long': 'MEAN_REVERSION',
    'neutral_sniper_short': 'MEAN_REVERSION',
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

    from hermes_constants import CHOP_DETECTOR_WR_THRESHOLD

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
