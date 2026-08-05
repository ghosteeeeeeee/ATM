#!/usr/bin/env python3
"""
audit_diagnose.py — Diagnose trade lifecycle events from audit.log

Usage:
    python3 audit_diagnose.py atom       # all ATOM events
    python3 audit_diagnose.py --failed    # all TRADE_OPEN_FAILED with HL positions left open
    python3 audit_diagnose.py --cooldown  # all LOSS_COOLDOWN_SET events
    python3 audit_diagnose.py --orphans   # all TRADE_ORPHAN_DETECTED events
    python3 audit_diagnose.py --sentinel  # all SENTINEL_ALERT events
    python3 audit_diagnose.py --closes    # all TRADE_CLOSE events, sorted by pnl_usdt
"""

import sys, json, os
from collections import defaultdict

AUDIT_LOG = '/var/www/hermes/data/audit.log'

def load_events():
    if not os.path.exists(AUDIT_LOG):
        print(f"AUDIT_LOG not found at {AUDIT_LOG}")
        sys.exit(1)
    events = []
    with open(AUDIT_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception:
                    pass
    return events

def filter_events(events, **kwargs):
    """Pass token='ATOM', event='TRADE_OPEN_FAILED', etc."""
    result = events
    for key, val in kwargs.items():
        if val is None:
            continue
        result = [e for e in result if e.get(key) == val]
    return result

def print_event(e, verbose=False):
    ts = e.get('ts', '')
    event = e.get('event', '')
    token = e.get('token', '')
    direction = e.get('direction', '')
    trade_id = e.get('trade_id', '')
    
    if event == 'TRADE_CLOSE':
        pnl = e.get('pnl_usdt', 0)
        pnl_pct = e.get('pnl_pct', 0)
        reason = e.get('close_reason', '')
        hype = e.get('hype_realized_pnl_usdt', '')
        is_loss = e.get('is_loss', '')
        print(f"  [{ts}] {event} id={trade_id} {token} {direction} pnl={pnl:+.4f} ({pnl_pct:+.4f}%) hype={hype} loss={is_loss} reason={reason}")
    elif event == 'TRADE_OPEN_SUCCESS':
        hl_ep = e.get('hl_entry_price', '')
        signal = e.get('signal', '')
        print(f"  [{ts}] {event} id={trade_id} {token} {direction} hl_entry={hl_ep} signal={signal}")
    elif event == 'TRADE_OPEN_FAILED':
        reason = e.get('reason', '')
        hl_left = e.get('hl_position_left_open', False)
        flag = " ⚠️ HL LEFT OPEN" if hl_left else ""
        print(f"  [{ts}] {event} {token} {direction} — {reason}{flag}")
    elif event == 'TRADE_ORPHAN_DETECTED':
        entry = e.get('entry_price', '')
        size = e.get('size', '')
        reason = e.get('reason', '')
        print(f"  [{ts}] {event} {token} {direction} entry={entry} size={size} reason={reason}")
    elif event == 'LOSS_COOLDOWN_SET':
        streak = e.get('streak', '')
        hours = e.get('hours', '')
        reason = e.get('reason', '')
        print(f"  [{ts}] {event} {token} {direction} streak={streak} hours={hours:.1f} reason={reason}")
    elif event == 'SENTINEL_ALERT':
        alert_type = e.get('alert_type', '')
        detail = e.get('detail', '')
        print(f"  [{ts}] {event} {token} — {alert_type}: {detail}")
    elif event == 'TRADE_OPEN_ATTEMPT':
        entry = e.get('entry_price', '')
        amount = e.get('amount_usdt', '')
        signal = e.get('signal', '')
        print(f"  [{ts}] {event} {token} {direction} entry={entry} amount={amount} signal={signal}")
    else:
        print(f"  [{ts}] {event} {token} {direction}")

if __name__ == '__main__':
    events = load_events()
    args = sys.argv[1:]

    if not args or '--help' in args:
        print(__doc__)
        sys.exit(0)

    token_filter = [a for a in args if not a.startswith('--')]
    show_failed = '--failed' in args
    show_cooldown = '--cooldown' in args
    show_orphans = '--orphans' in args
    show_sentinel = '--sentinel' in args
    show_closes = '--closes' in args
    show_all = '--all' in args

    if token_filter:
        for tok in token_filter:
            tok_events = [e for e in events if e.get('token', '').upper() == tok.upper()]
            print(f"\n=== {tok} — {len(tok_events)} events ===")
            for e in tok_events:
                print_event(e)
    elif show_failed:
        failed = [e for e in events if e.get('event') == 'TRADE_OPEN_FAILED']
        print(f"\n=== TRADE_OPEN_FAILED — {len(failed)} events ===")
        for e in failed:
            print_event(e)
        orphans = [e for e in events if e.get('event') == 'TRADE_ORPHAN_DETECTED']
        print(f"\n=== TRADE_ORPHAN_DETECTED — {len(orphans)} events ===")
        for e in orphans:
            print_event(e)
    elif show_cooldown:
        cooldown = [e for e in events if e.get('event') == 'LOSS_COOLDOWN_SET']
        print(f"\n=== LOSS_COOLDOWN_SET — {len(cooldown)} events ===")
        for e in cooldown:
            print_event(e)
    elif show_orphans:
        orphans = [e for e in events if e.get('event') == 'TRADE_ORPHAN_DETECTED']
        print(f"\n=== TRADE_ORPHAN_DETECTED — {len(orphans)} events ===")
        for e in orphans:
            print_event(e)
    elif show_sentinel:
        alerts = [e for e in events if e.get('event') == 'SENTINEL_ALERT']
        print(f"\n=== SENTINEL_ALERT — {len(alerts)} events ===")
        for e in alerts:
            print_event(e)
    elif show_closes:
        closes = [e for e in events if e.get('event') == 'TRADE_CLOSE']
        closes.sort(key=lambda e: e.get('pnl_usdt', 0))
        print(f"\n=== TRADE_CLOSE — {len(closes)} events (sorted by pnl_usdt) ===")
        for e in closes:
            print_event(e)
    elif show_all:
        print(f"\n=== ALL EVENTS — {len(events)} total ===")
        for e in events:
            print_event(e)
    else:
        print(__doc__)