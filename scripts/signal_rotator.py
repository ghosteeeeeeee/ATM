#!/usr/bin/env python3
"""
Signal Rotator: selects the optimal signal subset for current market conditions.

Data sources: signal_audit.json (from auditor) + regime_5m.json (from regime scanner)
Output: modifies hermes_constants.py (enable/disable signals)
Timer: every 4 hours (hermes-signal-rotator.timer)

Usage:
  python3 signal_rotator.py           # Full run: read → select → enable/disable
  python3 signal_rotator.py --dry     # Dry run: show what would change
"""

import sys, os, re, fcntl, shutil, json, sqlite3
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB

DRY_RUN = '--dry' in sys.argv
LOCK_FILE = '/tmp/hermes-constants.lock'  # shared with decay_detector to prevent race conditions
AUDIT_JSON = os.path.join(HERMES_DATA, 'signal_audit.json')
REGIME_FILE = '/var/www/hermes/data/regime_5m.json'
CONSTANTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hermes_constants.py')
ROTATION_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'signal_rotation.md')
ROTATION_JSON = os.path.join(HERMES_DATA, 'signal_rotation.json')

# Safety
# NOTE: Kill/disable logic is coordinated with self_learner.py (daily) and
# signal_decay_detector.py (rapid-response). This rotator handles REGIME-BASED
# selection (enable/disable for current market conditions), not kill decisions.
# Keep MIN_WR_TO_DISABLE conservative — self_learner handles the nuanced kills.
MAX_CHANGES_PER_CYCLE = 2
MIN_WR_TO_DISABLE = 45    # only disable if WR < 45% AND negative edge (self_learner handles kills)
MIN_WR_TO_ENABLE = 35     # never enable signals with WR < 35% (wider dead zone)
MIN_TRADES = 5            # need at least 5 trades for decisions

# Signal category mapping — which signals work best in which regime
# Computed dynamically from signal_outcomes when possible; these are fallback affinities
REGIME_SIGNAL_AFFINITY = {
    'LONG_BIAS': {
        'boost': ['accel_300', 'momentum', 'fast_momentum', 'mtf_momentum', 'gap_300',
                  'phase_accel', 'tl_break', 'squeeze_cross', 'bollinger_squeeze',
                  'pct_hermes', 'vel_hermes', 'hzscore'],
        'penalize': ['inv_accel_300', 'exhaustion', 'counter_flip'],
    },
    'SHORT_BIAS': {
        'boost': ['inv_accel_300', 'exhaustion', 'counter_flip', 'tl_break',
                  'pct_hermes', 'vel_hermes', 'hzscore'],
        'penalize': ['accel_300', 'momentum', 'fast_momentum', 'gap_300', 'phase_accel'],
    },
    'NEUTRAL': {
        'boost': ['zscore_rising', 'zscore_pump', 'mtp_zscore', 'atr_compression',
                  'volume_hl', 'pattern_scanner', 'hmacd'],
        'penalize': [],
    },
}


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)


def get_current_regime():
    """Read current market regime from regime scanner output."""
    try:
        with open(REGIME_FILE) as f:
            data = json.load(f)
        return data.get('aggregate', {}).get('overall', 'NEUTRAL')
    except Exception as e:
        log(f"Warning: Could not read regime data: {e}")
        return 'NEUTRAL'


def load_audit():
    """Load signal audit results from JSON."""
    try:
        with open(AUDIT_JSON) as f:
            data = json.load(f)
        return data.get('signals', [])
    except Exception as e:
        log(f"Error loading audit: {e}")
        return []


def get_registry_status():
    """Get enabled/disabled status from hermes_constants.py."""
    status = {}
    try:
        with open(CONSTANTS_FILE) as f:
            content = f.read()
        for match in re.finditer(r'^(\w+_ENABLED)\s*=\s*(True|False)', content, re.MULTILINE):
            status[match.group(1)] = match.group(2) == 'True'
    except Exception as e:
        log(f"Error reading constants: {e}")
    return status


def map_signal_to_flag(signal_type):
    """Map signal_type to its ENABLED flag (same logic as signal_auditor)."""
    base = signal_type.split(',')[0].strip()
    suffix = ''
    if base.endswith('+'):
        suffix = '_PLUS'
        base = base[:-1]
    elif base.endswith('-'):
        suffix = '_MINUS'
        base = base[:-1]

    base_underscore = base.replace('-', '_')

    master_overrides = {
        'bb_squeeze': 'BOLLINGER_SQUEEZE',
        'pattern_scanner': 'PATTERN_FLAG',
        'volume_hl': 'VOLUME_HL',
        'atr_compression': 'ATR_COMPRESSION',
    }

    exact_overrides = {
        'accel_300_vel': 'ACCEL_300_VELOCITY',
        'inv_accel_300': 'INVERSE_ACCEL_300',
        'tl_break_long': 'TL_BREAK_PLUS',
        'tl_break_short': 'TL_BREAK_MINUS',
        'ema9_sma20': 'EMA9_SMA20',
        'ma_cross_5m': 'MA_CROSS_5M',
        'gap_300': 'GAP_300',
        'mtp_zscore': 'MTP_ZSCORE',
    }

    if base_underscore in master_overrides:
        # When suffix present, use directional flag; otherwise use master
        flag_base = master_overrides[base_underscore]
        return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'

    if base_underscore in exact_overrides:
        flag_base = exact_overrides[base_underscore]
        return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'

    flag_base = base_underscore.upper()
    return f'{flag_base}{suffix}_ENABLED' if suffix else f'{flag_base}_ENABLED'


def select_signals(audit_signals, regime, registry):
    """Select which signals to enable/disable based on regime and performance."""
    affinity = REGIME_SIGNAL_AFFINITY.get(regime, REGIME_SIGNAL_AFFINITY['NEUTRAL'])
    boost_set = set(affinity['boost'])
    penalize_set = set(affinity['penalize'])

    scored = []
    for sig in audit_signals:
        flag = map_signal_to_flag(sig['signal_type'])
        is_enabled = registry.get(flag, None) if flag else None
        wr = sig.get('wr', 0)
        edge = sig.get('edge_score', 0)
        trades = sig.get('trades', 0)

        # Base score from edge
        score = edge

        # Regime adjustment: boost signals that work in current regime
        base_underscore = sig['signal_type'].split(',')[0].strip().rstrip('+-').replace('-', '_')
        if base_underscore in boost_set:
            score *= 1.5  # 50% boost for regime-aligned signals
        elif base_underscore in penalize_set:
            score *= 0.5  # 50% penalty for counter-regime signals

        scored.append({
            **sig,
            'flag': flag,
            'is_enabled': is_enabled,
            'regime_score': score,
        })

    # Sort by regime-adjusted score
    scored.sort(key=lambda x: x['regime_score'], reverse=True)

    # Decide: enable top performers, disable bottom performers
    changes = []

    # Load permanent-disable guard — never re-enable these flags
    try:
        from hermes_constants import NEVER_REENABLE_FLAGS
    except ImportError:
        NEVER_REENABLE_FLAGS = set()

    # Load rotator-protected flags — never auto-disable these (recently upgraded)
    try:
        from hermes_constants import ROTATOR_PROTECTED_FLAGS
    except ImportError:
        ROTATOR_PROTECTED_FLAGS = []

    for sig in scored:
        flag = sig['flag']
        wr = sig['wr']
        trades = sig['trades']
        is_enabled = sig['is_enabled']

        if not flag or is_enabled is None:
            continue
        if trades < MIN_TRADES:
            continue

        # Enable candidate: currently disabled but performing well + regime-aligned
        if is_enabled is False and wr >= MIN_WR_TO_ENABLE and sig['regime_score'] > 0.1:
            if flag in NEVER_REENABLE_FLAGS:
                log(f"  SKIP enable {flag}: in NEVER_REENABLE_FLAGS (manual disable)")
                continue
            changes.append({
                'flag': flag,
                'action': 'enable',
                'signal_type': sig['signal_type'],
                'reason': f'WR={wr:.0f}%, edge={sig["edge_score"]:.3f}, regime-aligned',
                'wr': wr,
            })

        # Disable candidate: currently enabled but underperforming
        elif is_enabled is True and wr < MIN_WR_TO_DISABLE and sig.get('edge_score', 0) < 0 and trades >= MIN_TRADES:
            # Check rotator-protected flags (recently upgraded signals)
            if flag in ROTATOR_PROTECTED_FLAGS:
                log(f"  SKIP disable {flag}: in ROTATOR_PROTECTED_FLAGS (recently upgraded)")
                continue
            changes.append({
                'flag': flag,
                'action': 'disable',
                'signal_type': sig['signal_type'],
                'reason': f'WR={wr:.0f}%, edge={sig["edge_score"]:.3f}, bleeding capital',
                'wr': wr,
            })

    return scored, changes[:MAX_CHANGES_PER_CYCLE]


def apply_changes(changes):
    """Apply enable/disable changes to hermes_constants.py."""
    if not changes:
        return []

    shutil.copy2(CONSTANTS_FILE, CONSTANTS_FILE + '.bak')

    with open(CONSTANTS_FILE) as f:
        content = f.read()

    # Strip existing auto-rotation comments
    content = re.sub(r'\s*#\s*AUTO-ROTATED\s*\d{4}-\d{2}-\d{2}\s*', ' ', content)

    applied = []
    for ch in changes:
        new_val = 'True' if ch['action'] == 'enable' else 'False'
        pattern = rf'({re.escape(ch["flag"])}\s*=\s*)(True|False)'
        replacement = f'\\g<1>{new_val}  # AUTO-ROTATED {datetime.now(timezone.utc).strftime("%Y-%m-%d")}'
        new_content = re.sub(pattern, replacement, content, count=1)

        if new_content != content:
            content = new_content
            applied.append(ch)
            log(f"{'[DRY] ' if DRY_RUN else ''}{ch['action'].upper()}: {ch['flag']} → {new_val} ({ch['signal_type']})")

    if applied and not DRY_RUN:
        try:
            compile(content, CONSTANTS_FILE, 'exec')
        except SyntaxError as e:
            log(f"FATAL: Corrupted constants, restoring backup: {e}")
            shutil.copy2(CONSTANTS_FILE + '.bak', CONSTANTS_FILE)
            return []
        tmp = CONSTANTS_FILE + '.tmp'
        with open(tmp, 'w') as f:
            f.write(content)
        os.replace(tmp, CONSTANTS_FILE)

    return applied


def write_rotation_report(scored_signals, regime, applied):
    """Write rotation report."""
    os.makedirs(os.path.dirname(ROTATION_LOG), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    tmp = ROTATION_LOG + '.tmp'
    with open(tmp, 'w') as f:
        f.write(f"# Signal Rotation — {ts}\n\n")
        f.write(f"## Market Regime: {regime}\n\n")
        f.write(f"## Signals Ranked by Regime-Adjusted Score\n\n")
        f.write(f"| # | Signal | WR | Edge | Regime Score | Enabled | Action |\n")
        f.write(f"|---|--------|-----|------|-------------|---------|--------|\n")
        for i, sig in enumerate(scored_signals[:15], 1):
            enabled_str = '✅' if sig['is_enabled'] is True else ('❌' if sig['is_enabled'] is False else '❓')
            action = ''
            for ch in applied:
                if ch['signal_type'] == sig['signal_type']:
                    action = ch['action'].upper()
                    break
            f.write(f"| {i} | {sig['signal_type'][:25]} | {sig['wr']:.0f}% | {sig['edge_score']:.3f} | {sig['regime_score']:.3f} | {enabled_str} | {action} |\n")

        if applied:
            f.write(f"\n## Changes Applied\n")
            for ch in applied:
                f.write(f"- **{ch['action'].upper()}**: {ch['flag']} ({ch['reason']})\n")
        else:
            f.write(f"\n## No changes applied\n")
    os.replace(tmp, ROTATION_LOG)


def main():
    log(f"{'[DRY RUN] ' if DRY_RUN else ''}=== Signal Rotator ===")

    # Lock
    lock_fd = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_fd.close()
        log("Another instance running, exiting")
        return

    try:
        # Get current regime
        regime = get_current_regime()
        log(f"Current regime: {regime}")

        # Load audit data
        audit_signals = load_audit()
        if not audit_signals:
            log("No audit data — run signal_auditor.py first")
            return
        log(f"Loaded {len(audit_signals)} signals from audit")

        # Get registry status
        registry = get_registry_status()

        # Select signals
        scored, changes = select_signals(audit_signals, regime, registry)
        log(f"{len(changes)} changes recommended:")
        for ch in changes:
            log(f"  {ch['action'].upper()}: {ch['signal_type']} ({ch['reason']})")

        # Apply changes
        applied = apply_changes(changes)

        # Write outputs
        write_rotation_report(scored, regime, applied)

        os.makedirs(os.path.dirname(ROTATION_JSON), exist_ok=True)
        tmp = ROTATION_JSON + '.tmp'
        with open(tmp, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'regime': regime,
                'changes': [{'flag': c['flag'], 'action': c['action'], 'signal_type': c['signal_type']} for c in applied],
            }, f, indent=2)
        os.replace(tmp, ROTATION_JSON)

        log(f"Rotation complete. {len(applied)} changes applied.")

    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == '__main__':
    main()
