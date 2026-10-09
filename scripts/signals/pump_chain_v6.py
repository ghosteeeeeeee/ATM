#!/usr/bin/env python3
"""
pump_chain_v6.py — Capital Rotation signal, both directions (audit-verified spec)

THESIS: capital rotates from leaders into laggards (pump-flow engine chain evidence);
the follower's move is real flow and continues — but only mid-cycle.

Gates (brain/specs/pump_chain_v6_spec.md rev1, double-audited 2026-10-08):
  LONG : block RSI(14) < 40  |  block momentum_state == 'flat'
  SHORT: block RSI(14) < 45  |  block momentum_state == 'flat'  (hygiene, not edge)
  RSI and momentum are computed by signal_schema._enrich_indicators — the EXACT same
  1-minute formula that produced the historical _signal_metadata labels the gates were
  validated against (zero calibration gap; see spec §4 G3/G4 + calibration script).

VALIDATION (extended family n=304, 60d):
  LONG gate: 43.7% WR +$2.59 -> 59.7% +$7.26; blocked 10W/32L -$3.44;
             Fisher p<0.001, permutation p=0.0001 (VALIDATED edge)
  SHORT gate: 53.5% WR +$1.40, blocked -$2.05; permutation p~0.05 (MONITORING BET —
             stricter kill criteria apply, see spec §9)

Architecture: pump_flow_engine.py -> pump_flow_data.json -> this signal -> add_signal()
  signal_type='pump-chain-v6' (independent outcome stats for decay detector + kill criteria)
  sources: 'pump-chain-v6+' / 'pump-chain-v6-' (fixed strings — chain evidence never in source)
  exits: SIGNAL_EXIT_CONFIG -> pump_exit (LONG) / rr_engine (SHORT)
  runs as a fast signal via signals_runner.
"""

import sys, os, json, sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signal_schema import add_signal, price_age_minutes, get_cooldown, set_cooldown, _enrich_indicators
from paths import HERMES_DATA, WWW_DATA

from hermes_constants import (
    PUMP_FLOW_ENABLED,
    PUMP_CHAIN_V6_ENABLED,
    PUMP_CHAIN_V6_PLUS_ENABLED,
    PUMP_CHAIN_V6_MINUS_ENABLED,
    PUMP_CHAIN_V6_LONG_RSI_MIN,
    PUMP_CHAIN_V6_SHORT_RSI_MIN,
    PUMP_CHAIN_V6_BLOCK_FLAT_MOMENTUM,
    PUMP_FLOW_MIN_CONFIDENCE,
    PUMP_FLOW_MIN_PHASE_CONFIDENCE,
    PUMP_FLOW_COOLDOWN_HOURS,
    PUMP_FLOW_MAX_PER_CYCLE,
    PUMP_FLOW_MAX_PRICE_AGE,
    LONG_BLACKLIST,
    SHORT_BLACKLIST,
)

SIGNAL_TYPE = 'pump-chain-v6'
SOURCE_LONG = 'pump-chain-v6+'
SOURCE_SHORT = 'pump-chain-v6-'

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
    (Reused logic from pump_chain_long — normalization kept identical.)"""
    for path in (FULL_STATE_FILE, STATE_FILE):
        try:
            with open(path) as f:
                data = json.load(f)
            if isinstance(data.get('phase'), str):
                data['phase'] = {
                    'phase': data['phase'],
                    'confidence': data.get('phase_confidence', 0),
                    'alt_signal': data.get('alt_signal', 'neutral'),
                    'reason': '',
                }
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
    """Ranking-only confidence (validated non-predictive at 90+; floor kept for sanity).
    Mirrors pump_chain_long's formula; magic numbers live in hermes_constants (AGENTS.md
    no-hardcoded-numbers rule; bug_hunter M3)."""
    from hermes_constants import (
        PUMP_FLOW_VELOCITY_BONUS, PUMP_FLOW_CHAIN_BONUS, PUMP_FLOW_PHASE_BONUS,
        PUMP_CHAIN_V6_VEL_BONUS_CAP, PUMP_CHAIN_V6_VEL_BONUS_DIVISOR,
        PUMP_CHAIN_V6_CHAIN_BONUS_CAP, PUMP_CHAIN_V6_PHASE_CONF_BONUS,
        PUMP_CHAIN_V6_PHASE_CONF_THRESHOLD,
    )
    base = recommendation.get('confidence', 0) * 100

    flow_score = abs(recommendation.get('flow_score', 0))
    vel_bonus = min(PUMP_CHAIN_V6_VEL_BONUS_CAP,
                    int(flow_score / PUMP_CHAIN_V6_VEL_BONUS_DIVISOR) * PUMP_FLOW_VELOCITY_BONUS)

    chains = recommendation.get('chain_evidence', [])
    chain_bonus = min(PUMP_CHAIN_V6_CHAIN_BONUS_CAP, len(chains) * PUMP_FLOW_CHAIN_BONUS)

    phase_bonus = 0
    direction = recommendation.get('suggested_direction', '')
    phase = phase_data.get('phase', '')
    if direction == 'LONG' and phase in ('DISTRIBUTION', 'MARKUP'):
        phase_bonus = PUMP_FLOW_PHASE_BONUS

    phase_conf_bonus = PUMP_CHAIN_V6_PHASE_CONF_BONUS if phase_data.get('confidence', 0) > PUMP_CHAIN_V6_PHASE_CONF_THRESHOLD else 0

    raw = base + vel_bonus + chain_bonus + phase_bonus + phase_conf_bonus
    return max(0, min(100, round(raw)))


def _format_chain_evidence(chains):
    """Format chain evidence for the audit log (spec §4: evidence is logged, never in source)."""
    if not chains:
        return 'none'
    parts = []
    for c in chains[:3]:
        ref = c.get('leader') or c.get('follower') or '?'
        parts.append(f"{ref}({c.get('lift', '?')}x)")
    return ','.join(parts)


def _check_token_speeds(token):
    """Return is_stale from token_speeds. Fail-open (None) if unavailable."""
    conn = None
    try:
        from paths import RUNTIME_DB
        conn = sqlite3.connect(f"file:{RUNTIME_DB}?mode=ro", uri=True, timeout=5)
        row = conn.execute(
            'SELECT is_stale FROM token_speeds WHERE token = ?', (token.upper(),)
        ).fetchone()
        return bool(row[0]) if row else None
    except Exception:
        return None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _gate_rsi_momentum(token, direction):
    """Apply G3 (RSI floor) + G4 (flat momentum block).

    RSI/momentum come from _enrich_indicators — the exact historical formula
    (1-minute price_history bars; RSI from candles_1m). Returns (allowed, reason).
    Fails OPEN on missing features (spec §2.4 / §10) with a DEBUG log.
    """
    try:
        enriched = _enrich_indicators(token) or {}
    except Exception as e:
        enriched = {}
        _log(f"  [PUMP-CHAIN-V6] {token} enrichment FAILED: {type(e).__name__}: {e} — failing open")

    rsi = enriched.get('rsi_14')
    floor = PUMP_CHAIN_V6_LONG_RSI_MIN if direction == 'LONG' else PUMP_CHAIN_V6_SHORT_RSI_MIN
    if rsi is None:
        _log(f"  [PUMP-CHAIN-V6] {token} {direction} rsi_14 MISSING — fail open (spec §10)")
    elif rsi < floor:
        return False, f"RSI {rsi:.1f} < {floor}"

    momentum = enriched.get('momentum_state')
    if PUMP_CHAIN_V6_BLOCK_FLAT_MOMENTUM:
        if momentum is None:
            _log(f"  [PUMP-CHAIN-V6] {token} {direction} momentum_state MISSING — fail open (spec §10)")
        elif momentum == 'flat':
            return False, "momentum_state='flat'"

    return True, f"rsi={rsi if rsi is not None else 'NA'} mom={momentum or 'NA'}"


def scan_signals() -> int:
    if not PUMP_FLOW_ENABLED or not PUMP_CHAIN_V6_ENABLED:
        return 0

    state = _load_state()
    if not state:
        return 0

    phase = state.get('phase', {})
    recommendations = state.get('recommendations', [])

    if phase.get('confidence', 0) < PUMP_FLOW_MIN_PHASE_CONFIDENCE:
        return 0

    try:
        from signal_schema import get_all_latest_prices
        all_prices = get_all_latest_prices()
    except Exception:
        all_prices = {}

    added = 0

    for rec in recommendations:
        if added >= PUMP_FLOW_MAX_PER_CYCLE:
            break

        token = (rec.get('token') or '').upper()
        if not token:
            continue  # watch-item fix: null token must not abort the scan (bug_hunter)
        direction = rec.get('suggested_direction', '')

        if direction not in ('LONG', 'SHORT'):
            continue

        # Per-direction kill-switch (Layer 1)
        if direction == 'LONG' and not PUMP_CHAIN_V6_PLUS_ENABLED:
            continue
        if direction == 'SHORT' and not PUMP_CHAIN_V6_MINUS_ENABLED:
            continue

        # Blacklists (Layer 1)
        if direction == 'LONG' and token in LONG_BLACKLIST:
            continue
        if direction == 'SHORT' and token in SHORT_BLACKLIST:
            continue

        # G1: freshness
        if price_age_minutes(token) > PUMP_FLOW_MAX_PRICE_AGE:
            continue
        if _check_token_speeds(token):
            _log(f"  [PUMP-CHAIN-V6] SKIP {token} — stale entry (token_speeds)")
            continue

        # G3 + G4: RSI floor + flat momentum (validated gates)
        allowed, why = _gate_rsi_momentum(token, direction)
        if not allowed:
            _log(f"  [PUMP-CHAIN-V6] SKIP {token} {direction} — {why}")
            continue

        # Cooldown
        if get_cooldown(token, direction=direction):
            continue

        # Ranking confidence (not an edge — spec §2.1)
        confidence = _compute_signal_confidence(rec, phase)
        if confidence < PUMP_FLOW_MIN_CONFIDENCE:
            continue

        price_data = all_prices.get(token, {})
        price = price_data.get('price') if isinstance(price_data, dict) else None
        if price is None or price <= 0:
            continue

        source = SOURCE_LONG if direction == 'LONG' else SOURCE_SHORT
        chains = rec.get('chain_evidence', [])

        sid = add_signal(
            token=token,
            direction=direction,
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
            set_cooldown(token, direction, hours=PUMP_FLOW_COOLDOWN_HOURS)
            _log(f"  [PUMP-CHAIN-V6] {token:10s} {direction:5s} conf={confidence:.0f}% "
                 f"{why} phase={phase.get('phase', '?')} chains={_format_chain_evidence(chains)}")

    return added


def run():
    """Entry point for signals_runner. Reads DB/state directly (no prices_dict)."""
    return scan_signals()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Pump chain V6 signal (both directions)')
    parser.add_argument('--dry', action='store_true', help='Dry run')
    args = parser.parse_args()

    if args.dry:
        print("=== Pump Chain V6 Dry Run ===")
        state = _load_state()
        if not state:
            print("No state file found")
            sys.exit(1)
        phase = state.get('phase', {})
        recs = state.get('recommendations', [])
        print(f"Phase: {phase.get('phase', '?')} ({phase.get('confidence', 0):.0%})")
        for rec in recs:
            d = rec.get('suggested_direction', '')
            if d not in ('LONG', 'SHORT'):
                continue
            token = (rec.get('token') or '').upper()
            if not token:
                continue
            allowed, why = _gate_rsi_momentum(token, d)
            print(f"  {token:10s} {d:5s} conf={_compute_signal_confidence(rec, phase):.0f}% "
                  f"{'PASS' if allowed else 'BLOCK'} ({why})")
    else:
        n = run()
        print(f"Pump chain V6 signals added: {n}")
