#!/usr/bin/env python3
"""
checkpoint_watch.py — Surface DUE/OVERDUE time-boxed checkpoints (zero-LLM).

CEO 2026-10-27 item 2 companion (d). Intraday time-boxed checkpoints (e.g. the
"17:12Z pc- formal NO-GO") were free-text in the brain-auditor's queue line. With
the auditor dropped hourly -> 4h, such a checkpoint could sit unread for up to 4h
and its window would silently close (the 17:12Z case was caught ~36min late even
at hourly cadence).

This watcher gives intraday resolution WITHOUT an LLM session:
  * reads a registry of pending checkpoints (data/checkpoint_registry.json)
  * when one is due (within its window) or overdue, appends a prominent
    DUE/OVERDUE line to automation/ceo/ceo_kanban.md + error_alerts.md
  * dedupes so a checkpoint is surfaced once per state transition, not every run

Registry entry shape:
  {"id": "pc-formal-1712", "desc": "pc- formal NO-GO (contrarian join reproduce)",
   "due_at": "2026-10-27T17:12:00+00:00", "status": "pending",
   "grace_min": 60, "created_by": "brain_auditor #186"}

  status: pending -> surfaced -> done/acknowledged
  grace_min: how long past due_at before it counts as OVERDUE (default 60)

Who writes the registry: the brain-auditor (or T/CEO) appends a pending entry
when it registers an intraday checkpoint. This script only READS it and surfaces.

Modes:
  (default) scan + surface + mark
  --report  print registry state, change nothing

Usage: python3 scripts/checkpoint_watch.py [--report]
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA

REGISTRY = os.path.join(HERMES_DATA, 'checkpoint_registry.json')
CEO_KANBAN = '/root/.hermes/automation/ceo/ceo_kanban.md'
ERROR_ALERTS = '/root/.hermes/automation/error_alerts.md'
DEFAULT_GRACE_MIN = 60


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [checkpoint_watch] {msg}', flush=True)


def load_registry():
    if not os.path.exists(REGISTRY):
        return []
    try:
        with open(REGISTRY) as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception as e:
        log(f'registry unreadable: {e}')
        return []


def save_registry(entries):
    tmp = REGISTRY + '.tmp'
    os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)
    with open(tmp, 'w') as f:
        json.dump(entries, f, indent=2)
    os.replace(tmp, REGISTRY)


def parse_due(s):
    """Parse due_at; naive strings treated as UTC."""
    try:
        dt = datetime.fromisoformat(str(s))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _append(path, text):
    try:
        with open(path, 'a') as f:
            f.write(text)
        return True
    except Exception as e:
        log(f'append to {path} failed: {e}')
        return False


def scan(report_only=False):
    entries = load_registry()
    if not entries:
        log('registry empty or absent — nothing to do')
        return 0

    now = datetime.now(timezone.utc)
    surfaced = 0
    due_lines = []

    for e in entries:
        if not isinstance(e, dict):
            continue
        if e.get('status') not in ('pending', 'surfaced'):
            continue
        # Per-entry fault isolation: one malformed entry (bad grace_min, bad
        # status type) must NOT crash the scan for every OTHER checkpoint
        # (review #6). A registry entry can be written by an LLM agent.
        try:
            grace_raw = e.get('grace_min', DEFAULT_GRACE_MIN)
            grace = timedelta(minutes=int(grace_raw))
        except (TypeError, ValueError):
            grace = timedelta(minutes=DEFAULT_GRACE_MIN)
        due = parse_due(e.get('due_at'))
        if due is None:
            continue
        eid = e.get('id', '?')
        desc = e.get('desc', '')

        if now < due:
            continue  # not yet due

        overdue = now > (due + grace)
        state = 'OVERDUE' if overdue else 'DUE'
        # Dedupe on STATE TRANSITION, not just "was surfaced". Without this an
        # OVERDUE entry re-logged every 30min run — the exact alert spam the
        # anomaly-only design exists to avoid. Re-surface only if the state
        # changed since last time (pending->DUE, or DUE->OVERDUE escalation).
        if e.get('status') == 'surfaced' and e.get('last_state') == state:
            continue

        e['status'] = 'surfaced'
        e['last_state'] = state
        e['surfaced_at'] = now.isoformat()
        surfaced += 1
        due_lines.append((state, eid, desc, e.get('due_at')))

    if report_only:
        for state, eid, desc, due_at in due_lines:
            print(f'{state}: {eid} (due {due_at}) — {desc}')
        return len(due_lines)

    if not due_lines:
        log(f'scanned {len(entries)} entries — none due')
        save_registry(entries)
        return 0

    ts = now.strftime('%Y-%m-%d %H:%M UTC')
    kb = [f'\n## ⏰ Checkpoint Watch — {ts}\n']
    al = [f'\n## Error Alerts — {ts}\n']
    for state, eid, desc, due_at in due_lines:
        kb.append(f'- **[{state}]** `{eid}` (due {due_at}): {desc}\n')
        al.append(f'- **[WARN]** (checkpoint_watch): **{state}** `{eid}` (due {due_at}): {desc}\n')
        log(f'{state}: {eid} — {desc}')

    _append(CEO_KANBAN, ''.join(kb))
    _append(ERROR_ALERTS, ''.join(al))
    save_registry(entries)
    log(f'surfaced {len(due_lines)} checkpoint(s) to kanban + error_alerts')
    return len(due_lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true', help='print state, change nothing')
    args = ap.parse_args()
    scan(report_only=args.report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
