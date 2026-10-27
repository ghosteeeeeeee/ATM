#!/usr/bin/env python3
"""
shadow_disposition.py — SHADOW-RECKONING learning-loop runner (CEO consult
20261027T024741Z, T sign-off 2026-10-27).

The fix for "we collect shadow data forever and never decide": every stream/
escalation in data/shadow_disposition.json carries {threshold, deadline,
default_action}. This runner:

  1. deadline passed      -> DEFAULT packet appended to ceo_kanban.md
                             (24h CEO clock: silence lets the default fire)
  2. deadline within 24h  -> DECISION DUE line in report (+kanban once)
  3. zero-event rule      -> source file missing/empty for 14d while status=open
                             -> auto-KILL ticket
  4. done entries         -> verifies their action stuck (timers still disabled,
                             flags still off) and reports any regression

Output: automation/ceo/shadow_disposition_report.md (fresh each run) + bounded,
deduped kanban appends (state: data/shadow_disposition_state.json).
Never raises out of main() — a broken stream must not break the weekly timer.

Schedule: hermes-shadow-disposition.timer (Mon 08:15 UTC weekly).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import HERMES_DATA  # noqa: E402

REGISTRY = os.path.join(HERMES_DATA, 'shadow_disposition.json')
STATE = os.path.join(HERMES_DATA, 'shadow_disposition_state.json')
KANBAN = '/root/.hermes/automation/ceo/ceo_kanban.md'
REPORT = '/root/.hermes/automation/ceo/shadow_disposition_report.md'
REPO = '/root/.hermes'

NOW = datetime.now(timezone.utc)


def log(msg):
    print(f"[shadow-disposition] {msg}", flush=True)


def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log(f"WARN: cannot load {path}: {e}")
        return default


def _save(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def stream_source_paths(entry):
    """Extract brain/*.db|data/*.json[l] paths mentioned in the stream string."""
    return re.findall(r'(?:brain|data)/[\w./-]+\.(?:db|json|jsonl)', entry.get('stream', ''))


def stream_liveness(entry):
    """(rows, age_days, detail) for the first parseable source file, else None."""
    for rel in stream_source_paths(entry):
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            return (0, 9999, f'{rel}: MISSING')
        age = (NOW.timestamp() - os.path.getmtime(p)) / 86400.0
        size = os.path.getsize(p)
        rows = None
        detail = f'{rel}: {size}B, age {age:.1f}d'
        if rel.endswith('.db'):
            try:
                conn = sqlite3.connect(f'file:{p}?mode=ro', uri=True, timeout=5)
                try:
                    tbls = [r[0] for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'")]
                    if tbls:
                        rows = sum(conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                                   for t in tbls)
                        detail = f'{rel}: {rows} rows across {len(tbls)} tables, age {age:.1f}d'
                finally:
                    conn.close()
            except Exception as e:
                detail = f'{rel}: db-error {e}'
        elif rel.endswith('.jsonl'):
            try:
                with open(p, 'rb') as f:
                    rows = sum(chunk.count(b'\n') for chunk in iter(lambda: f.read(1 << 20), b''))
                detail = f'{rel}: {rows} lines, age {age:.1f}d'
            except Exception as e:
                detail = f'{rel}: read-error {e}'
        # bare .json: keep byte/age detail (rows stays None -> no zero-event trigger)
        return (rows, age, detail)
    return None


def timer_active(unit):
    try:
        r = subprocess.run(['systemctl', 'is-active', unit],
                           capture_output=True, text=True, timeout=10)
        return (r.stdout or '').strip()
    except Exception:
        return 'unknown'


def main():
    reg = _load(REGISTRY, None)
    if not reg or 'entries' not in reg:
        log('ERROR: registry missing/empty — cannot run')
        return 1
    state = _load(STATE, {})
    now_iso = NOW.isoformat()
    report = [
        f'# Shadow disposition report — {now_iso}',
        f"registry: {len(reg['entries'])} entries "
        f"(open={sum(1 for e in reg['entries'] if e.get('status') == 'open')})",
        ''
    ]
    kanban_lines = []
    problems = 0

    for e in reg['entries']:
        eid = e.get('id', '?')
        status = e.get('status', 'open')
        st = state.setdefault(eid, {})

        # ── verify DONE actions stuck (regression check) ─────────────────────
        if status == 'done':
            act = e.get('action_taken', '')
            for unit in re.findall(r'(hermes-[\w-]+\.timer)', act):
                if timer_active(unit) not in ('inactive', 'unknown'):
                    problems += 1
                    kanban_lines.append(
                        f'- [{now_iso}] shadow-disposition: ⚠️ REGRESSION {eid} — {unit} is '
                        f'BACK ACTIVE after KILL (action_taken says disabled)')
            flag = re.search(r'([A-Z_]+)\s*=\s*False', act)
            if flag:
                try:
                    out = subprocess.run(
                        ['grep', '-E', f'^{flag.group(1)}\\s*=',
                         f'{REPO}/scripts/hermes_constants.py'],
                        capture_output=True, text=True, timeout=10).stdout
                    if '= True' in out:
                        problems += 1
                        kanban_lines.append(
                            f'- [{now_iso}] shadow-disposition: ⚠️ REGRESSION {eid} — '
                            f'{flag.group(1)} re-enabled after KILL')
                except Exception:
                    pass
            report.append(f'- DONE {eid}: {e.get("disposition", "?")} ({e.get("done_at", "?")})')
            continue

        # ── liveness / zero-event rule ───────────────────────────────────────
        live = stream_liveness(e)
        zero_event = False
        if live:
            rows, age, detail = live
            report.append(f'- OPEN {eid}: deadline={e.get("deadline", "?")} | {detail}')
            if rows == 0 and age >= 14 and e.get('kind') in ('shadow', 'concept'):
                zero_event = True
        else:
            report.append(f'- OPEN {eid}: deadline={e.get("deadline", "?")} | (no parseable source)')

        if zero_event:
            if not st.get('zerokill_fired'):
                st['zerokill_fired'] = now_iso
                problems += 1
                kanban_lines.append(
                    f'- [{now_iso}] shadow-disposition: 🔪 AUTO-KILL TICKET {eid} — '
                    f'source empty/missing ≥14d while status=open (registry rule). '
                    f'Default action: {e.get("default_action", "KILL")}. 24h CEO clock.')
            report.append(f'  -> ZERO-EVENT RULE HIT for {eid} (auto-KILL ticket issued once)')

        # ── deadline handling ────────────────────────────────────────────────
        dl = e.get('deadline')
        if not dl:
            continue
        try:
            dl_dt = datetime.fromisoformat(str(dl).replace('Z', '+00:00'))
        except Exception:
            report.append(f'  -> unparsable deadline {dl} for {eid}')
            continue
        if NOW >= dl_dt:
            if not st.get('default_fired_for') == str(dl):
                st['default_fired_for'] = str(dl)
                problems += 1
                kanban_lines.append(
                    f'- [{now_iso}] shadow-disposition: ⏰ DEFAULT FIRES {eid} — deadline '
                    f'{dl} passed with no disposition. Default action: '
                    f'{e.get("default_action", "(registry missing default_action)")}. '
                    f'24h CEO clock to override with a decision+evidence.')
                report.append(f'  -> DEADLINE PASSED for {eid} (default packet issued)')
            else:
                report.append(f'  -> deadline passed (packet already issued) for {eid}')
        elif (dl_dt - NOW) <= timedelta(hours=24):
            if not st.get('due_warned') == str(dl):
                st['due_warned'] = str(dl)
                kanban_lines.append(
                    f'- [{now_iso}] shadow-disposition: ⚠️ DECISION DUE {eid} — deadline '
                    f'{dl} within 24h. Threshold: {e.get("threshold", "?")}. '
                    f'Default if silent: {e.get("default_action", "?")}')
                report.append(f'  -> DECISION DUE within 24h for {eid}')

    # ── emit ────────────────────────────────────────────────────────────────
    try:
        with open(REPORT, 'w') as f:
            f.write('\n'.join(report) + '\n')
        log(f'report -> {REPORT}')
    except Exception as e:
        log(f'WARN: report write failed: {e}')

    if kanban_lines:
        try:
            with open(KANBAN, 'a') as f:
                f.write(f'\n## shadow_disposition run {now_iso} ({len(kanban_lines)} action(s))\n')
                f.write('\n'.join(kanban_lines) + '\n')
            log(f'{len(kanban_lines)} packet line(s) -> {KANBAN}')
        except Exception as e:
            log(f'WARN: kanban append failed: {e}')
    else:
        log('no new packets (all deduped or nothing due)')

    _save(STATE, state)
    for line in report:
        print(line)
    log(f'done — {problems} action(s) issued this run')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'[shadow-disposition] FATAL (weekly timer must not die silently): {e}', flush=True)
        sys.exit(1)
