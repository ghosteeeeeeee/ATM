#!/usr/bin/env python3
"""
pump_flow_signal.py — Capital Rotation Flow Signal

Reads the pump flow engine state and emits trade signals when:
1. Phase is DISTRIBUTION (capital rotating to alts) + strong chain evidence
2. Phase is MARKUP (BTC pumping) + spillover detected into specific tokens
3. Phase is MARKDOWN (capital fleeing) + short opportunities on alt chain followers

Architecture:
  pump_flow_engine.py → pump_flow_state.json → this signal reads state
  → add_signal() → signals_hermes_runtime.db → signal_compactor → hotset → guardian

Signal types:
  - pump_flow_long  : capital rotation LONG
  - pump_flow_short : capital rotation SHORT

Pipeline: runs as a slow signal (every 5 minutes) via signals_runner.
"""

import sys, os, json, time, sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown
from paths import HERMES_DATA, WWW_DATA

from hermes_constants import (
    PUMP_FLOW_ENABLED,
    PUMP_FLOW_PLUS_ENABLED,
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

SIGNAL_TYPE_LONG  = 'pump_flow_long'
SIGNAL_TYPE_SHORT = 'pump_flow_short'
SOURCE_LONG       = 'pump-flow+'
SOURCE_SHORT      = 'pump-flow-'

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
    """Load pump flow state — prefer full data file, fall back to compact.

    Normalizes compact file format:
      - phase as string → phase as dict
      - direction → suggested_direction
      - Missing flow_score/chain_evidence → defaults
    Rejects stale data (>10 min old).
    """
    now = time.time()
    MAX_STATE_AGE_SECS = 600  # 10 minutes

    # Try full data file first (has complete phase dict with suggested_direction)
    for path in (FULL_STATE_FILE, STATE_FILE):
        try:
            with open(path) as f:
                data = json.load(f)

            # Staleness check
            ts_str = data.get('updated_at') or data.get('stats', {}).get('generated_at', '')
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    age_secs = (datetime.now(timezone.utc) - ts).total_seconds()
                    if age_secs > MAX_STATE_AGE_SECS:
                        _log(f"  [pump-flow] State file stale ({age_secs:.0f}s old, max {MAX_STATE_AGE_SECS}s)")
                        continue
                except Exception:
                    pass  # if we can't parse timestamp, accept the data

            # Normalize phase: compact file has phase as string
            if isinstance(data.get('phase'), str):
                data['phase'] = {
                    'phase': data['phase'],
                    'confidence': data.get('phase_confidence', 0),
                    'alt_signal': data.get('alt_signal', 'neutral'),
                    'reason': '',
                }

            # Normalize recommendations: compact uses 'direction', full uses 'suggested_direction'
            recs = data.get('recommendations', [])
            for rec in recs:
                if 'suggested_direction' not in rec and 'direction' in rec:
                    rec['suggested_direction'] = rec['direction']
                # Ensure flow_score and chain_evidence exist (missing in compact)
                rec.setdefault('flow_score', 0)
                rec.setdefault('chain_evidence', [])

            return data
        except Exception:
            continue

    _log(f"  [pump-flow] No valid state file found")
    return None


def _get_current_price(token):
    """Get current price from latest_prices."""
    try:
        from signal_schema import get_all_latest_prices
        prices = get_all_latest_prices()
        data = prices.get(token.upper())
        if data and data.get('price') and data['price'] > 0:
            return data['price']
    except Exception:
        pass
    return None


def _compute_signal_confidence(recommendation, phase_data):
    """
    Compute signal confidence from recommendation + phase context.
    
    Base: recommendation confidence (0-1)
    Bonuses:
      - Velocity bonus: +3 per 0.1% velocity (up to +12)
      - Chain bonus: +2 per chain evidence link (up to +10)
      - Phase bonus: +5 if signal direction aligns with phase
      - Phase confidence bonus: +5 if phase confidence > 0.6
    
    Returns confidence in 0-100 range.
    """
    base = recommendation.get('confidence', 0) * 100
    
    # Velocity bonus
    flow_score = abs(recommendation.get('flow_score', 0))
    vel_bonus = min(12, int(flow_score / 2) * PUMP_FLOW_VELOCITY_BONUS)
    
    # Chain evidence bonus
    chains = recommendation.get('chain_evidence', [])
    chain_bonus = min(10, len(chains) * PUMP_FLOW_CHAIN_BONUS)
    
    # Phase alignment bonus
    phase_bonus = 0
    direction = recommendation.get('suggested_direction', '')
    phase = phase_data.get('phase', '')
    alt_signal = phase_data.get('alt_signal', '')
    
    if direction == 'LONG' and phase in ('DISTRIBUTION', 'MARKUP'):
        phase_bonus = PUMP_FLOW_PHASE_BONUS
    elif direction == 'SHORT' and phase in ('MARKDOWN', 'DISTRIBUTION'):
        phase_bonus = PUMP_FLOW_PHASE_BONUS
    
    # Phase confidence bonus
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
        parts.append(f"{ref}({c['lift']}x)")
    return ','.join(parts)


def scan_signals():
    """
    Main scan: read pump flow state, emit signals for high-confidence recommendations.
    
    Returns number of signals added.
    """
    if not PUMP_FLOW_ENABLED:
        return 0
    
    # Load state
    state = _load_state()
    if not state:
        return 0
    
    phase = state.get('phase', {})
    recommendations = state.get('recommendations', [])
    
    # Phase must meet minimum confidence
    if phase.get('confidence', 0) < PUMP_FLOW_MIN_PHASE_CONFIDENCE:
        _log(f"  [pump-flow] Phase confidence too low: {phase.get('confidence', 0):.2f}")
        return 0
    
    added = 0
    
    # Hoist price lookup outside loop — one fetch for all recommendations
    try:
        from signal_schema import get_all_latest_prices
        all_prices = get_all_latest_prices()
    except Exception:
        all_prices = {}
    
    for rec in recommendations:
        if added >= PUMP_FLOW_MAX_PER_CYCLE:
            break
        
        token = rec.get('token', '').upper()
        direction = rec.get('suggested_direction', '')
        
        # Skip WAIT signals
        if direction == 'WAIT':
            continue
        
        # Validate direction
        if direction not in ('LONG', 'SHORT'):
            continue
        
        # Per-direction kill-switch
        if direction == 'LONG' and not PUMP_FLOW_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not PUMP_FLOW_MINUS_ENABLED:
            continue
        
        # Blacklist
        if direction == 'LONG' and token in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token in SHORT_BLACKLIST:
            continue
        
        # Price freshness
        if price_age_minutes(token) > PUMP_FLOW_MAX_PRICE_AGE:
            continue
        
        # Cooldown
        if get_cooldown(token, direction=direction):
            continue
        
        # Compute confidence
        confidence = _compute_signal_confidence(rec, phase)
        
        # Confidence threshold
        if confidence < PUMP_FLOW_MIN_CONFIDENCE:
            _log(f"  [pump-flow] {token} {direction} conf={confidence} < {PUMP_FLOW_MIN_CONFIDENCE} [skip]")
            continue
        
        # Get price from pre-fetched lookup
        price_data = all_prices.get(token, {})
        price = price_data.get('price') if isinstance(price_data, dict) else None
        if price is None or price <= 0:
            continue
        
        # Chain evidence for value
        chains = rec.get('chain_evidence', [])
        chain_str = _format_chain_evidence(chains)
        
        # Signal type and source
        sig_type = SIGNAL_TYPE_LONG if direction == 'LONG' else SIGNAL_TYPE_SHORT
        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
        if chain_str:
            source += f',chain({chain_str})'
        
        # Fire signal
        sid = add_signal(
            token=token,
            direction=direction,
            signal_type=sig_type,
            source=source,
            confidence=confidence,
            value=rec.get('flow_score', 0),
            price=price,
            exchange='hyperliquid',
            timeframe='5m',
        )
        
        if sid:
            added += 1
            set_cooldown(token, direction, hours=PUMP_FLOW_COOLDOWN_HOURS)
            
            chain_summary = f" chains=[{chain_str}]" if chain_str else ""
            _log(
                f"  [PUMP-FLOW] {token:10s} {direction:5s} "
                f"conf={confidence:.0f}% "
                f"phase={phase.get('phase', '?')}({phase.get('confidence', 0):.0%}) "
                f"vel={rec.get('flow_score', 0):+.1f}"
                f"{chain_summary}"
            )
    
    if added > 0:
        _log(f"  [pump-flow] {added} signals emitted (phase={phase.get('phase', '?')})")
    
    return added


def run():
    """Entry point for signals_runner."""
    return scan_signals()


if __name__ == '__main__':
    # CLI: dry run
    import argparse
    parser = argparse.ArgumentParser(description='Pump flow signal')
    parser.add_argument('--dry', action='store_true', help='Dry run (show what would fire)')
    args = parser.parse_args()
    
    if args.dry:
        print("=== Pump Flow Signal Dry Run ===")
        state = _load_state()
        if not state:
            print("No state file found. Run pump_flow_engine.py first.")
            sys.exit(1)
        
        phase = state.get('phase', {})
        recs = state.get('recommendations', [])
        
        print(f"Phase: {phase.get('phase', '?')} ({phase.get('confidence', 0):.0%})")
        print(f"Reason: {phase.get('reason', '?')}")
        print(f"Alt signal: {phase.get('alt_signal', '?')}")
        print(f"\nRecommendations: {len(recs)}")
        
        for rec in recs:
            if rec.get('suggested_direction') == 'WAIT':
                continue
            conf = _compute_signal_confidence(rec, phase)
            chains = rec.get('chain_evidence', [])
            chain_str = _format_chain_evidence(chains)
            print(f"  {rec['suggested_direction']:6s} {rec['token']:10s} "
                  f"conf={conf:.0f}% "
                  f"vel={rec.get('flow_score', 0):+.1f} "
                  f"chains=[{chain_str}] "
                  f"— {rec.get('reason', '')[:60]}")
    else:
        n = run()
        print(f"Pump flow signals added: {n}")
