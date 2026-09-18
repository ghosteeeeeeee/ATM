#!/usr/bin/env python3
"""
pump_chain_v4.py — Capital Rotation LONG Signal with BTC Oscillator Filter

Upgraded pump-chain LONG signal with BTC oscillator-based filtering.
Blocks LONG at extreme BTC bullish (80-100) where pump-chain chases exhaustion.
Boosts confidence in sweet spot (40-80) where pump-chain works.

Architecture:
  pump_flow_engine.py → pump_flow_state.json → this signal reads state
  + BTC oscillator from continuum.db → filters based on score/linreg
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset → guardian

Signal type: pump-chain
Source: pump-chain+

Thesis: pump-chain is a MEAN-REVERSION signal (not momentum).
- Works in downtrend (BTC 0-40): pumping coins are genuine breakouts
- Fails in strong bull (BTC 80-100): pumping coins chase exhaustion
- Linreg BEAR is sweet spot: downtrend confirms genuine breakouts

Pipeline: runs as a slow signal (every 5 minutes) via signals_runner.

Author: Hermes Trading System
Created: 2026-09-18
"""

import sys, os, json, time, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA, WWW_DATA

from hermes_constants import (
    PUMP_FLOW_ENABLED,
    PUMP_FLOW_PLUS_ENABLED,
    PUMP_FLOW_MIN_CONFIDENCE,
    PUMP_FLOW_MIN_PHASE_CONFIDENCE,
    PUMP_FLOW_COOLDOWN_HOURS,
    PUMP_FLOW_MAX_PER_CYCLE,
    PUMP_FLOW_MAX_PRICE_AGE,
    PUMP_FLOW_VELOCITY_BONUS,
    PUMP_FLOW_CHAIN_BONUS,
    PUMP_FLOW_PHASE_BONUS,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE  = 'pump-chain'
SOURCE       = 'pump-chain+'

STATE_FILE = os.path.join(HERMES_DATA, 'pump_flow_state.json')
FULL_STATE_FILE = os.path.join(WWW_DATA, 'pump_flow_data.json')
CONTINUUM_DB = os.path.join(HERMES_DATA, 'continuum.db')

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'

# ── BTC Oscillator Thresholds (from 14-day analysis) ────────────────────────
# pump-chain LONG is mean-reversion — works in downtrend, fails at extremes
BTC_SCORE_BLOCK_ABOVE = 80      # Block LONG when BTC > 80 (chasing exhaustion)
BTC_SCORE_BOOST_LOW = 40        # Boost when BTC 40-80 (sweet spot)
BTC_SCORE_BOOST_HIGH = 80       # Boost when BTC 40-80 (sweet spot)
BTC_LINREG_BLOCK_BULL = True    # Block LONG when Linreg BULL (chasing)


def _log(msg):
    print(msg)
    try:
        with open(SIGNAL_LOG, 'a') as f:
            f.write(msg + '\n')
    except Exception:
        pass


def _load_state():
    """Load pump flow state — prefer full data file, fall back to compact."""
    for path in (FULL_STATE_FILE, STATE_FILE):
        try:
            with open(path) as f:
                data = json.load(f)
            # Normalize compact format
            if isinstance(data.get('phase'), str):
                data['phase'] = {
                    'phase': data['phase'],
                    'confidence': data.get('phase_confidence', 0),
                    'alt_signal': data.get('alt_signal', 'neutral'),
                    'reason': '',
                }
            # Normalize recommendations
            recs = data.get('recommendations', [])
            for rec in recs:
                if 'suggested_direction' not in rec and 'direction' in rec:
                    rec['suggested_direction'] = rec['direction']
                rec.setdefault('flow_score', 0)
                rec.setdefault('chain_evidence', [])
            return data
        except Exception:
            continue
    return None


def _get_btc_oscillator():
    """Get current BTC oscillator state from continuum.db."""
    try:
        conn = sqlite3.connect(CONTINUUM_DB, timeout=5)
        row = conn.execute('''
            SELECT state_score, linreg_direction, linreg_alignment, 
                   trend_quality, zscore_val
            FROM continuum_states
            WHERE token = 'BTC'
            ORDER BY ts DESC
            LIMIT 1
        ''').fetchone()
        conn.close()
        
        if not row:
            return None
        
        score, linreg_dir, linreg_align, trend, zscore = row
        
        # Classify linreg bias
        if linreg_dir and 'BULL' in str(linreg_dir).upper():
            linreg_bias = 'BULL'
        elif linreg_dir and 'BEAR' in str(linreg_dir).upper():
            linreg_bias = 'BEAR'
        else:
            linreg_bias = 'MIXED'
        
        return {
            'score': float(score) if score else 50,
            'linreg_bias': linreg_bias,
            'trend': trend,
            'zscore': float(zscore) if zscore else 0,
        }
    except Exception as e:
        _log(f"  [WARN] BTC oscillator check failed: {e}")
        return None


def _compute_signal_confidence(recommendation, phase_data, btc_state=None):
    """Compute signal confidence from recommendation + phase + BTC oscillator."""
    base = recommendation.get('confidence', 0) * 100
    
    flow_score = abs(recommendation.get('flow_score', 0))
    vel_bonus = min(12, int(flow_score / 2) * PUMP_FLOW_VELOCITY_BONUS)
    
    chains = recommendation.get('chain_evidence', [])
    chain_bonus = min(10, len(chains) * PUMP_FLOW_CHAIN_BONUS)
    
    phase_bonus = 0
    direction = recommendation.get('suggested_direction', '')
    phase = phase_data.get('phase', '')
    
    if direction == 'LONG' and phase in ('DISTRIBUTION', 'MARKUP'):
        phase_bonus = PUMP_FLOW_PHASE_BONUS
    
    phase_conf_bonus = 5 if phase_data.get('confidence', 0) > 0.6 else 0
    
    raw = base + vel_bonus + chain_bonus + phase_bonus + phase_conf_bonus
    
    # ── BTC Oscillator Adjustment ──────────────────────────────────────────
    btc_mult = 1.0
    if btc_state and direction == 'LONG':
        score = btc_state['score']
        linreg = btc_state['linreg_bias']
        
        # Block at extreme bullish (chasing exhaustion)
        if score > BTC_SCORE_BLOCK_ABOVE:
            btc_mult = 0.3  # Heavy penalty
            _log(f"  🚫 [BTC-OSC] LONG penalty: BTC score {score:.0f} > {BTC_SCORE_BLOCK_ABOVE} (chasing exhaustion)")
        
        # Boost in sweet spot (40-80)
        elif BTC_SCORE_BOOST_LOW <= score <= BTC_SCORE_BOOST_HIGH:
            btc_mult = 1.15  # Mild boost
            _log(f"  ✅ [BTC-OSC] LONG boost: BTC score {score:.0f} in sweet spot ({BTC_SCORE_BOOST_LOW}-{BTC_SCORE_BOOST_HIGH})")
        
        # Block when Linreg BULL (chasing)
        if BTC_LINREG_BLOCK_BULL and linreg == 'BULL':
            btc_mult *= 0.7  # Additional penalty
            _log(f"  🚫 [BTC-OSC] LONG penalty: Linreg BULL (chasing)")
    
    raw *= btc_mult
    
    return max(0, min(100, round(raw)))


def _format_chain_evidence(chains):
    """Format chain evidence for signal source tag."""
    if not chains:
        return ''
    parts = []
    for c in chains[:3]:
        ref = c.get('leader') or c.get('follower', '?')
        parts.append(f"{ref}({c['lift']}x)")
    return ','.join(parts)


def scan_signals():
    """
    Main scan: read pump flow state, emit LONG signals with BTC oscillator filter.
    
    v4 upgrade: blocks LONG at BTC > 80, boosts in sweet spot (40-80).
    """
    if not PUMP_FLOW_ENABLED or not PUMP_FLOW_PLUS_ENABLED:
        return 0
    
    state = _load_state()
    if not state:
        return 0
    
    phase = state.get('phase', {})
    recommendations = state.get('recommendations', [])
    
    if phase.get('confidence', 0) < PUMP_FLOW_MIN_PHASE_CONFIDENCE:
        return 0
    
    # Get BTC oscillator state
    btc_state = _get_btc_oscillator()
    
    added = 0
    
    for rec in recommendations:
        if added >= PUMP_FLOW_MAX_PER_CYCLE:
            break
        
        token = rec.get('token', '').upper()
        direction = rec.get('suggested_direction', '')
        
        if direction != 'LONG':
            continue
        
        if token in LONG_BLACKLIST:
            continue
        
        if price_age_minutes(token) > PUMP_FLOW_MAX_PRICE_AGE:
            continue

        # Block stale entries
        try:
            _conn_spd = sqlite3.connect(os.path.join(HERMES_DATA, 'signals_hermes_runtime.db'), timeout=5)
            _cur_spd = _conn_spd.cursor()
            _cur_spd.execute('SELECT is_stale FROM token_speeds WHERE token = ?', (token.upper(),))
            _row = _cur_spd.fetchone()
            if _row and _row[0]:
                _log(f"  [PUMP-CHAIN-V4] SKIP {token} — stale entry")
                if _conn_spd:
                    _conn_spd.close()
                continue
        except Exception:
            pass
        finally:
            try:
                if _conn_spd:
                    _conn_spd.close()
            except Exception:
                pass

        if get_cooldown(token, direction='LONG'):
            continue
        
        confidence = _compute_signal_confidence(rec, phase, btc_state)
        
        if confidence < PUMP_FLOW_MIN_CONFIDENCE:
            continue
        
        price_data = {}
        try:
            from signal_schema import get_all_latest_prices
            all_prices = get_all_latest_prices()
            price_data = all_prices.get(token, {})
        except Exception:
            pass
        
        price = price_data.get('price') if isinstance(price_data, dict) else None
        if price is None or price <= 0:
            continue
        
        chains = rec.get('chain_evidence', [])
        chain_str = _format_chain_evidence(chains)
        
        source = SOURCE
        if chain_str:
            source += f',chain({chain_str})'
        
        sid = add_signal(
            token=token,
            direction='LONG',
            signal_type=SIGNAL_TYPE,
            source=source,
            confidence=confidence,
            value=rec.get('flow_score', 0),
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        
        if sid:
            added += 1
            set_cooldown(token, 'LONG', hours=PUMP_FLOW_COOLDOWN_HOURS)
            _log(f"  [PUMP-CHAIN-V4] {token:10s} conf={confidence:.0f}% phase={phase.get('phase', '?')} btc={btc_state.get('score', '?') if btc_state else '?'}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pump chain V4 LONG signal (BTC oscillator filtered)')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    if args.dry:
        print("=== Pump Chain V4 LONG Dry Run ===")
        state = _load_state()
        if not state:
            print("No state file found")
            sys.exit(1)
        
        phase = state.get('phase', {})
        recs = state.get('recommendations', [])
        btc = _get_btc_oscillator()
        
        print(f"Phase: {phase.get('phase', '?')} ({phase.get('confidence', 0):.0%})")
        if btc:
            print(f"BTC: score={btc['score']:.0f} linreg={btc['linreg_bias']} trend={btc['trend']}")
        else:
            print("BTC: no data")
        
        print(f"\nLONG Recommendations:")
        for rec in recs:
            if rec.get('suggested_direction') == 'LONG':
                conf = _compute_signal_confidence(rec, phase, btc)
                print(f"  {rec['token']:10s} conf={conf:.0f}% vel={rec.get('flow_score', 0):+.1f}")
    else:
        n = run()
        print(f"Pump chain V4 LONG signals added: {n}")
