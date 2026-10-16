#!/usr/bin/env python3
"""
vacation_mode.py — Vacation mode switch.

Flip on: all automation runs in conservative mode (shadow-first, no enforcement,
guardrails active). Flip off: return to normal.

Usage:
    python3 scripts/vacation_mode.py status    # Check current state
    python3 scripts/vacation_mode.py on        # Enable vacation mode
    python3 scripts/vacation_mode.py off       # Disable vacation mode
"""
import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import HERMES_DATA

SWITCH_PATH = os.path.join(HERMES_DATA, 'vacation_mode.json')


def get_status():
    """Read vacation mode state."""
    if not os.path.exists(SWITCH_PATH):
        return {'vacation_mode': False, 'reason': 'not_set'}
    with open(SWITCH_PATH) as f:
        return json.load(f)


def enable(reason='T on vacation'):
    """Enable vacation mode."""
    config = {
        'vacation_mode': True,
        'reason': reason,
        'enabled_at': datetime.now(timezone.utc).isoformat(),
        'daily_growth_target': 0.01,  # 1% per day
        'rules': {
            'shadow_first': True,        # All new gates ship shadow-only
            'no_enforcement_flips': True, # No shadow→enforce transitions
            'no_constants_change': True,  # hermes_constants.py frozen
            'no_signal_enable_disable': True,
            'guardrails_active': True,   # PnL/WR auto-pause armed
            'moE_weekly': True,          # Weekly MoE panel
            'ceo_every_30min': True,     # CEO checks every 30 min
        }
    }
    with open(SWITCH_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Vacation mode ENABLED: {reason}")
    print(f"   Daily growth target: 1%")
    print(f"   Shadow-first: ON | No enforcement flips: ON")
    print(f"   Constants frozen: ON | Guardrails: ON")
    return config


def disable(reason='T returned'):
    """Disable vacation mode."""
    config = get_status()
    config['vacation_mode'] = False
    config['disabled_at'] = datetime.now(timezone.utc).isoformat()
    config['disable_reason'] = reason
    with open(SWITCH_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"❌ Vacation mode DISABLED: {reason}")
    return config


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Vacation mode switch')
    parser.add_argument('action', choices=['status', 'on', 'off'])
    parser.add_argument('--reason', default=None)
    args = parser.parse_args()

    if args.action == 'status':
        status = get_status()
        print(json.dumps(status, indent=2))
    elif args.action == 'on':
        enable(args.reason or 'T on vacation')
    elif args.action == 'off':
        disable(args.reason or 'T returned')
