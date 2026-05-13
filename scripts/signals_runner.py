#!/usr/bin/env python3
"""
signals_runner.py — Run registered signals and log their outputs.

Two execution modes:
  - FAST (default): run fast signals every minute (accel_300, hzscore, etc.)
  - SLOW: run slow signals (momentum, mtf_momentum) every 5 minutes

Called every minute via run_pipeline.py STEPS_EVERY_MIN.
Pass --slow to run the slow signals instead.
"""
import sys
import os
import time
import argparse

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'pipeline.log')


def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except Exception:
        pass


def main():
    # Parse --slow flag for slow signal runs
    parser = argparse.ArgumentParser()
    parser.add_argument('--slow', action='store_true', help='Run slow signals instead of fast')
    args = parser.parse_args()

    try:
        from signals import (
            run_all_signals,
            get_registered_signals,
            get_fast_signals,
            get_slow_signals,
        )

        mode = 'SLOW' if args.slow else 'FAST'
        signals = get_slow_signals() if args.slow else get_fast_signals()
        signal_names = [s['name'] for s in signals]

        log(f'signals_runner [{mode}]: {len(signals)} signals — {signal_names}')

        if not signals:
            log(f'signals_runner [{mode}]: no signals to run')
            return

        results = run_all_signals(signal_list=signals)

        if not results:
            log(f'signals_runner [{mode}]: no results')
            return

        total = len(results)
        errors = sum(1 for v in results.values() if isinstance(v, str) and v.startswith('ERROR:'))
        log(f'signals_runner [{mode}]: {total} done, {errors} errors')

        for sig_name, sig_result in results.items():
            if isinstance(sig_result, str) and sig_result.startswith('ERROR:'):
                log(f'  Signal {sig_name}: ERROR → {sig_result}')
            elif sig_result is not None:
                log(f'  Signal {sig_name}: {str(sig_result)[:80]}')

    except ImportError as e:
        log(f'signals_runner: ImportError — signals module not available: {e}')
    except Exception as e:
        log(f'signals_runner: ERROR — {e}')
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
