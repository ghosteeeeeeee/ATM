#!/usr/bin/env python3
"""
pump_chain_v5_short.py — Pump-Chain V5 SHORT with Evidence-Based Filters

THESIS: Pump-chain SHORT signals work best when:
1. NOT accelerating+rising — 0% WR (0W 2L), entering into strength
2. NOT falling+flat+BB>0.4 — 0% WR (0W 2L), entering at resistance

EVIDENCE (verified by independent audit, 63 SHORT trades):
- Baseline: 36W 24L, 60.0% WR, +$0.25 PnL
- accel+rising filter: catches INJ -$0.27, ARB -$0.13 (0 kills)
- falling+flat+BB>0.4 filter: catches BCH -$0.12, ENA -$0.16 (0 kills)
- COMBO: 4 losses caught, 0 wins killed, WR 64.3%, PnL +$0.93

Pipeline: pump_flow_engine.py → pump_flow_state.json → this signal → add_signal()
"""

import sys, os, json, time, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA, WWW_DATA, RUNTIME_DB

from hermes_constants import (
    PUMP_FLOW_ENABLED,
    PUMP_FLOW_MINUS_ENABLED,
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

SIGNAL_TYPE = 'pump-chain'
SOURCE = 'pump-chain-'

STATE_FILE = os.path.join(HERMES_DATA, 'pump_flow_state.json')
FULL_STATE_FILE = os.path.join(WWW_DATA, 'pump_flow_data.json')

SIGNAL_LOG = '/var/www/hermes/logs/signals.log'


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


def _compute_signal_confidence(recommendation, phase_data):
    """Compute signal confidence from recommendation + phase context."""
    base = recommendation.get('confidence', 0) * 100
    
    flow_score = abs(recommendation.get('flow_score', 0))
    vel_bonus = min(12, int(flow_score / 2) * PUMP_FLOW_VELOCITY_BONUS)
    
    chains = recommendation.get('chain_evidence', [])
    chain_bonus = min(10, len(chains) * PUMP_FLOW_CHAIN_BONUS)
    
    phase_bonus = 0
    direction = recommendation.get('suggested_direction', '')
    phase = phase_data.get('phase', '')
    
    if direction == 'SHORT' and phase in ('MARKDOWN', 'DISTRIBUTION'):
        phase_bonus = PUMP_FLOW_PHASE_BONUS
    
    phase_conf_bonus = 5 if phase_data.get('confidence', 0) > 0.6 else 0
    
    raw = base + vel_bonus + chain_bonus + phase_bonus + phase_conf_bonus
    return max(0, min(100, round(raw)))


def _format_chain_evidence(chains):
    """Format chain evidence for signal source tag."""
    if not chains:
        return ''
    parts = []
    for c in chains[:3]:
        ref = c.get('leader') or c.get('follower', '?')
        parts.append(f"{ref}({c.get('lift', '?')}x)")
    return ','.join(parts)


def _get_signal_metadata(token):
    """
    Get latest signal metadata from PostgreSQL for a token.
    Returns dict with wave_phase, momentum_state, bb_position, etc.
    """
    conn = None
    try:
        import psycopg2
        from _secrets import BRAIN_DB_DICT
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute("""
            SELECT _signal_metadata FROM trades
            WHERE token = %s AND signal LIKE '%pump-chain%'
            AND _signal_metadata IS NOT NULL
            AND direction = 'SHORT'
            ORDER BY close_time DESC LIMIT 1
        """, (token,))
        row = cur.fetchone()
        cur.close()
        
        if row and row[0]:
            meta = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            return meta
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return {}


def scan_signals():
    """
    Main scan: read pump flow state, emit SHORT signals with V5 filters.
    
    V5 SHORT Filters (evidence-based, 0 wins killed):
    1. Block when wave_phase='accelerating' AND momentum_state='rising' (0% WR)
    2. Block when wave_phase='falling' AND momentum_state='flat' AND bb_position>0.4 (0% WR)
    """
    if not PUMP_FLOW_ENABLED or not PUMP_FLOW_MINUS_ENABLED:
        return 0
    
    state = _load_state()
    if not state:
        return 0
    
    phase = state.get('phase', {})
    recommendations = state.get('recommendations', [])
    
    if phase.get('confidence', 0) < PUMP_FLOW_MIN_PHASE_CONFIDENCE:
        return 0
    
    added = 0
    
    for rec in recommendations:
        if added >= PUMP_FLOW_MAX_PER_CYCLE:
            break
        
        token = rec.get('token', '').upper()
        direction = rec.get('direction', rec.get('suggested_direction', ''))
        
        if direction != 'SHORT':
            continue
        
        # Blacklist
        if token in SHORT_BLACKLIST:
            continue
        
        # Price freshness
        if price_age_minutes(token) > PUMP_FLOW_MAX_PRICE_AGE:
            continue
        
        # ── V5 FILTER 1: Accelerating + Rising Momentum ──────────────────────
        # Evidence: 0% WR (0W 2L), catches INJ -$0.27, ARB -$0.13
        meta = _get_signal_metadata(token)
        wave_phase = meta.get('wave_phase')
        momentum_state = meta.get('momentum_state')
        bb_position = meta.get('bb_position')
        
        if wave_phase == 'accelerating' and momentum_state == 'rising':
            _log(f"  [PUMP-CHAIN-V5-SHORT] {token} SHORT blocked — accelerating+rising (0% WR)")
            continue
        
        # ── V5 FILTER 2: Falling + Flat + High BB ───────────────────────────
        # Evidence: 0% WR (0W 2L), catches BCH -$0.12, ENA -$0.16
        if (wave_phase == 'falling' and momentum_state == 'flat' 
            and bb_position is not None and bb_position > 0.4):
            _log(f"  [PUMP-CHAIN-V5-SHORT] {token} SHORT blocked — falling+flat+BB>{bb_position:.2f} (0% WR)")
            continue
        
        # Cooldown
        if get_cooldown(token, direction='SHORT'):
            continue
        
        # Compute confidence
        confidence = _compute_signal_confidence(rec, phase)
        
        # Confidence threshold
        if confidence < PUMP_FLOW_MIN_CONFIDENCE:
            continue
        
        # Get price
        try:
            from signal_schema import get_all_latest_prices
            all_prices = get_all_latest_prices()
            price_data = all_prices.get(token, {})
            price = price_data.get('price') if isinstance(price_data, dict) else None
        except Exception:
            price = None
        
        if price is None or price <= 0:
            continue
        
        # Chain evidence
        chains = rec.get('chain_evidence', [])
        chain_str = _format_chain_evidence(chains)
        
        source = SOURCE
        
        # Fire signal
        sid = add_signal(
            token=token,
            direction='SHORT',
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
            set_cooldown(token, 'SHORT', hours=PUMP_FLOW_COOLDOWN_HOURS)
            chain_summary = f" chains=[{chain_str}]" if chain_str else ""
            _log(f"  [PUMP-CHAIN-V5-SHORT] {token} SHORT conf={confidence:.0f}% phase={phase.get('phase', '?')} vel={rec.get('flow_score', 0):+.1f}{chain_summary}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pump chain V5 SHORT signal')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    if args.dry:
        print("=== Pump Chain V5 SHORT Dry Run ===")
        state = _load_state()
        if not state:
            print("No state file found")
            sys.exit(1)
        
        phase = state.get('phase', {})
        recs = state.get('recommendations', [])
        
        print(f"Phase: {phase.get('phase', '?')} ({phase.get('confidence', 0):.0%})")
        print(f"\nSHORT Recommendations:")
        for rec in recs:
            d = rec.get('direction', rec.get('suggested_direction', ''))
            if d == 'SHORT':
                token = rec.get('token', '').upper()
                meta = _get_signal_metadata(token)
                wave = meta.get('wave_phase')
                momentum = meta.get('momentum_state')
                bb = meta.get('bb_position')
                conf = _compute_signal_confidence(rec, phase)
                
                # Check filters
                filter1 = wave == 'accelerating' and momentum == 'rising'
                filter2 = (wave == 'falling' and momentum == 'flat' 
                          and bb is not None and bb > 0.4)
                blocked = filter1 or filter2
                
                bb_str = f"{bb:.3f}" if bb is not None else "N/A"
                print(f"  {token} conf={conf:.0f}% wave={wave} mom={momentum} bb={bb_str}")
                if blocked:
                    reason = "accelerating+rising" if filter1 else f"falling+flat+BB>{bb:.2f}"
                    print(f"    BLOCKED: {reason}")
                else:
                    print(f"    PASS")
    else:
        n = run()
        print(f"Pump chain V5 SHORT signals added: {n}")
