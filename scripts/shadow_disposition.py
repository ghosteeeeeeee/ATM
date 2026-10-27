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
  3. zero-event rule      -> NO parseable source healthy (rows>0) for 14d while
                             status=open -> auto-KILL ticket. Missing paths get
                             a 14d grace tracked in state; a healthy sibling path
                             anywhere in the stream string vetoes the rule.
  4. done entries         -> verifies their action stuck (timers disabled, flags
                             off) and reports regressions (deduped per finding)
  5. threshold_eval       -> OPTIONAL per-entry evaluator name (entries carry
                             {threshold_eval: <key>} -> THRESHOLD_EVALS). Runs the
                             entry's pre-registered numeric trip condition
                             ("revert if X") BEFORE the deadline does, so a trial
                             that turns bad reverts on the breach instead of
                             waiting for deadline day. Missing/unknown eval name
                             is reported and skipped — the deadline path still
                             applies, so a wiring gap can never kill the entry.
                             brain_auditor 2026-10-27 run #190: before this, the
                             coupled-SL trial's two live trip conditions
                             (7d-PnL / worst-HML-exit) had NO code path at all —
                             same defect class as the Oct-24 waiver lapse (#102).

Robustness contract (code review 2026-10-27 MED-4/5/6/7, LOW-1/5):
  - dedupe keys are applied ONLY after a successful kanban append (a failed
    append must never swallow the packet);
  - one bad entry (naive deadline string, bad types) is reported and skipped —
    it cannot abort the run or the remaining entries;
  - deadlines without tzinfo are treated as UTC (date-only strings are naive
    in py3.11+ and would otherwise TypeError against an aware `now`);
  - packet lines and regression lines are both deduped via state.

Output: automation/ceo/shadow_disposition_report.md (fresh each run) + bounded,
deduped kanban appends (state: data/shadow_disposition_state.json).
Schedule: hermes-shadow-disposition.timer (daily 08:15 UTC — was weekly;
  day-scale registry deadlines need a day-scale runner, brain_auditor #190 2026-10-27).
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
ZERO_EVENT_DAYS = 14

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
    """All brain/*.db|data/*.json[l] paths mentioned in the stream string."""
    # bug_hunter MED-3: alternation order matters — 'json' before 'jsonl' made every
    # *.jsonl path resolve to *.json (permanent "missing" -> false auto-KILL after 14d).
    return re.findall(r'(?:brain|data)/[\w./-]+\.(?:db|jsonl|json)', entry.get('stream', ''))


def stream_livenesses(entry):
    """Per-path [{'path','state':ok|error|missing,'rows':int|None,'age':days}] —
    ALL paths are evaluated (review MED-6: first-path-only missed healthy siblings
    and .json sources). rows: .db -> total rows, .json/.jsonl -> line count, None = unknown."""
    out = []
    for rel in stream_source_paths(entry):
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            out.append({'path': rel, 'state': 'missing', 'rows': None, 'age': None})
            continue
        age = max(0.0, (NOW.timestamp() - os.path.getmtime(p)) / 86400.0)
        rows = None
        state = 'ok'
        if rel.endswith('.db'):
            try:
                conn = sqlite3.connect(f'file:{p}?mode=ro', uri=True, timeout=5)
                try:
                    tbls = [r[0] for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name NOT LIKE 'sqlite_%'")]
                    rows = sum(conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
                               for t in tbls) if tbls else 0
                finally:
                    conn.close()
            except Exception:
                state = 'error'          # errors are NOT evidence of emptiness
        else:
            try:
                with open(p, 'rb') as f:
                    rows = sum(chunk.count(b'\n') for chunk in iter(lambda: f.read(1 << 20), b''))
            except Exception:
                state = 'error'
        out.append({'path': rel, 'state': state, 'rows': rows, 'age': age})
    return out


def zero_event_decision(lives, st, now_iso):
    """(fire: bool, detail: str) — 14d grace everywhere (review MED-6)."""
    if not lives:
        return False, '(no parseable source)'
    detail = ' | '.join(
        (f"{L['path']}: missing" if L['state'] == 'missing'
         else f"{L['path']}: err" if L['state'] == 'error'
         else f"{L['path']}: {L['rows']} rows, {L['age']:.1f}d")
        for L in lives)
    healthy = [L for L in lives if L['state'] == 'ok' and (L['rows'] or 0) > 0]
    if healthy:
        st.pop('first_missing_at', None)
        return False, detail
    oks = [L for L in lives if L['state'] == 'ok']          # known-empty files
    errs = [L for L in lives if L['state'] == 'error']      # unknowable -> never fire
    missing = [L for L in lives if L['state'] == 'missing']
    if oks and all((L['rows'] or 0) == 0 for L in oks) and not errs:
        oldest = max(L['age'] for L in oks)
        if oldest >= ZERO_EVENT_DAYS:
            return True, detail + ' -> ZERO-EVENT (empty >=14d)'
        return False, detail
    if missing and not oks and not errs:
        # all missing: 14d grace from FIRST sighting (a typo/archived path must not
        # instantly kill a healthy stream — review MED-6 proof)
        fm = st.get('first_missing_at')
        if not fm:
            st['first_missing_at'] = now_iso
            return False, detail + ' -> all missing (grace starts now)'
        try:
            fm_dt = datetime.fromisoformat(str(fm).replace('Z', '+00:00'))
            if fm_dt.tzinfo is None:
                fm_dt = fm_dt.replace(tzinfo=timezone.utc)
            if (NOW - fm_dt) >= timedelta(days=ZERO_EVENT_DAYS):
                return True, detail + ' -> ZERO-EVENT (missing >=14d since first sighting)'
        except Exception:
            pass
        return False, detail + ' -> all missing (grace running)'
    return False, detail  # mixed error/healthy/empty -> never fire


def timer_active(unit):
    try:
        r = subprocess.run(['systemctl', 'is-active', unit],
                           capture_output=True, text=True, timeout=10)
        return (r.stdout or '').strip()
    except Exception:
        return 'unknown'


def parse_deadline(dl):
    """Aware UTC datetime or None on garbage (never raises — review MED-5)."""
    try:
        dt = datetime.fromisoformat(str(dl).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ── threshold evaluators ─────────────────────────────────────────────────────
def _registry_limits(threshold_text):
    """(pnl_limit, hml_limit) pulled OUT of the free-text threshold string so the
    registry stays the single source of truth — no duplicated magic numbers here.
    None on unparsable. Never raises."""
    m_pnl = re.search(r'PnL\s*<\s*(-?\d+(?:\.\d+)?)', threshold_text)
    m_hml = re.search(r'worse than\s+(-?\d+(?:\.\d+)?)%', threshold_text)
    return (float(m_pnl.group(1)) if m_pnl else None,
            float(m_hml.group(1)) if m_hml else None)


def trial_metrics(started):
    """Postgres read for a trial entry: (trial_pnl, n_closed, worst_hml_pct,
    n_hml, rolling_7d_pnl). Cursor closed in finally; psycopg2 imported lazily so
    a missing driver degrades to a reported entry error, not a dead weekly run."""
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(pnl_usdt),0)::float, COUNT(*) FROM trades "
                    "WHERE status='closed' AND close_time >= %s", (started,))
        trial_pnl, n = cur.fetchone()
        cur.execute("SELECT COALESCE(MIN(pnl_pct),0)::float, COUNT(*) FROM trades "
                    "WHERE status='closed' AND exit_reason='hard_max_loss' "
                    "AND close_time >= %s", (started,))
        worst_hml, n_hml = cur.fetchone()
        cur.execute("SELECT COALESCE(SUM(pnl_usdt),0)::float FROM trades "
                    "WHERE status='closed' AND close_time > NOW() - INTERVAL '7 days'")
        rolling = cur.fetchone()[0]
        cur.close()
        return float(trial_pnl), int(n), float(worst_hml), int(n_hml), float(rolling)
    finally:
        conn.close()


def evaluate_trial_threshold(threshold_text, started, metrics):
    """Pure decision: (breached, detail).

    Only ATTRIBUTABLE-to-trial numbers can breach. The registry's 'rolling 7d' is
    reported as context but deliberately does NOT trip the guard on its own:
    for the first 7 trial-days that window still contains pre-trial closes, so
    tripping on it would demand a revert for bleed the trial did not cause.
    Started is date-only in the registry, so same-day pre-start closes are
    included in trial_pnl (immaterial vs a -2.50 limit, documented here).
    """
    pnl_limit, hml_limit = _registry_limits(threshold_text)
    if pnl_limit is None and hml_limit is None:
        return False, 'threshold not parseable (no numeric limit) — deadline path still applies'
    trial_pnl, n, worst_hml, n_hml, rolling = metrics
    hits = []
    if pnl_limit is not None and trial_pnl < pnl_limit:
        hits.append(f'trial PnL {trial_pnl:+.2f} < {pnl_limit}')
    if hml_limit is not None and n_hml and worst_hml < hml_limit:
        hits.append(f'worst HML exit {worst_hml:+.2f}% < {hml_limit}%')
    detail = (f'trial since {started}: PnL {trial_pnl:+.2f} over {n} closes (limit {pnl_limit}), '
              f'worst HML {worst_hml:+.2f}% over {n_hml} exits (limit {hml_limit}), '
              f'rolling7d {rolling:+.2f} context-only')
    if hits:
        return True, detail + ' -> BREACH: ' + '; '.join(hits)
    return False, detail


def _eval_trial_revert_guard(e):
    started = str(e.get('started') or e.get('deadline') or '')[:10]
    if len(started) < 10:
        return False, 'no usable started/deadline date — cannot attribute PnL'
    return evaluate_trial_threshold(str(e.get('threshold', '')), started + ' 00:00:00',
                                    trial_metrics(started + ' 00:00:00'))


THRESHOLD_EVALS = {
    'trial_revert_guard': _eval_trial_revert_guard,
}


def main():
    reg = _load(REGISTRY, None)
    if not reg or 'entries' not in reg:
        log('ERROR: registry missing/empty — cannot run')
        return 1
    state = _load(STATE, {})
    now_iso = NOW.isoformat()
    # bug_hunter MED-1: a stray non-dict entry crashed the header genexpr and the
    # loop's e.get BEFORE the per-entry try — one bad JSON value killed the whole
    # weekly run. Filter at load, report the skip, and keep eid assignment inside
    # the try (eid pre-set so the except can still name the entry).
    raw_entries = reg.get('entries') or []
    entries = [e for e in raw_entries if isinstance(e, dict)]
    n_nondict = len(raw_entries) - len(entries)
    report = [
        f'# Shadow disposition report — {now_iso}',
        f"registry: {len(entries)} entries "
        f"(open={sum(1 for e in entries if e.get('status') == 'open')})"
        + (f" | SKIPPED non-dict entries: {n_nondict}" if n_nondict else ''),
        ''
    ]
    kanban_lines = []
    # (eid, state_key, value) pairs applied ONLY after a successful kanban append
    # (review MED-4: recording dedupe keys on a failed append loses the packet forever)
    pending_state = []
    problems = 0
    entry_errors = 0

    for e in entries:
        eid = '?'
        try:
            eid = e.get('id', '?')
            st = state.setdefault(eid, {})
            status = e.get('status', 'open')

            # ── verify DONE actions stuck (regression check) ───────────────
            if status == 'done':
                act = e.get('action_taken', '')
                reg_sigs = []
                for unit in re.findall(r'(hermes-[\w-]+\.timer)', act):
                    if timer_active(unit) not in ('inactive', 'unknown'):
                        reg_sigs.append(f'timer:{unit}')
                for flag in re.findall(r'([A-Z_]+)\s*=\s*False', act):  # ALL flags (MED-7)
                    try:
                        out = subprocess.run(
                            ['grep', '-E', f'^{flag}\\s*=',
                             f'{REPO}/scripts/hermes_constants.py'],
                            capture_output=True, text=True, timeout=10).stdout
                        if '= True' in out:
                            reg_sigs.append(f'flag:{flag}')
                    except Exception:
                        pass
                if reg_sigs:
                    sig = ','.join(sorted(reg_sigs))
                    if st.get('regression_fired_for') != sig:   # dedupe (LOW-1)
                        # bug_hunter MED-2: queue via pending_state — recorded only
                        # after a successful kanban append (else the packet is
                        # deduped away forever while the report claims otherwise)
                        pending_state.append((eid, 'regression_fired_for', sig))
                        problems += 1
                        kanban_lines.append(
                            f'- [{now_iso}] shadow-disposition: ⚠️ REGRESSION {eid} — '
                            f'{sig} reverted after KILL (action_taken says otherwise)')
                report.append(f'- DONE {eid}: {e.get("disposition", "?")} '
                              f'({e.get("done_at", "?")})')
                continue

            # ── liveness / zero-event ───────────────────────────────────────
            lives = stream_livenesses(e)
            zero_event, detail = zero_event_decision(lives, st, now_iso)
            report.append(f'- OPEN {eid}: deadline={e.get("deadline", "?")} | {detail}')
            if zero_event and not st.get('zerokill_fired'):
                # bug_hunter MED-2: queue via pending_state (append-success-only)
                pending_state.append((eid, 'zerokill_fired', now_iso))
                problems += 1
                kanban_lines.append(
                    f'- [{now_iso}] shadow-disposition: 🔪 AUTO-KILL TICKET {eid} — '
                    f'source empty/missing ≥{ZERO_EVENT_DAYS}d while status=open '
                    f'(registry rule). Default action: '
                    f'{e.get("default_action", "KILL")}. 24h CEO clock.')
                report.append(f'  -> ZERO-EVENT RULE HIT for {eid} (auto-KILL ticket issued once)')

            # ── pre-registered threshold trip (before deadline) ──────────────
            ev_name = e.get('threshold_eval')
            if ev_name:
                ev = THRESHOLD_EVALS.get(ev_name)
                if ev is None:
                    entry_errors += 1
                    report.append(f'  -> UNKNOWN threshold_eval {ev_name!r} '
                                  f'(deadline path still applies)')
                else:
                    try:
                        breached, detail = ev(e)
                    except Exception as ex:
                        entry_errors += 1
                        report.append(f'  -> threshold_eval {ev_name} error: '
                                      f'{type(ex).__name__}: {ex} (deadline path still applies)')
                    else:
                        report.append(f'  -> threshold: '
                                      f'{"BREACHED" if breached else "not breached"} | {detail}')
                        if not breached:
                            st.pop('threshold_fired', None)   # re-arm for a later breach
                        elif not st.get('threshold_fired'):
                            # append-success-only recording (review MED-4 contract)
                            pending_state.append((eid, 'threshold_fired', now_iso))
                            problems += 1
                            kanban_lines.append(
                                f'- [{now_iso}] shadow-disposition: 🚨 THRESHOLD BREACHED {eid} — '
                                f'{detail}. Default action: '
                                f'{e.get("default_action", "(registry missing default_action)")}. '
                                f'24h CEO clock to revert or override with evidence.')

            # ── deadline handling ──────────────────────────────────────────
            dl = e.get('deadline')
            if not dl:
                continue
            dl_dt = parse_deadline(dl)
            if dl_dt is None:
                entry_errors += 1
                report.append(f'  -> UNPARSABLE deadline {dl!r} for {eid} (entry skipped)')
                continue
            if NOW >= dl_dt:
                if st.get('default_fired_for') != str(dl):
                    pending_state.append((eid, 'default_fired_for', str(dl)))
                    problems += 1
                    kanban_lines.append(
                        f'- [{now_iso}] shadow-disposition: ⏰ DEFAULT FIRES {eid} — deadline '
                        f'{dl} passed with no disposition. Default action: '
                        f'{e.get("default_action", "(registry missing default_action)")}. '
                        f'24h CEO clock to override with a decision+evidence.')
                    report.append(f'  -> DEADLINE PASSED for {eid} (default packet queued)')
                else:
                    report.append(f'  -> deadline passed (packet already issued) for {eid}')
            elif (dl_dt - NOW) <= timedelta(hours=24):
                if st.get('due_warned') != str(dl):
                    pending_state.append((eid, 'due_warned', str(dl)))
                    problems += 1
                    kanban_lines.append(
                        f'- [{now_iso}] shadow-disposition: ⚠️ DECISION DUE {eid} — deadline '
                        f'{dl} within 24h. Threshold: {e.get("threshold", "?")}. '
                        f'Default if silent: {e.get("default_action", "?")}')
                    report.append(f'  -> DECISION DUE within 24h for {eid}')
        except Exception as ex:
            entry_errors += 1
            problems += 1
            report.append(f'- ERROR {eid}: {type(ex).__name__}: {ex} (entry skipped, '
                          f'run continues)')

    # ── emit ────────────────────────────────────────────────────────────────
    append_ok = True
    if kanban_lines:
        try:
            with open(KANBAN, 'a') as f:
                f.write(f'\n## shadow_disposition run {now_iso} ({len(kanban_lines)} action(s))\n')
                f.write('\n'.join(kanban_lines) + '\n')
            log(f'{len(kanban_lines)} packet line(s) -> {KANBAN}')
        except Exception as e:
            append_ok = False
            log(f'ERROR: kanban append failed ({e}) — packets NOT deduped, '
                f'will re-issue next run')
    else:
        log('no new packets (all deduped or nothing due)')

    if append_ok:
        for eid, key, val in pending_state:
            state.setdefault(eid, {})[key] = val
    else:
        report.append('!! kanban append FAILED — dedupe keys withheld (packets re-issue next run)')

    try:
        _save(STATE, state)
    except Exception as e:
        log(f'WARN: state save failed: {e}')

    try:
        with open(REPORT, 'w') as f:
            f.write('\n'.join(report) + '\n')
        log(f'report -> {REPORT}')
    except Exception as e:
        log(f'WARN: report write failed: {e}')

    for line in report:
        print(line)
    log(f'done — {problems} action(s) issued, {entry_errors} entry error(s)')
    return 0


def selfcheck():
    """One runnable check for the threshold guard — fixtures first (no DB needed),
    then the live read, then the wiring assert that catches the #102-class bug
    (code present but the registry never names it)."""
    ok = True

    def chk(cond, name):
        nonlocal ok
        print(('PASS  ' if cond else 'FAIL  ') + name, flush=True)
        ok = ok and bool(cond)

    th = ('revert if rolling 7d trial PnL < -2.50 OR any single hard_max_loss exit '
          'worse than -6.5% account')
    chk(_registry_limits(th) == (-2.5, -6.5), 'registry threshold parses -> (-2.5, -6.5)')
    chk(_registry_limits('no numbers here') == (None, None), 'unparsable -> (None, None)')

    b, d = evaluate_trial_threshold(th, 'x', (-2.60, 9, -4.80, 0, -0.47))
    chk(b and 'trial PnL -2.60 < -2.5' in d, 'trial-PnL breach detected')
    b, d = evaluate_trial_threshold(th, 'x', (0.62, 17, -7.10, 3, -0.47))
    chk(b and 'worst HML exit -7.10% < -6.5' in d, 'worst-HML breach detected')
    b, d = evaluate_trial_threshold(th, 'x', (0.62, 17, -4.83, 1, -0.47))
    chk(not b, 'healthy trial -> no breach')
    b, d = evaluate_trial_threshold('garbage', 'x', (0.62, 17, -4.83, 1, -0.47))
    chk(not b, 'unparsable threshold -> no false packet')
    b, d = evaluate_trial_threshold(th, 'x', (0.62, 17, -4.83, 1, -3.50))
    chk(not b, 'rolling7d under limit alone does NOT breach (pre-trial attribution)')
    b, d = evaluate_trial_threshold(th, 'x', (0.62, 17, 0.0, 0, -0.47))
    chk(not b, 'zero HML exits -> HML limb cannot breach on COALESCE(0)')

    reg = _load(REGISTRY, None) or {}
    ent = next((x for x in reg.get('entries', [])
                if isinstance(x, dict) and x.get('id') == 'trial-coupled-cutsloser-sl'), None)
    chk(ent is not None and ent.get('threshold_eval') in THRESHOLD_EVALS,
        'registry wiring: trial-coupled-cutsloser-sl names a known threshold_eval')

    try:
        m = trial_metrics('2026-10-27 00:00:00')
        chk(len(m) == 5 and all(isinstance(x, (int, float)) for x in m),
            f'live metrics well-formed {m}')
        b, d = evaluate_trial_threshold(th, '2026-10-27 00:00:00', m)
        print(f'        live: {d} | breached={b}', flush=True)
    except Exception as ex:
        chk(False, f'live metrics read failed: {type(ex).__name__}: {ex}')

    print('SELFCHECK ' + ('PASS' if ok else 'FAIL'), flush=True)
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        if '--selfcheck' in sys.argv:
            sys.exit(selfcheck())
        sys.exit(main())
    except Exception as e:
        print(f'[shadow-disposition] FATAL (weekly timer must not die silently): {e}',
              flush=True)
        sys.exit(1)
