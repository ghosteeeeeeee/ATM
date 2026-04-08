#!/usr/bin/env python3
"""Signal flip enable/disable script for Hermes trading pipeline.

Usage:
    python3 signal_flip.py status   # check current state
    python3 signal_flip.py on      # enable flip
    python3 signal_flip.py off     # disable flip
"""
import sys, re, argparse

FILE = '/root/.hermes/scripts/decider_run.py'

def get_status():
    with open(FILE) as f:
        content = f.read()
    m = re.search(r'_FLIP_SIGNALS\s*=\s*(True|False)', content)
    if m:
        return m.group(1) == 'True'
    return None

def set_flip(enabled: bool):
    value = 'True' if enabled else 'False'
    with open(FILE) as f:
        content = f.read()
    if f'_FLIP_SIGNALS = {value}' in content:
        print(f'Flip already {"ENABLED" if enabled else "DISABLED"} (no change needed)')
        return
    new_content = re.sub(r'_FLIP_SIGNALS\s*=\s*(True|False)', f'_FLIP_SIGNALS = {value}', content)
    with open(FILE, 'w') as f:
        f.write(new_content)
    print(f'Flip {"ENABLED" if enabled else "DISABLED"} — takes effect on next pipeline run (~1 min)')

def main():
    parser = argparse.ArgumentParser(description='Signal flip for Hermes')
    parser.add_argument('action', choices=['on', 'off', 'status'], help='on=enable, off=disable, status=check')
    args = parser.parse_args()
    if args.action == 'status':
        status = get_status()
        if status is None:
            print('ERROR: _FLIP_SIGNALS not found in decider-run.py')
            sys.exit(1)
        print(f'Signal flip is: {"ENABLED" if status else "DISABLED"}')
    elif args.action == 'on':
        set_flip(True)
    elif args.action == 'off':
        set_flip(False)

if __name__ == '__main__':
    main()
