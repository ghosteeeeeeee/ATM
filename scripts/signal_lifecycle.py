#!/usr/bin/env python3
"""
Signal Lifecycle Manager: orchestrates auditor + rotator, tracks signal state.

Runs daily. Coordinates the signal lifecycle:
  1. Runs signal_auditor.py (read-only audit)
  2. Runs signal_rotator.py (enable/disable based on regime)
  3. Updates signal state metadata (experimental/active/maturing/deprecated)
  4. Writes daily summary

Data sources: signal_audit.json, signal_rotation.json, signal_outcomes
Output: data/signal_lifecycle.json, automation/signal_lifecycle.md
Timer: every 24 hours (hermes-signal-lifecycle.timer)

Usage:
  python3 signal_lifecycle.py           # Full run: audit → rotate → update states
  python3 signal_lifecycle.py --dry     # Dry run: show what would change
"""

import sys, os, re, json, subprocess, sqlite3
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA, RUNTIME_DB

DRY_RUN = '--dry' in sys.argv
LIFECYCLE_JSON = os.path.join(HERMES_DATA, 'signal_lifecycle.json')
LIFECYCLE_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'automation', 'signal_lifecycle.md')
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# State transition thresholds
STATE_THRESHOLDS = {
    'experimental': {
        'promote_to_active': {'min_wr': 50, 'min_days': 3, 'min_trades': 20},
        'demote_to_deprecated': {'max_wr': 20, 'min_trades': 10},
    },
    'active': {
        'demote_to_maturing': {'max_wr': 40, 'min_days': 2},
    },
    'maturing': {
        'demote_to_deprecated': {'max_wr': 25, 'min_days': 3},
    },
}


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    line = f"[{ts}] {msg}"
    print(line)


def run_script(name, extra_args=None):
    """Run a lifecycle sub-script and capture output."""
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, name)]
    if extra_args:
        cmd.extend(extra_args)
    # Only pass --dry to scripts that support it
    SUPPORTED_DRY = {'signal_rotator.py'}
    if DRY_RUN and name in SUPPORTED_DRY:
        cmd.append('--dry')
    log(f"Running {name}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=SCRIPTS_DIR)
        for line in result.stdout.strip().split('\n')[-5:]:  # last 5 lines
            if line.strip():
                log(f"  {line.strip()}")
        if result.returncode != 0:
            log(f"  WARNING: {name} exited with code {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"  ERROR: {name} timed out")
        return False
    except Exception as e:
        log(f"  ERROR: {name} failed: {e}")
        return False


def load_lifecycle():
    """Load existing lifecycle state."""
    if os.path.exists(LIFECYCLE_JSON):
        try:
            with open(LIFECYCLE_JSON) as f:
                return json.load(f)
        except Exception:
            pass
    return {'signals': {}, 'last_run': None}


def save_lifecycle(data):
    """Save lifecycle state atomically."""
    os.makedirs(os.path.dirname(LIFECYCLE_JSON), exist_ok=True)
    tmp = LIFECYCLE_JSON + '.tmp'
    try:
        with open(tmp, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, LIFECYCLE_JSON)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_audit():
    """Load latest audit data."""
    audit_path = os.path.join(HERMES_DATA, 'signal_audit.json')
    try:
        with open(audit_path) as f:
            return json.load(f).get('signals', [])
    except Exception:
        return []


def get_signal_history(signal_type, days=7):
    """Get historical performance for a signal type."""
    conn = sqlite3.connect(RUNTIME_DB)
    try:
        c = conn.cursor()
        c.execute("""
            SELECT DATE(created_at) as day,
                   COUNT(*) as trades,
                   SUM(CASE WHEN is_win = 1 THEN 1 ELSE 0 END) as wins,
                   AVG(pnl_pct) as avg_pnl
            FROM signal_outcomes
            WHERE signal_type = ?
              AND created_at > datetime('now', '-' || ? || ' days')
              AND trade_id IS NOT NULL
            GROUP BY day
            ORDER BY day
        """, (signal_type, days))
        return c.fetchall()
    finally:
        conn.close()


def check_state_transition(signal_type, current_state, history, lifecycle_data):
    """Check if a signal should transition to a new state."""
    if not history:
        return current_state, None

    # Compute recent WR (last 3 days)
    recent_days = [h for h in history if h[0] >= (datetime.now(timezone.utc) - timedelta(days=3)).strftime('%Y-%m-%d')]
    recent_trades = sum(h[1] for h in recent_days)
    recent_wins = sum(h[2] for h in recent_days)
    recent_wr = (recent_wins / recent_trades * 100) if recent_trades > 0 else 0

    # Total stats
    total_trades = sum(h[1] for h in history)
    total_wins = sum(h[2] for h in history)
    total_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

    # Track consecutive days below threshold
    sig_data = lifecycle_data.get('signals', {}).get(signal_type, {})
    days_below = sig_data.get('days_below_threshold', 0)

    if recent_wr < 25:
        days_below += 1
    else:
        days_below = 0

    # State transitions
    new_state = current_state
    reason = None

    if current_state == 'experimental':
        if total_wr >= 50 and total_trades >= 20:
            new_state = 'active'
            reason = f'Promoted: WR={total_wr:.0f}% ({total_trades} trades)'
        elif total_wr < 20 and total_trades >= 10:
            new_state = 'deprecated'
            reason = f'Deprecated: WR={total_wr:.0f}% ({total_trades} trades)'

    elif current_state == 'active':
        if days_below >= 2:
            new_state = 'maturing'
            reason = f'Maturing: WR={recent_wr:.0f}% below 40% for {days_below} days'

    elif current_state == 'maturing':
        if days_below >= 3:
            new_state = 'deprecated'
            reason = f'Deprecated: WR={recent_wr:.0f}% below 25% for {days_below} days'

    # Update days_below in lifecycle data
    if signal_type in lifecycle_data.get('signals', {}):
        lifecycle_data['signals'][signal_type]['days_below_threshold'] = days_below

    return new_state, reason


def update_states(lifecycle_data, audit_signals):
    """Update all signal states based on latest data."""
    transitions = []

    # Get all known signals (from audit + lifecycle)
    known_signals = set()
    for sig in audit_signals:
        known_signals.add(sig['signal_type'])
    for sig_type in lifecycle_data.get('signals', {}):
        known_signals.add(sig_type)

    # Build audit lookup
    audit_lookup = {s['signal_type']: s for s in audit_signals}

    for signal_type in sorted(known_signals):
        sig_data = lifecycle_data.get('signals', {}).get(signal_type, {})
        current_state = sig_data.get('state', 'experimental')
        audit = audit_lookup.get(signal_type, {})

        # Get history
        history = get_signal_history(signal_type, days=7)

        # Check transition
        new_state, reason = check_state_transition(signal_type, current_state, history, lifecycle_data)

        # Update state
        if signal_type not in lifecycle_data.get('signals', {}):
            lifecycle_data.setdefault('signals', {})[signal_type] = {
                'state': new_state,
                'enabled_since': datetime.now(timezone.utc).isoformat(),
                'decay_count': 0,
                're_enable_count': 0,
                'days_below_threshold': 0,
            }

        if new_state != current_state:
            lifecycle_data['signals'][signal_type]['state'] = new_state
            transitions.append({
                'signal_type': signal_type,
                'from': current_state,
                'to': new_state,
                'reason': reason,
            })
            log(f"  {signal_type}: {current_state} → {new_state} ({reason})")

        # Update metrics
        lifecycle_data['signals'][signal_type].update({
            'last_wr': audit.get('wr', 0),
            'last_edge': audit.get('edge_score', 0),
            'last_updated': datetime.now(timezone.utc).isoformat(),
        })

    return transitions


def write_lifecycle_report(lifecycle_data, transitions, audit_success, rotation_success):
    """Write daily lifecycle report."""
    os.makedirs(os.path.dirname(LIFECYCLE_MD), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # Count states
    states = {}
    for sig_type, sig_data in lifecycle_data.get('signals', {}).items():
        state = sig_data.get('state', 'experimental')
        states[state] = states.get(state, 0) + 1

    tmp = LIFECYCLE_MD + '.tmp'
    with open(tmp, 'w') as f:
        f.write(f"# Signal Lifecycle — {ts}\n\n")
        f.write(f"## Pipeline\n")
        f.write(f"- Audit: {'✅' if audit_success else '❌'}\n")
        f.write(f"- Rotation: {'✅' if rotation_success else '❌'}\n\n")

        f.write(f"## Signal States\n")
        for state in ['active', 'experimental', 'maturing', 'deprecated']:
            count = states.get(state, 0)
            if count > 0:
                emoji = {'active': '🟢', 'experimental': '🔵', 'maturing': '🟡', 'deprecated': '🔴'}[state]
                f.write(f"- {emoji} {state}: {count}\n")

        f.write(f"\n## State Transitions\n")
        if transitions:
            for t in transitions:
                f.write(f"- **{t['signal_type']}**: {t['from']} → {t['to']} ({t['reason']})\n")
        else:
            f.write(f"- No transitions\n")

        f.write(f"\n## All Signals\n\n")
        f.write(f"| Signal | State | WR | Edge | Updated |\n")
        f.write(f"|--------|-------|-----|------|--------|\n")
        for sig_type, sig_data in sorted(lifecycle_data.get('signals', {}).items()):
            state = sig_data.get('state', 'experimental')
            emoji = {'active': '🟢', 'experimental': '🔵', 'maturing': '🟡', 'deprecated': '🔴'}.get(state, '⚪')
            wr = sig_data.get('last_wr', 0)
            edge = sig_data.get('last_edge', 0)
            updated = sig_data.get('last_updated', 'never')[:10]
            f.write(f"| {sig_type[:25]} | {emoji} {state} | {wr:.0f}% | {edge:.3f} | {updated} |\n")

    os.replace(tmp, LIFECYCLE_MD)


def main():
    log(f"{'[DRY RUN] ' if DRY_RUN else ''}=== Signal Lifecycle Manager ===")

    # Load existing state
    lifecycle_data = load_lifecycle()
    log(f"Loaded {len(lifecycle_data.get('signals', {}))} tracked signals")

    # Step 1: Run auditor
    audit_success = run_script('signal_auditor.py')

    # Step 2: Run rotator
    rotation_success = run_script('signal_rotator.py')

    # Step 3: Update signal states
    audit_signals = load_audit()
    transitions = update_states(lifecycle_data, audit_signals)

    # Save state
    lifecycle_data['last_run'] = datetime.now(timezone.utc).isoformat()
    if not DRY_RUN:
        save_lifecycle(lifecycle_data)

    # Step 4: Write report
    write_lifecycle_report(lifecycle_data, transitions, audit_success, rotation_success)

    log(f"Lifecycle complete. {len(transitions)} transitions, {len(lifecycle_data.get('signals', {}))} signals tracked.")


if __name__ == '__main__':
    main()
