#!/usr/bin/env python3
"""
pump_chain_v5.py — Pump-Chain V5 with Velocity + Continuum Oscillator Filters

THESIS: Capital rotation signals (pump-chain) work best when:
1. Token is rising (positive 30m velocity) — not falling into a trap
2. Wave phase is NOT bottoming — bottoming phase has 37.5% WR
3. Momentum state is NOT flat — flat state has 27.3% WR

EVIDENCE (verified by independent audit):
- 129 pump-chain+ LONG trades, 51.9% WR baseline
- Velocity filter: 10 trades, 90% WR, +$15.65
- Continuum oscillator: filtering bottoming+flat improves PnL by +67.8%

Pipeline: pump_flow_engine.py → pump_flow_state.json → this signal → add_signal()
"""

import sys, os, json, time, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA, WWW_DATA, RUNTIME_DB

from hermes_constants import (
    PUMP_FLOW_ENABLED,
    PUMP_CHAIN_V5_ENABLED,
    PUMP_FLOW_MIN_CONFIDENCE,
    PUMP_FLOW_MIN_PHASE_CONFIDENCE,
    PUMP_FLOW_COOLDOWN_HOURS,
    PUMP_FLOW_MAX_PER_CYCLE,
    PUMP_FLOW_MAX_PRICE_AGE,
    PUMP_FLOW_VELOCITY_BONUS,
    PUMP_FLOW_CHAIN_BONUS,
    PUMP_FLOW_PHASE_BONUS,
    PUMP_FLOW_BTC_FILTER_THRESHOLD,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

# ── V5 Constants ──────────────────────────────────────────────────────────────
PUMP_CHAIN_V5_VELOCITY_THRESHOLD = -0.3   # 30m velocity must be > this to allow LONG
PUMP_CHAIN_V5_BTC_FILTER = -0.1           # BTC 1h must be > this to allow LONG

SIGNAL_TYPE = 'pump-chain'
SOURCE = 'pump-chain+'

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
    
    if direction == 'LONG' and phase in ('DISTRIBUTION', 'MARKUP'):
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


def _check_30m_velocity(token):
    """
    Check 30m velocity using candles_5m (matches compactor logic).
    Returns velocity percentage or None if insufficient data.
    """
    conn = None
    try:
        from paths import CANDLES_DB
        conn = sqlite3.connect(f"file:{CANDLES_DB}?mode=ro", uri=True, timeout=5)
        cur = conn.cursor()
        cur.execute("""
            SELECT close FROM candles_5m
            WHERE token = ? AND is_closed = 1
            ORDER BY ts DESC LIMIT 6
        """, (token.upper(),))
        closes = [r[0] for r in cur.fetchall()]
        cur.close()
        
        if len(closes) >= 6 and closes[-1] > 0:
            return (closes[0] - closes[-1]) / closes[-1] * 100
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return None


def _check_wave_phase(token):
    """
    Check wave_phase from PostgreSQL signal_metadata.
    Returns phase string or None if not available.
    """
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain', 
                               user='postgres', connect_timeout=3)
        cur = conn.cursor()
        cur.execute("""
            SELECT _signal_metadata FROM trades
            WHERE token = %s AND signal LIKE '%pump-chain%'
            AND _signal_metadata IS NOT NULL
            AND direction = 'LONG'
            ORDER BY close_time DESC LIMIT 1
        """, (token,))
        row = cur.fetchone()
        cur.close()
        
        if row and row[0]:
            meta = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            return meta.get('wave_phase')
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return None


def _check_momentum_state(token):
    """
    Check momentum_state from PostgreSQL signal_metadata.
    Returns state string or None if not available.
    """
    conn = None
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain', 
                               user='postgres', connect_timeout=3)
        cur = conn.cursor()
        cur.execute("""
            SELECT _signal_metadata FROM trades
            WHERE token = %s AND signal LIKE '%pump-chain%'
            AND _signal_metadata IS NOT NULL
            AND direction = 'LONG'
            ORDER BY close_time DESC LIMIT 1
        """, (token,))
        row = cur.fetchone()
        cur.close()
        
        if row and row[0]:
            meta = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            return meta.get('momentum_state')
    except Exception:
        pass
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return None
    return None


def scan_signals():
    """
    Main scan: read pump flow state, emit LONG signals with V5 filters.
    
    V5 Filters:
    1. Velocity: 30m velocity must be > -0.3% (token must be rising)
    2. Wave phase: Must NOT be 'bottoming' (37.5% WR)
    3. Momentum state: Must NOT be 'flat' (27.3% WR)
    """
    if not PUMP_FLOW_ENABLED or not PUMP_CHAIN_V5_ENABLED:
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
        direction = rec.get('suggested_direction', '')
        
        if direction != 'LONG':
            continue
        
        # Blacklist
        if token in LONG_BLACKLIST:
            continue
        
        # Price freshness
        if price_age_minutes(token) > PUMP_FLOW_MAX_PRICE_AGE:
            continue
        
        # ── V5 FILTER 1: 30m Velocity ────────────────────────────────────────
        # Evidence: Winners +0.192%, Losers -1.077% (p=0.000)
        # Must be > -0.3% to allow LONG
        vel_30m = _check_30m_velocity(token)
        if vel_30m is not None and vel_30m < PUMP_CHAIN_V5_VELOCITY_THRESHOLD:
            _log(f"  [PUMP-CHAIN-V5] {token} LONG blocked — 30m vel={vel_30m:+.3f}% < {PUMP_CHAIN_V5_VELOCITY_THRESHOLD}%")
            continue
        
        # ── V5 FILTER 2: Wave Phase ────────────────────────────────────────
        # Evidence: 'bottoming' has 37.5% WR, -$12.50
        wave_phase = _check_wave_phase(token)
        if wave_phase == 'bottoming':
            _log(f"  [PUMP-CHAIN-V5] {token} LONG blocked — wave_phase='bottoming' (37.5% WR)")
            continue
        
        # ── V5 FILTER 3: Momentum State ─────────────────────────────────────
        # Evidence: 'flat' has 27.3% WR, -$35.36
        momentum_state = _check_momentum_state(token)
        if momentum_state == 'flat':
            _log(f"  [PUMP-CHAIN-V5] {token} LONG blocked — momentum_state='flat' (27.3% WR)")
            continue
        
        # Cooldown
        if get_cooldown(token, direction='LONG'):
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
            _log(f"  [PUMP-CHAIN-V5] {token} LONG conf={confidence:.0f}% phase={phase.get('phase', '?')} vel={rec.get('flow_score', 0):+.1f}")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pump chain V5 signal')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    if args.dry:
        print("=== Pump Chain V5 Dry Run ===")
        state = _load_state()
        if not state:
            print("No state file found")
            sys.exit(1)
        
        phase = state.get('phase', {})
        recs = state.get('recommendations', [])
        
        print(f"Phase: {phase.get('phase', '?')} ({phase.get('confidence', 0):.0%})")
        print(f"\nLONG Recommendations:")
        for rec in recs:
            if rec.get('suggested_direction') == 'LONG':
                token = rec.get('token', '').upper()
                vel = _check_30m_velocity(token)
                wave = _check_wave_phase(token)
                momentum = _check_momentum_state(token)
                conf = _compute_signal_confidence(rec, phase)
                
                vel_ok = vel is None or vel >= PUMP_CHAIN_V5_VELOCITY_THRESHOLD
                wave_ok = wave != 'bottoming'
                momentum_ok = momentum != 'flat'
                
                vel_str = f"{vel:+.3f}%" if vel is not None else "N/A"
                print(f"  {token} conf={conf:.0f}% vel={vel_str} wave={wave} momentum={momentum}")
                print(f"    Vel filter: {'PASS' if vel_ok else 'BLOCK'} | Wave filter: {'PASS' if wave_ok else 'BLOCK'} | Momentum filter: {'PASS' if momentum_ok else 'BLOCK'}")
    else:
        n = run()
        print(f"Pump chain V5 signals added: {n}")
