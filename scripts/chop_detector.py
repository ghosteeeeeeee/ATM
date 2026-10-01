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
    'continuum_osc_long': 'MEAN_REVERSION',  # continuum oscillator — structural, allowed in chop (2026-09-23)
    'continuum_osc_short': 'MEAN_REVERSION',
    'continuum_score_long': 'MEAN_REVERSION',
    'continuum_score_short': 'MEAN_REVERSION',
    'continuum_trend_long': 'MEAN_REVERSION',
    'continuum_trend_short': 'MEAN_REVERSION',
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
    # rs: support/resistance — mean-reversion signal, fires on key levels (2026-09-25)
    'rs': 'MEAN_REVERSION',
    'rs_r': 'MEAN_REVERSION',   # rs-r60 normalized (hyphens→underscores)
    'rs_s': 'MEAN_REVERSION',   # rs-s36 normalized
    'rs-r': 'MEAN_REVERSION',   # rs-r60 after digit strip (hyphens preserved)
    'rs-s': 'MEAN_REVERSION',   # rs-s36 after digit strip
    'rsr': 'MEAN_REVERSION',    # rs-r60 fully stripped (no hyphens, no digits)
    'rss': 'MEAN_REVERSION',    # rs-s36 fully stripped
    'rs_long': 'MEAN_REVERSION',
    'rs_short': 'MEAN_REVERSION',
    'support_resistance': 'MEAN_REVERSION',  # family name used as signal_type in scoring
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


def get_coin_trend_score(token: str) -> int:
    """
    0-100 per-coin trend score. Extends _get_token_momentum() with richer data.

    0-30: Deep chop → mean-rev only, momentum blocked
    31-60: Weak trend → momentum penalized (0.3x), mean-rev boosted (1.2x)
    61-100: Strong trend → full signal set allowed (same as TREND regime)

    All data from candles_1m — no new APIs.
    """
    conn = None
    try:
        conn = sqlite3.connect(CANDLES_DB, timeout=5)
        cur = conn.cursor()
        token = token.upper()

        # Fetch 1h of 1m candles (60 bars)
        cur.execute("""
            SELECT close, high, low, volume FROM candles_1m
            WHERE token = ? ORDER BY ts DESC LIMIT 60
        """, (token,))
        rows = cur.fetchall()
        if len(rows) < 30:
            return 50  # insufficient data — neutral score

        closes = [r[0] for r in rows]
        highs = [r[1] for r in rows]
        lows = [r[2] for r in rows]
        volumes = [r[3] for r in rows]

        score = 0

        # 1. EMA20 vs EMA50 alignment (0-30 points)
        # ponytail: manual EMA calc, stdlib math only
        def _ema(data, period):
            if len(data) < period:
                return data[-1] if data else 0
            k = 2 / (period + 1)
            ema = sum(data[-period:]) / period
            for v in reversed(data[:-period]):
                ema = v * k + ema * (1 - k)
            return ema

        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, min(50, len(closes)))
        if ema50 > 0:
            ema_diff_pct = (ema20 - ema50) / ema50 * 100
            # Strong alignment: +30, weak: +15, crossed: +5
            if abs(ema_diff_pct) > 0.3:
                score += 30
            elif abs(ema_diff_pct) > 0.1:
                score += 20
            elif abs(ema_diff_pct) > 0.02:
                score += 10

        # 2. Price vs EMA20 position (0-20 points)
        if ema20 > 0:
            price_vs_ema = (closes[0] - ema20) / ema20 * 100
            if price_vs_ema > 0.2:
                score += 20  # price above EMA = bullish
            elif price_vs_ema > 0.05:
                score += 10
            elif price_vs_ema < -0.2:
                score += 20  # price below EMA = bearish (trending down = also trend)
            elif price_vs_ema < -0.05:
                score += 10

        # 3. Consecutive same-direction candles (last 6) (0-20 points)
        if len(closes) >= 6:
            recent = closes[:6]
            up_count = sum(1 for i in range(5) if recent[i] > recent[i+1])
            down_count = 5 - up_count
            max_consecutive = max(up_count, down_count)
            if max_consecutive >= 5:
                score += 20
            elif max_consecutive >= 4:
                score += 15
            elif max_consecutive >= 3:
                score += 10

        # 4. ATR ratio (current / 20-period avg) (0-15 points)
        if len(closes) >= 20:
            # Current ATR (14-period approximation from recent bars)
            trs = []
            for i in range(min(14, len(closes)-1)):
                tr = max(highs[i]-lows[i], abs(highs[i]-closes[i+1]), abs(lows[i]-closes[i+1]))
                trs.append(tr)
            current_atr = sum(trs) / len(trs) if trs else 0

            # 20-period avg ATR
            all_trs = []
            for i in range(min(20, len(closes)-1)):
                tr = max(highs[i]-lows[i], abs(highs[i]-closes[i+1]), abs(lows[i]-closes[i+1]))
                all_trs.append(tr)
            avg_atr = sum(all_trs) / len(all_trs) if all_trs else 0

            if avg_atr > 0 and current_atr > 0:
                atr_ratio = current_atr / avg_atr
                if atr_ratio > 1.5:
                    score += 15  # expanding volatility = trending
                elif atr_ratio > 1.1:
                    score += 10
                elif atr_ratio > 0.8:
                    score += 5

        # 5. Volume trend (0-10 points)
        if len(volumes) >= 10:
            recent_vol = sum(volumes[:5]) / 5
            older_vol = sum(volumes[5:10]) / 5
            if older_vol > 0:
                vol_ratio = recent_vol / older_vol
                if vol_ratio > 1.5:
                    score += 10  # volume increasing = conviction
                elif vol_ratio > 1.1:
                    score += 5

        # 6. Existing momentum bonus (0-5 points)
        mom = _get_token_momentum(token)
        if abs(mom) > 0.5:
            score += 5

        return max(0, min(100, score))
    except Exception:
        return 50  # neutral on error
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
        # Try original signal_type first — signal_family does its own suffix
        # stripping + fallback to full name. Stripping here first breaks
        # lookups: volume_breakout_short -> volume_breakout -> 'Other' -> MOMENTUM.
        family = signal_family(signal_type)
        if family in MOMENTUM_FAMILIES:
            return 'MOMENTUM'
        elif family in MEAN_REVERSION_FAMILIES:
            return 'MEAN_REVERSION'
        # Fall back to pre-stripped base
        family = signal_family(base)
        if family in MOMENTUM_FAMILIES:
            return 'MOMENTUM'
        elif family in MEAN_REVERSION_FAMILIES:
            return 'MEAN_REVERSION'
    except ImportError:
        pass

    # Try stripping trailing digits (e.g. 'rs-r60' -> 'rs-r', 'rs_r60' -> 'rs_r')
    import re
    # Strip digits first, then normalize hyphens
    base_stripped = re.sub(r'\d+$', '', signal_type.replace('+', '').replace('-', '_'))
    if base_stripped in SIGNAL_OVERRIDES:
        return SIGNAL_OVERRIDES[base_stripped]
    # Also try with hyphens preserved
    base_stripped2 = re.sub(r'\d+$', '', signal_type.rstrip('+-'))
    if base_stripped2 in SIGNAL_OVERRIDES:
        return SIGNAL_OVERRIDES[base_stripped2]

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

    # 5. BTC continuum oscillator override (2026-09-21) — fast indicator, overrides chop
    # When BTC continuum score is extreme with strong trend_bias, override chop classification
    try:
        from continuum_context import get_btc_trend_context
        _ctx = get_btc_trend_context()
        if _ctx and _ctx.get('available'):
            _score = _ctx.get('score', 50)
            _bias = _ctx.get('trend_bias', 0)
            if _score > 80 and _bias > 0.5:
                votes['TREND'] += 2  # strong bullish continuum — override chop
            elif _score < 20 and _bias < -0.5:
                votes['TREND'] += 2  # strong bearish continuum — override chop
    except Exception:
        pass  # if continuum unavailable, fall through to existing votes

    # 6. BTC continuum override (2026-09-20) — structural regime from continuum oscillator
    # When continuum shows clear directional structure (not just velocity), override chop
    # Catches slow bleeds where BTC is drifting but structure is bearish
    # Actual market_phase values: NEUTRAL, STORMY, CALM, RECOVERY, DECLINING
    _continuum_voted = False
    try:
        _cont_db = os.path.join(HERMES_DATA, 'continuum.db')
        _cont_conn = None
        try:
            _cont_conn = sqlite3.connect(_cont_db, timeout=3)
            _cont_row = _cont_conn.execute(
                "SELECT market_phase, linreg_direction, ema300_position, ts FROM continuum_states "
                "WHERE token='BTC' ORDER BY ts DESC LIMIT 1"
            ).fetchone()
        finally:
            if _cont_conn:
                try: _cont_conn.close()
                except: pass
        if _cont_row:
            _phase, _linreg, _ema_pos, _cont_ts = _cont_row[0], _cont_row[1], _cont_row[2], _cont_row[3]
            # Skip if stale (>10 min old)
            if _cont_ts and (time.time() - _cont_ts) > 600:
                pass  # stale data, don't override
            else:
                # FIX (Bug Hunter 2026-09-20): DECLINING alone is NOT bearish — it just means RSI<45.
                # Require structural confirmation (linreg BEAR + BELOW EMA300) for ALL phases.
                _bearish = ((_phase in ('DECLINING', 'CALM', 'RECOVERY') and
                             _linreg in ('LEAN_BEAR', 'BEAR') and _ema_pos == 'BELOW'))
                # Bullish structure: RECOVERY/CALM + LEAN_BULL + ABOVE EMA300
                _bullish = ((_phase in ('RECOVERY', 'CALM') and
                             _linreg in ('LEAN_BULL', 'BULL') and _ema_pos == 'ABOVE'))
                if _bearish or _bullish:
                    votes['TREND'] += 5
                    _continuum_voted = True
    except Exception:
        pass  # if continuum unavailable, fall through to existing votes
    if votes['CRISIS'] >= 3:
        regime = 'CRISIS'
        reason = f"CRISIS: dir_outcome={dir_outcome}, vol={vol_regime}, btc_mom={btc_momentum['momentum_pct']:+.3f}%"
        momentum_allowed = False
        mean_reversion_allowed = False
    elif _continuum_voted and votes['TREND'] >= votes['CHOP']:
        regime = 'TREND'
        reason = f"TREND (continuum override): votes={votes}, btc_mom={btc_momentum['momentum_pct']:+.3f}%"
        momentum_allowed = True
        mean_reversion_allowed = True
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
        # Token-level check: use trend score (0-100) for granular routing
        # chop-v2-spec: score <30 = deep chop (block), 31-60 = weak (penalize), >60 = strong (allow)
        if token:
            try:
                tscore = get_coin_trend_score(token)
                if tscore >= 61:
                    return True, f"CHOP bypass — {token} trend_score={tscore} (strong trend, momentum OK)"
                elif tscore >= 31:
                    return True, f"CHOP bypass — {token} trend_score={tscore} (weak trend, momentum allowed with penalty)"
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

    # Per-coin trend scores (chop-v2 foundation)
    test_tokens = ['BTC', 'ETH', 'SOL', 'DOGE', 'PEPE', 'LINK', 'AVAX', 'BNB']
    print(f"\n=== Per-Coin Trend Scores ===")
    for tok in test_tokens:
        tscore = get_coin_trend_score(tok)
        if tscore >= 61:
            zone = "STRONG"
        elif tscore >= 31:
            zone = "WEAK"
        else:
            zone = "CHOP"
        mom = _get_token_momentum(tok)
        print(f"  {tok:>6}: score={tscore:>3}/100 [{zone:>6}]  momentum={mom:+.2f}%")
