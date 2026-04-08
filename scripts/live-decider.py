#!/usr/bin/env python3
"""
Live Trading Decider - Wrapper for decider_run.py
Executes trades on real Hyperliquid using the unified execution pipeline.
"""
import sys
import subprocess
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run_live():
    """Run live trading via decider_run.py with --live flag"""
    result = subprocess.run(
        ['python3', f'{SCRIPT_DIR}/decider_run.py', '--live'],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode

def main():
    """Main entry point - runs decider in live mode"""
    sys.exit(run_live())

if __name__ == '__main__':
    main()
