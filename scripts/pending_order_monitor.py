#!/usr/bin/env python3
"""pending_order_monitor — pipeline step (CEO directive 2026-11-08).

Fills CEO-armed conditional orders on the NEXT 1-MINUTE pipeline cycle
instead of waiting for the 30-minute watchdog cadence. One code base:
imports trade_watchdog's monitor + execute path; the one-shot state file
makes the second caller double-fire-proof (watchdog and pipeline can both
run it in the same window without double-trading).

Mode gate mirrors execute_safe_actions: executes ONLY in autopilot mode;
in recommend mode it reports and leaves the order armed for the watchdog.
Data source: local prices.json only (data-source rule).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA
import trade_watchdog as tw

PRICE_FILE = os.path.join(HERMES_DATA, 'prices.json')


def main():
    try:
        with open(PRICE_FILE) as f:
            price = float(json.load(f)['prices'].get('BTC') or 0)
    except Exception as e:
        print(f'pending_order_monitor: no local price ({e}) — skipped')
        return 0
    if price <= 0:
        print('pending_order_monitor: price missing — skipped')
        return 0

    mode = tw.get_watchdog_mode()[0]
    if mode != 'autopilot':
        # Same rule as the watchdog: recommend mode never touches one-shot
        # state (execution can't follow — PENDING_ORDERS_CAN_PERSIST logic).
        print(f'pending_order_monitor: mode={mode} — no execution this cycle')
        return 0

    steers = tw.monitor_pending_orders(price)
    hits = [s for s in steers if s.get('category') == 'pending_order']
    if not hits:
        return 0                       # quiet cycle — no output spam

    rc = 0
    for s in hits:
        act = s.get('action') or {}
        if not (isinstance(act, dict) and act.get('order')):
            continue
        res = tw._execute_pending_order(act['order'])
        if isinstance(res, dict) and res.get('hl_result') == 'success':
            print(f"pending_order_monitor: FILLED {res.get('trade')} — {s.get('title')}")
        else:
            print(f"pending_order_monitor: FAILED — {s.get('title')} ({res})")
            rc = 1
    return rc


if __name__ == '__main__':
    sys.exit(main())
