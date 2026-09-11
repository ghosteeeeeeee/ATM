#!/usr/bin/env python3
"""
continuum_context.py — Reusable BTC trend context layer for all signals.

The continuum engine tracks BTC as a living state machine. This module
exposes that state as a simple API that any signal can query to get:
  - BTC trend bias (+1 bullish to -1 bearish)
  - Linreg direction and alignment (the "trendlines")
  - Score momentum (rising/falling/flat)
  - Composite regime (BULL_TREND, BEAR_TREND, RANGING, etc.)

Usage in any signal:
    from continuum_context import get_btc_trend_context
    ctx = get_btc_trend_context()
    if ctx['trend_bias'] > 0.5:
        # BTC is strongly bullish — favor LONG entries on alts
    elif ctx['trend_bias'] < -0.5:
        # BTC is strongly bearish — favor SHORT entries on alts

Author: Hermes Trading System
Created: 2026-09-12
"""

import os
import sys
import time
import sqlite3
import json
from typing import Optional, Dict, Tuple, List

sys.path.insert(0, os.path.dirname(__file__))
from paths import HERMES_DATA, WWW_DATA

CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')


def _query_latest(token: str = 'BTC', max_age_seconds: int = 300) -> Optional[dict]:
    """Query the latest continuum state from continuum.db.
    
    Returns dict with all state dimensions or None if stale/missing.
    max_age_seconds: how old data can be before we consider it stale (default 5min).
    """
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM continuum_states 
            WHERE token = ? 
            ORDER BY ts DESC 
            LIMIT 1
        """, (token.upper(),))
        row = cur.fetchone()
        if not row:
            return None
        
        row_dict = dict(row)
        
        # Check staleness
        age = time.time() - row_dict['ts']
        if age > max_age_seconds:
            return None
        
        return row_dict
    except Exception as e:
        print(f"[continuum_context] Error: {e}", flush=True)
        return None
    finally:
        if conn:
            conn.close()


def _query_recent(token: str = 'BTC', limit: int = 20) -> List[dict]:
    """Query recent continuum states for momentum/trend detection."""
    conn = None
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM continuum_states 
            WHERE token = ? 
            ORDER BY ts DESC 
            LIMIT ?
        """, (token.upper(), limit))
        rows = cur.fetchall()
        # Reverse to oldest-first
        return [dict(r) for r in reversed(rows)]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def _score_to_bias(score: float) -> float:
    """Convert a 0-100 score to a -1 to +1 trend bias.
    
    Score 50 = neutral (0)
    Score 100 = max bullish (+1)
    Score 0 = max bearish (-1)
    Linear mapping with a dead zone around 45-55 for noise filtering.
    """
    if score is None:
        return 0.0
    if score >= 55:
        return min(1.0, (score - 55) / 45.0)  # 55→0, 100→1
    elif score <= 45:
        return max(-1.0, (score - 45) / 45.0)  # 45→0, 0→-1
    else:
        return 0.0  # Dead zone: 45-55 = neutral


def _compute_score_momentum(scores: List[float]) -> float:
    """Compute score momentum: rate of change over recent scores.
    
    Returns -1 (strong bearish momentum) to +1 (strong bullish momentum).
    """
    if len(scores) < 4:
        return 0.0
    
    # Use linear regression slope of recent scores, normalized
    n = len(scores)
    x_mean = (n - 1) / 2
    y_mean = sum(scores) / n
    
    num = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
    den = sum((i - x_mean) ** 2 for i in range(n))
    
    if den == 0:
        return 0.0
    
    slope = num / den  # points per tick
    
    # Normalize: slope of ±2 per tick = strong momentum
    # Each tick is 30 seconds, so slope of 2 = score changing 4 points/minute
    return max(-1.0, min(1.0, slope / 2.0))


def _compute_linreg_bias(linreg_direction: str, linreg_alignment: float) -> float:
    """Convert linreg direction+alignment to -1 to +1 bias.
    
    This is the "trendlines" signal — the most powerful component.
    When 1m/5m/15m/1h linreg slopes all agree, the trend is established.
    """
    direction_map = {
        'BULL': 1.0,
        'LEAN_BULL': 0.5,
        'NEUTRAL': 0.0,
        'LEAN_BEAR': -0.5,
        'BEAR': -1.0,
    }
    
    dir_bias = direction_map.get(linreg_direction, 0.0)
    return dir_bias * linreg_alignment


def _classify_regime(score: float, linreg_dir: str, momentum: float) -> str:
    """Classify the overall BTC continuum regime.
    
    Returns one of:
    - BULL_TREND: Strong uptrend, score >60, linreg BULL
    - BEAR_TREND: Strong downtrend, score <40, linreg BEAR
    - RANGING_BULL: Ranging with bullish bias
    - RANGING_BEAR: Ranging with bearish bias
    - RANGING: No clear direction
    - TRANSITIONING: Score changing rapidly, direction unclear
    """
    if abs(momentum) > 0.6:
        return 'TRANSITIONING'
    
    if score >= 65 and linreg_dir in ('BULL', 'LEAN_BULL'):
        return 'BULL_TREND'
    elif score <= 35 and linreg_dir in ('BEAR', 'LEAN_BEAR'):
        return 'BEAR_TREND'
    elif score >= 50 and linreg_dir in ('BULL', 'LEAN_BULL'):
        return 'RANGING_BULL'
    elif score <= 50 and linreg_dir in ('BEAR', 'LEAN_BEAR'):
        return 'RANGING_BEAR'
    else:
        return 'RANGING'


def get_btc_trend_context(token: str = 'BTC', max_age: int = 300) -> dict:
    """
    Get comprehensive BTC trend context from the continuum engine.
    
    This is the main entry point. Any signal can call this to get
    a simple dict with everything it needs to align with BTC's trend.
    
    Returns dict:
        score: float (0-100) — current continuum score
        trend_bias: float (-1 to +1) — directional bias
        linreg_bias: float (-1 to +1) — trendline-based bias (most reliable)
        momentum: float (-1 to +1) — score momentum
        regime: str — classified regime
        ema300_position: str — ABOVE/BELOW/AT
        linreg_direction: str — BULL/BEAR/NEUTRAL etc.
        linreg_alignment: float (0-1) — fraction of TFs agreeing
        linreg_1m: float — 1m linreg slope
        linreg_5m: float — 5m linreg slope  
        linreg_15m: float — 15m linreg slope
        linreg_1h: float — 1h linreg slope
        volume_regime: str — LOW/NORMAL/HIGH/PARABOLIC
        velocity: str — FALLING/SLOW/RISING/FAST
        trend_quality: str — STRONG_UP/UP/WEAK/DOWN/STRONG_DOWN
        wyckoff: str — ACCUMULATION/MARKUP/DISTRIBUTION/MARKDOWN/UNKNOWN
        freshness: float — seconds since last update
        available: bool — whether data is fresh enough to use
    """
    latest = _query_latest(token, max_age)
    
    if not latest:
        return {
            'score': 50.0,
            'trend_bias': 0.0,
            'linreg_bias': 0.0,
            'momentum': 0.0,
            'regime': 'RANGING',
            'ema300_position': 'AT',
            'linreg_direction': 'NEUTRAL',
            'linreg_alignment': 0.0,
            'linreg_1m': 0.0,
            'linreg_5m': 0.0,
            'linreg_15m': 0.0,
            'linreg_1h': 0.0,
            'volume_regime': 'NORMAL',
            'velocity': 'SLOW',
            'trend_quality': 'WEAK',
            'wyckoff': 'UNKNOWN',
            'freshness': 9999,
            'available': False,
        }
    
    score = latest['state_score'] or 50.0
    linreg_dir = latest.get('linreg_direction', 'NEUTRAL') or 'NEUTRAL'
    linreg_align = latest.get('linreg_alignment', 0.0) or 0.0
    
    # Get recent scores for momentum
    recent = _query_recent(token, limit=20)
    recent_scores = [r['state_score'] for r in recent if r['state_score'] is not None]
    momentum = _compute_score_momentum(recent_scores)
    
    # Compute biases
    trend_bias = _score_to_bias(score)
    linreg_bias = _compute_linreg_bias(linreg_dir, linreg_align)
    
    # Classify regime
    regime = _classify_regime(score, linreg_dir, momentum)
    
    freshness = time.time() - latest['ts']
    
    return {
        'score': score,
        'trend_bias': trend_bias,
        'linreg_bias': linreg_bias,
        'momentum': momentum,
        'regime': regime,
        'ema300_position': latest.get('ema300_position', 'AT') or 'AT',
        'linreg_direction': linreg_dir,
        'linreg_alignment': linreg_align,
        'linreg_1m': latest.get('linreg_1m_slope', 0.0) or 0.0,
        'linreg_5m': latest.get('linreg_5m_slope', 0.0) or 0.0,
        'linreg_15m': latest.get('linreg_15m_slope', 0.0) or 0.0,
        'linreg_1h': latest.get('linreg_1h_slope', 0.0) or 0.0,
        'volume_regime': latest.get('volume_regime', 'NORMAL') or 'NORMAL',
        'velocity': latest.get('velocity_state', 'SLOW') or 'SLOW',
        'trend_quality': latest.get('trend_quality', 'WEAK') or 'WEAK',
        'wyckoff': latest.get('wyckoff_phase', 'UNKNOWN') or 'UNKNOWN',
        'freshness': freshness,
        'available': True,
    }


def get_trend_boost(direction: str, ctx: Optional[dict] = None) -> float:
    """
    Get a confidence boost (0.0 to 0.15) for a signal direction based on BTC context.
    
    When BTC is trending strongly in the same direction as the signal,
    we add up to 15% confidence. When against the trend, we subtract.
    
    This is the simplest integration point — call this from any signal
    to align with BTC's macro trend.
    
    Args:
        direction: 'LONG' or 'SHORT'
        ctx: pre-fetched context dict, or None to fetch fresh
    
    Returns:
        float: confidence modifier, -0.10 to +0.15
    """
    if ctx is None:
        ctx = get_btc_trend_context()
    
    if not ctx.get('available', False):
        return 0.0
    
    # Use linreg_bias as the primary signal (most reliable trendline)
    bias = ctx['linreg_bias']
    
    # Also factor in score momentum for timing
    momentum = ctx['momentum']
    
    # Combined bias: 70% trendlines, 30% momentum
    combined = bias * 0.7 + momentum * 0.3
    
    if direction == 'LONG':
        if combined > 0:
            # BTC is bullish — boost LONG
            return min(0.15, combined * 0.15)
        else:
            # BTC is bearish — penalize LONG
            return max(-0.10, combined * 0.10)
    elif direction == 'SHORT':
        if combined < 0:
            # BTC is bearish — boost SHORT
            return min(0.15, abs(combined) * 0.15)
        else:
            # BTC is bullish — penalize SHORT
            return max(-0.10, -combined * 0.10)
    
    return 0.0


def get_btc_regime_for_volatility_gate() -> str:
    """
    Map continuum state to a regime string compatible with volatility_gate.
    
    Returns: 'BULL_TREND', 'BEAR_TREND', 'RANGING', 'TRANSITIONING'
    """
    ctx = get_btc_trend_context()
    return ctx.get('regime', 'RANGING')


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    ctx = get_btc_trend_context()
    print(f"=== BTC Continuum Context ===")
    print(f"Score:        {ctx['score']:.1f}/100")
    print(f"Trend Bias:   {ctx['trend_bias']:+.2f}  (-1 bear ↔ +1 bull)")
    print(f"Linreg Bias:  {ctx['linreg_bias']:+.2f}  (trendlines)")
    print(f"Momentum:     {ctx['momentum']:+.2f}  (-1 falling ↔ +1 rising)")
    print(f"Regime:       {ctx['regime']}")
    print(f"EMA300:       {ctx['ema300_position']}")
    print(f"Linreg Dir:   {ctx['linreg_direction']} (alignment={ctx['linreg_alignment']:.0%})")
    print(f"Linreg 1m:    {ctx['linreg_1m']:.4f}")
    print(f"Linreg 5m:    {ctx['linreg_5m']:.4f}")
    print(f"Linreg 15m:   {ctx['linreg_15m']:.4f}")
    print(f"Linreg 1h:    {ctx['linreg_1h']:.4f}")
    print(f"Volume:       {ctx['volume_regime']}")
    print(f"Velocity:     {ctx['velocity']}")
    print(f"Trend Qual:   {ctx['trend_quality']}")
    print(f"Wyckoff:      {ctx['wyckoff']}")
    print(f"Freshness:    {ctx['freshness']:.0f}s ago")
    print(f"Available:    {ctx['available']}")
    print()
    
    long_boost = get_trend_boost('LONG', ctx)
    short_boost = get_trend_boost('SHORT', ctx)
    print(f"LONG confidence boost:  {long_boost:+.1%}")
    print(f"SHORT confidence boost: {short_boost:+.1%}")
