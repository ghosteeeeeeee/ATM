#!/usr/bin/env python3
"""
continuum_trend.py — BTC trendline alignment signal for the alt pipeline.

This signal fires when the continuum engine's multi-timeframe linear regression
slopes (the "trendlines") align strongly in one direction. This is the most
reliable indicator from the continuum engine because it captures STRUCTURAL
momentum — not just where price is, but where the trend is going.

When 1m/5m/15m/1h linreg slopes all point the same way, it means BTC has
established a trend that altcoins will follow. This is the "riding the waves"
signal.

Signal modes:
1. TREND_ALIGN: When linreg_direction is BULL or BEAR with alignment ≥ 0.75
   → fires a directional signal (LONG if BULL, SHORT if BEAR)
   
2. TREND_REVERSAL: When linreg_direction flips from BULL→BEAR or BEAR→BULL
   with strong momentum → fires an early reversal signal

The signal only fires for BTC (which drives the entire market).
Altcoins get the benefit via signal_compactor's continuum context boost.
"""
import sys, os, sqlite3, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from signal_schema import add_signal, get_cooldown, set_cooldown
from paths import HERMES_DATA

from hermes_constants import (
    CONTINUUM_TREND_ENABLED,
    CONTINUUM_TREND_ALIGN_ENABLED,
    CONTINUUM_TREND_REVERSAL_ENABLED,
    CONTINUUM_TREND_MIN_ALIGNMENT,
    CONTINUUM_TREND_MIN_SLOPE,
    CONTINUUM_TREND_COOLDOWN_MIN,
    CONTINUUM_TREND_CONF_BASE,
    LONG_BLACKLIST, SHORT_BLACKLIST,
)

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _get_recent_states(token: str = 'BTC', limit: int = 10):
    """Get recent continuum states with linreg data."""
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=10)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, price, state_score, linreg_direction, linreg_alignment,
                   linreg_1m_slope, linreg_5m_slope, linreg_15m_slope, linreg_1h_slope,
                   ema300_position, velocity_state, volume_regime
            FROM continuum_states
            WHERE token = ?
            ORDER BY ts DESC
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        return [dict(r) for r in reversed(rows)]
    except Exception as e:
        print(f"[continuum-trend] Error: {e}")
        return []
    finally:
        if conn:
            conn.close()


def detect_trend_align(token: str = 'BTC'):
    """
    Detect when linreg trendlines strongly align in one direction.
    
    Requires:
    - linreg_direction is BULL or BEAR
    - linreg_alignment ≥ 0.75 (75%+ of timeframes agree)
    - At least one linreg slope is above minimum (not all flat)
    """
    states = _get_recent_states(token, limit=5)
    if not states:
        return None
    
    latest = states[-1]
    
    # Check freshness
    age = time.time() - latest['ts']
    if age > 300:  # 5 min max
        return None
    
    direction = latest.get('linreg_direction', 'NEUTRAL')
    alignment = latest.get('linreg_alignment', 0) or 0
    score = latest.get('state_score', 50) or 50
    
    # Check minimum alignment
    if alignment < CONTINUUM_TREND_MIN_ALIGNMENT:
        return None
    
    # Check that at least one slope is meaningful (not all flat)
    slopes = [
        latest.get('linreg_1m_slope', 0) or 0,
        latest.get('linreg_5m_slope', 0) or 0,
        latest.get('linreg_15m_slope', 0) or 0,
        latest.get('linreg_1h_slope', 0) or 0,
    ]
    max_abs_slope = max(abs(s) for s in slopes) if slopes else 0
    if max_abs_slope < CONTINUUM_TREND_MIN_SLOPE:
        return None
    
    # BULL alignment → LONG signal
    if direction in ('BULL', 'LEAN_BULL'):
        # Confidence: base + alignment bonus + slope strength bonus
        conf = CONTINUUM_TREND_CONF_BASE
        conf += alignment * 10  # up to +10 for perfect alignment
        conf += min(5, max_abs_slope * 50)  # up to +5 for strong slopes
        conf = min(92, conf)
        
        # Score bonus: higher score = stronger trend confirmation
        if score >= 70:
            conf = min(94, conf + 3)
        
        price = latest.get('price', 0) or 0
        if price <= 0:
            return None
        
        return {
            'direction': 'LONG',
            'confidence': conf,
            'value': alignment,
            'price': price,
            'reason': f'trend_align_{direction}_{alignment:.0%}_slope_{max_abs_slope:.4f}',
            'score': score,
        }
    
    # BEAR alignment → SHORT signal
    if direction in ('BEAR', 'LEAN_BEAR'):
        conf = CONTINUUM_TREND_CONF_BASE
        conf += alignment * 10
        conf += min(5, max_abs_slope * 50)
        conf = min(92, conf)
        
        if score <= 30:
            conf = min(94, conf + 3)
        
        price = latest.get('price', 0) or 0
        if price <= 0:
            return None
        
        return {
            'direction': 'SHORT',
            'confidence': conf,
            'value': alignment,
            'price': price,
            'reason': f'trend_align_{direction}_{alignment:.0%}_slope_{max_abs_slope:.4f}',
            'score': score,
        }
    
    return None


def detect_trend_reversal(token: str = 'BTC'):
    """
    Detect when linreg direction flips (BULL→BEAR or BEAR→BULL).
    
    This is the early reversal signal — when the trendlines change
    direction, a new wave is starting.
    
    Requires:
    - Direction flipped in the last 3 ticks (1.5 min)
    - New direction has alignment ≥ 0.5 (at least some TFs confirming)
    - Previous direction had alignment ≥ 0.5 (it was a real trend, not noise)
    """
    states = _get_recent_states(token, limit=8)
    if len(states) < 4:
        return None
    
    latest = states[-1]
    age = time.time() - latest['ts']
    if age > 300:
        return None
    
    current_dir = latest.get('linreg_direction', 'NEUTRAL')
    current_align = latest.get('linreg_alignment', 0) or 0
    
    # Check minimum alignment on new direction
    if current_align < 0.5:
        return None
    
    # Find the most recent direction change in last 3 ticks
    prev_dir = None
    for i in range(len(states) - 2, max(0, len(states) - 5), -1):
        d = states[i].get('linreg_direction', 'NEUTRAL')
        if d != current_dir and d != 'NEUTRAL':
            prev_dir = d
            prev_idx = i
            break
    
    if prev_dir is None:
        return None
    
    # Verify previous direction was a real trend (not just NEUTRAL bouncing)
    prev_align = states[prev_idx].get('linreg_alignment', 0) or 0
    if prev_align < 0.5:
        return None
    
    # Check it's a meaningful flip (BULL↔BEAR, not just LEAN→LEAN)
    bull_bear_dirs = {'BULL', 'BEAR'}
    if prev_dir in bull_bear_dirs or current_dir in bull_bear_dirs:
        # This is a real reversal
        score = latest.get('state_score', 50) or 50
        price = latest.get('price', 0) or 0
        if price <= 0:
            return None
        
        # BULL reversal → LONG
        if current_dir in ('BULL', 'LEAN_BULL'):
            conf = CONTINUUM_TREND_CONF_BASE + 5  # reversals get a boost
            conf += current_align * 8
            conf = min(90, conf)
            return {
                'direction': 'LONG',
                'confidence': conf,
                'value': current_align,
                'price': price,
                'reason': f'trend_reversal_{prev_dir}_to_{current_dir}_{current_align:.0%}',
                'score': score,
            }
        
        # BEAR reversal → SHORT
        if current_dir in ('BEAR', 'LEAN_BEAR'):
            conf = CONTINUUM_TREND_CONF_BASE + 5
            conf += current_align * 8
            conf = min(90, conf)
            return {
                'direction': 'SHORT',
                'confidence': conf,
                'value': current_align,
                'price': price,
                'reason': f'trend_reversal_{prev_dir}_to_{current_dir}_{current_align:.0%}',
                'score': score,
            }
    
    return None


def scan_signals() -> int:
    """Scan for continuum trend signals."""
    if not CONTINUUM_TREND_ENABLED:
        return 0
    
    added = 0
    token = 'BTC'
    
    # Check blacklists
    for direction in ['LONG', 'SHORT']:
        if direction == 'LONG' and token.upper() in LONG_BLACKLIST:
            return 0
        if direction == 'SHORT' and token.upper() in SHORT_BLACKLIST:
            return 0
    
    # Try trend alignment first (stronger signal)
    sig = None
    if CONTINUUM_TREND_ALIGN_ENABLED:
        sig = detect_trend_align(token)
    
    # Then try reversal (but only if no alignment signal)
    if not sig and CONTINUUM_TREND_REVERSAL_ENABLED:
        sig = detect_trend_reversal(token)
    
    if not sig:
        return 0
    
    direction = sig['direction']
    
    # Per-direction kill-switch
    if direction == 'LONG' and not CONTINUUM_TREND_ALIGN_ENABLED:
        return 0
    if direction == 'SHORT' and not CONTINUUM_TREND_REVERSAL_ENABLED:
        return 0
    
    # Cooldown
    if get_cooldown(token, direction=direction):
        return 0
    
    sig_type = f'continuum_trend_{direction.lower()}'
    source = f'continuum-trend{"+" if direction == "LONG" else "-"}'
    
    sid = add_signal(
        token=token.upper(),
        direction=direction,
        signal_type=sig_type,
        source=source,
        confidence=sig['confidence'],
        value=sig['value'],
        price=sig['price'],
        exchange='hyperliquid',
        timeframe='1m',
    )
    
    if sid:
        added += 1
        set_cooldown(token, direction, hours=CONTINUUM_TREND_COOLDOWN_MIN / 60.0)
        print(f"[CONTINUUM-TREND] {direction} {token} | conf={sig['confidence']} | "
              f"reason={sig['reason']}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    print("=== Continuum Trend Signal Test ===")
    states = _get_recent_states('BTC', limit=5)
    if states:
        latest = states[-1]
        print(f"Latest state:")
        print(f"  Linreg direction: {latest.get('linreg_direction')}")
        print(f"  Linreg alignment: {latest.get('linreg_alignment', 0):.0%}")
        print(f"  Slopes: 1m={latest.get('linreg_1m_slope', 0):.4f} "
              f"5m={latest.get('linreg_5m_slope', 0):.4f} "
              f"15m={latest.get('linreg_15m_slope', 0):.4f} "
              f"1h={latest.get('linreg_1h_slope', 0):.4f}")
        print(f"  Score: {latest.get('state_score', 0):.1f}")
        print()
        
        sig = detect_trend_align('BTC')
        if sig:
            print(f"Alignment signal: {sig['direction']} | Conf: {sig['confidence']} | reason={sig['reason']}")
        else:
            print("No alignment signal")
        
        sig = detect_trend_reversal('BTC')
        if sig:
            print(f"Reversal signal: {sig['direction']} | Conf: {sig['confidence']} | reason={sig['reason']}")
        else:
            print("No reversal signal")
    else:
        print("No continuum data found")
