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

  6. control tower        -> automation/ceo/control_tower.md, rewritten EVERY run:
                             OVERDUE / DUE<=24h / <=7d / 8-14d / later, running
                             trials with live n-vs-bar (progress_eval hooks),
                             full date-ordered calendar, done collapsed. CEO
                             APPROVE 2026-10-31 (brief-control-tower): the single
                             centralized spot for shadows + trials + calendar.
                             Regenerated-only — hand edits are overwritten (the
                             hand dashboard brain/trial_tracking_dashboard.md
                             rotted precisely because it lacked this rule).
  7. weekly LOOKAHEAD     -> once per ISO week, one kanban packet listing every
                             item due <=7d with owner + tower freshness — the
                             calendar-drives-action layer that warns BEFORE the
                             daily 24h packet and the deadline default.
  8. auto-flip packet      -> AUTO-FLIP POLICY (CEO 20261108T230547Z): gate
                             admissions with registered defaults auto-flip via
                             this packet (flag flip = one-line constants edit
                             on receipt, no waiting for a human to read at
                             2am); money-sizing/mults/protected flags NEVER
                             auto-flip. Opt-in: an entry carries
                             auto_flip_flag = '<HERMES_CONSTANTS_FLAG>' plus a
                             bar evaluator (auto_flip_check preferred, else
                             threshold_eval — for an opt-in entry the
                             evaluator's True means bar MET). When the bar is
                             MET the runner emits ONE loud [AUTO-FLIP-READY]
                             kanban packet (state-deduped, fires once) and
                             NEVER touches hermes_constants.py itself — that
                             file is human/CEO-owned and imported at process
                             start, so the actual flip stays a reviewed
                             one-line constants edit executed by the
                             parent/CEO on receipt of the packet. No registry
                             entry carries auto_flip_flag today
                             (storm-confl-waiver ruled NO-CONVERT
                             20261108T230547Z; mechanism ships ready, entries
                             opt in later).
                             Guards (reviews 2026-11-09): a threshold_eval
                             fallback is BREACH-style in this runner, so the
                             entry must ALSO declare auto_flip_polarity=
                             "true=met" (or register a positive-semantics
                             auto_flip_check) or the bar is reported
                             unknowable; protected/money/mult flags are
                             refused by auto_flip_flag_blocked()
                             (CEO_PROTECTED_FLAGS + denylist patterns) —
                             enforced in code, never prose alone; and
                             auto_flip_fired RE-ARMS when the bar clears
                             (mirror of threshold_fired) so a revert-then-
                             re-met bar can packet again.

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
CONTROL_TOWER = '/root/.hermes/automation/ceo/control_tower.md'
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
    # review MED-4: pid-unique tmp so overlapping runs can't interleave into
    # one fixed path and atomically publish a corrupted file.
    tmp = f'{path}.{os.getpid()}.tmp'
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


# ── progress evaluators (control-tower n-vs-bar; CEO build 2026-10-31) ────────
# Mirror of the THRESHOLD_EVALS registration pattern: entries carry
# {progress_eval: <key>} -> PROGRESS_EVALS. Each takes the entry (so bar targets
# are parsed from the registry text — no duplicated magic numbers here) and
# returns {'now','target','unit','met'} or {'error': str}. NEVER raises: a broken
# hook degrades to a rendered "unavailable" line, so the tower always renders and
# the deadline path is untouched (same contract as threshold_eval).

def _run_trial_report(flag):
    """Combined stdout+stderr of shadow_trader.py <flag>. Raises on nonzero rc or
    empty output (crash/format drift) so the caller renders a degraded line
    instead of parsing a partial traceback as authoritative (review LOW-6)."""
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, 'scripts', 'shadow_trader.py'), flag],
        capture_output=True, text=True, timeout=150)
    out = (r.stdout or '') + (r.stderr or '')
    if r.returncode != 0:
        raise RuntimeError(f'{flag} rc={r.returncode}: {out.strip()[-200:]}')
    if not out.strip():
        raise RuntimeError(f'shadow_trader.py {flag} produced no output (rc={r.returncode})')
    return out


def _progress_wider_sl(e):
    """Wider-SL trial. The bar has TWO limbs (WR >= t AND trades >= n_target);
    both are parsed from the report's own 'Required:' line so shadow_trader
    stays the single source of truth. Collecting state (n below bar) and any
    unverifiable n-limb degrade to CONSERVATIVE 'not met' — a false OK would
    contradict the bar (review MED-3)."""
    try:
        out = _run_trial_report('--report-wider')
    except Exception as ex:
        return {'error': f'{type(ex).__name__}: {ex}'}
    req = re.search(r'Required:\s*WR\s*>=\s*(-?\d+(?:\.\d+)?)%\s*'
                    r'with\s*>=\s*(\d+)\s*trades', out)
    wr_m = re.search(r'Wider:\s*WR\s*=\s*(-?\d+(?:\.\d+)?)%,\s*trades\s*=\s*(\d+)',
                     out)
    if req and wr_m:
        v, n = float(wr_m.group(1)), int(wr_m.group(2))
        t, n_target = float(req.group(1)), int(req.group(2))
        collecting = 'COLLECTING DATA' in out
        met = (not collecting) and v >= t and n >= n_target
        unit = (f'% WR wider-arm, n={n}/{n_target}'
                + (' [COLLECTING]' if collecting else ''))
        return {'now': v, 'target': t, 'unit': unit, 'met': met}
    # verdict/Win-Rate fallbacks: n limb cannot be verified -> conservative
    m = re.search(r'WR\s+(-?\d+(?:\.\d+)?)%\s*[<>]=?\s*(\d+(?:\.\d+)?)%', out)
    if m:
        return {'now': float(m.group(1)), 'target': float(m.group(2)),
                'unit': '% WR wider-arm [n-limb unverified]', 'met': False}
    m = re.search(r'Win Rate\s+(-?\d+(?:\.\d+)?)%\s+(-?\d+(?:\.\d+)?)%', out)
    if m:
        m2 = re.search(r'WR\s*>=\s*(-?\d+(?:\.\d+)?)', str(e.get('threshold', '')))
        if m2:
            return {'now': float(m.group(2)), 'target': float(m2.group(1)),
                    'unit': '% WR wider-arm [n-limb unverified]', 'met': False}
    return {'error': 'report format drift: no parseable WR/bar lines'}


# bug_hunter NEW-1: shadow_trader emits '{:+.1f}pp' — a sign is ALWAYS printed,
# so without \+? a POSITIVE improvement ('+4.9pp') parses as format drift exactly
# when the trial starts working (fails safe, but hides the decision-critical number).
_RE_TIME_EXT = re.compile(
    r'Extended:\s*WR improvement\s*=\s*\+?(-?\d+(?:\.\d+)?)pp,\s*trades\s*=\s*(\d+)')


def _progress_extended_time(e):
    """Extended-time-exits trial — same two-limb bar rule as wider_sl: the
    report's 'Required:' line carries BOTH the improvement target and the n
    floor; collecting state renders explicitly (review MED-3)."""
    try:
        out = _run_trial_report('--report-time')
    except Exception as ex:
        return {'error': f'{type(ex).__name__}: {ex}'}
    req = re.search(r'Required:\s*WR improvement\s*>=\s*\+?(-?\d+(?:\.\d+)?)pp\s*'
                    r'with\s*>=\s*(\d+)\s*trades', out)
    ext = _RE_TIME_EXT.search(out)
    if req and ext:
        v, n = float(ext.group(1)), int(ext.group(2))
        t, n_target = float(req.group(1)), int(req.group(2))
        collecting = 'Collecting data:' in out
        met = (not collecting) and v >= t and n >= n_target
        unit = (f'pp WR-improvement, n={n}/{n_target}'
                + (' [COLLECTING]' if collecting else ''))
        return {'now': v, 'target': t, 'unit': unit, 'met': met}
    if req and 'Collecting data:' in out:
        mc = re.search(r'Collecting data:\s*(\d+)/(\d+)', out)
        if mc:
            return {'now': int(mc.group(1)), 'target': int(mc.group(2)),
                    'unit': 'trades collected [COLLECTING]', 'met': False}
    return {'error': 'report format drift: no parseable improvement/bar lines'}


def _progress_contrarian_live(e):
    """CONTRARIAN-LIVE watch: count REAL fade trades = pump-chain- LONG opens
    since the watch started — PostgreSQL is authoritative (review HIGH-1: the
    original hook grepped logs/decider*.log, which does not exist; a log-grep
    replacement would still be wrong because only ~11 of 170 filtered log lines
    ever opened a trade — approved != executed, and logs rotate out)."""
    try:
        started = str(e.get('started') or '')[:10]
        if len(started) < 10:
            return {'error': 'no usable started date on entry'}
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql', database='brain',
                                user='postgres')
        try:
            cur = conn.cursor()
            # hyphen anchors pc- (pump-chain+ / -v6+ are the PLUS LONG family,
            # NOT fades — verified: 19 pc+ LONG vs 11 fade opens since 10-27)
            cur.execute("SELECT COUNT(*) FROM trades "
                        "WHERE signal LIKE 'pump-chain-%%' "
                        "AND signal NOT LIKE '%%+%%' AND direction='LONG' "
                        "AND open_time >= %s", (started,))
            v = int(cur.fetchone()[0])
            cur.close()
        finally:
            conn.close()
    except Exception as ex:
        return {'error': f'{type(ex).__name__}: {ex}'}
    m = re.search(r'>=\s*(\d+)\s*REAL', str(e.get('threshold', '')))
    t = int(m.group(1)) if m else 1                  # 'first real trade' semantics
    return {'now': v, 'target': t,
            'unit': 'real fade trades (pc- LONG opens since started)',
            'met': v >= t}


PROGRESS_EVALS = {
    'wider_sl': _progress_wider_sl,
    'extended_time': _progress_extended_time,
    'contrarian_live': _progress_contrarian_live,
}


# Protected-flag denylist (AUTO-FLIP POLICY, CEO 20261108T230547Z):
# "money-sizing/mults/protected flags NEVER auto-flip" — enforced in CODE
# (bug_hunter LOW-3 2026-11-09: prose is not a guard). Patterns are
# intentionally broad: a false REFUSE is harmless (a human can still flip the
# flag by hand), a false ALLOW hands a money flag an auto packet.
_AUTO_FLIP_BLOCKED_PATTERNS = (
    (re.compile(r'PM_TRAIL_'), 'PM-trail tier (CEO-protected)'),
    (re.compile(r'WINNER_CELL'), 'winner-cell sizing (money-sizing)'),
    (re.compile(r'_MULT$|_MULT_'), 'mult change (money-sizing)'),
    (re.compile(r'DAMPEN'), 'dampen flag (money-sizing)'),
    (re.compile(r'^(CUT_LOSER_PNL|ATR_SL_MAX|ATR_SL_MAX_INIT|HL_MIN_NOTIONAL)$'),
     'money/risk-sizing constant'),
    (re.compile(r'^LIVE_TRADING_ENABLED$'), 'master live-trading switch'),
)


def auto_flip_flag_blocked(flag):
    """reason `flag` may NEVER auto-flip, else None. Never raises.

    Checks (1) name shape — must look like a constants flag; (2) the house's
    own CEO_PROTECTED_FLAGS registry (imported read-only); (3) the money/mult
    denylist patterns above. Used BOTH in main() (loud report line) and
    inside auto_flip_packet() (defense in depth)."""
    f = str(flag or '').strip()
    if not f:
        return 'empty auto_flip_flag'
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*', f):
        return f'not a constants flag name: {f!r}'
    try:
        from hermes_constants import CEO_PROTECTED_FLAGS
        if f in CEO_PROTECTED_FLAGS:
            return f'CEO_PROTECTED_FLAGS member ({f})'
    except Exception:
        pass
    for pat, why in _AUTO_FLIP_BLOCKED_PATTERNS:
        if pat.search(f):
            return f'protected ({why})'
    return None


def auto_flip_bar(entry, preset=None):
    """(breached, detail) for an auto-flip entry's bar, or (None, why).

    Evaluator resolution: the entry's own `auto_flip_check`
    (THRESHOLD_EVALS style, preferred — its contract is POSITIVE:
    True = bar MET), else its `threshold_eval` — which is BREACH-style
    (True = bad news) in this runner — and that fallback is trusted only
    when the entry ALSO declares `auto_flip_polarity: "true=met"`
    (adversarial review MED-2: without the declaration an opt-in would emit
    "flip <flag> ON" for a losing trial plus two contradictory packets).
    `preset` is the already-computed (name, breached, detail) from the main
    threshold section — passed through so an opted-in evaluator never runs
    twice per run (duplicate Postgres reads, review MED-2 secondary).
    No evaluator / unknown name / error / missing polarity declaration ->
    (None, why): the packet is skipped and reported — a wiring gap can never
    fire a false flip packet (the #102 class). Never raises.
    """
    name = entry.get('auto_flip_check') or entry.get('threshold_eval')
    if not name:
        return None, 'no evaluator (threshold_eval/auto_flip_check) — bar unknowable'
    fn = THRESHOLD_EVALS.get(name)
    if fn is None:
        return None, f'unknown evaluator {name!r}'
    if preset is not None and preset[0] == name:
        breached, detail = preset[1], preset[2]
    else:
        try:
            breached, detail = fn(entry)
        except Exception as ex:
            return None, f'evaluator {name} error: {type(ex).__name__}: {ex}'
    if name == entry.get('threshold_eval') and not entry.get('auto_flip_check'):
        if str(entry.get('auto_flip_polarity', '')).strip().lower() != 'true=met':
            return None, (f'threshold_eval {name!r} is breach-style (True = bad news) — '
                          f'declare auto_flip_polarity="true=met" or register '
                          f'auto_flip_check (positive semantics)')
        detail = f'[polarity declared true=met] {detail}'
    return bool(breached), str(detail)


def auto_flip_packet(entry, st, now_iso, breached, detail):
    """(kanban_line, state_value) for a bar-met auto-flip entry, else
    (None, None). Pure — selfcheck calls it with fixtures.

    Fires ONCE per entry (state key auto_flip_fired); the caller queues the
    state write only after a successful kanban append (the MED-4
    append-success-only contract), and clears the key again if the bar later
    clears (re-arm, mirror of threshold_fired). Protected flags are refused
    here too (defense in depth behind main()'s report line). The line is
    deliberately loud and actionable — it names the exact one-line constants
    edit; the runner itself never edits hermes_constants.py.
    """
    flag = entry.get('auto_flip_flag')
    if not flag or entry.get('status') != 'open' or st.get('auto_flip_fired'):
        return None, None
    if auto_flip_flag_blocked(flag):
        return None, None
    if not breached:
        return None, None
    line = (
        f'- [{now_iso}] shadow-disposition: 🔄 [AUTO-FLIP-READY] '
        f'{entry.get("id", "?")} bar met — flip {flag} now (one-line command: '
        f'set {flag} = True in scripts/hermes_constants.py) | {detail} | '
        f'AUTO-FLIP POLICY (CEO 20261108T230547Z): gate admissions with '
        f'registered defaults auto-flip via this packet (flag flip = one-line '
        f'constants edit on receipt, no waiting for a human to read at 2am); '
        f'money-sizing/mults/protected flags NEVER auto-flip. Registry: '
        f'data/shadow_disposition.json')
    return line, now_iso


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
            _thr_resolved = None   # (name, breached, detail) for auto-flip reuse
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
                        _thr_resolved = (ev_name, breached, detail)
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

            # ── auto-flip packet (AUTO-FLIP POLICY, CEO 20261108T230547Z) ──
            # Gate admissions with a registered default: bar MET -> ONE loud
            # kanban packet (fires once, state-deduped) instead of waiting for
            # a human to read at 2am. The runner NEVER edits
            # hermes_constants.py (human/CEO-owned, imported at process start)
            # — the actual flip stays a one-line constants edit executed by the
            # parent/CEO on receipt. Opt-in field auto_flip_flag; no entry
            # carries it today (storm-confl-waiver is NO-CONVERT — mechanism
            # ships ready, entries opt in later). Guards (reviews 2026-11-09):
            # protected flags refused in code (denylist, never prose);
            # threshold_eval fallback needs auto_flip_polarity="true=met"
            # (breach-style evals); bar-not-met RE-ARMS auto_flip_fired so a
            # revert-then-re-met bar can packet again.
            if e.get('auto_flip_flag') and status == 'open':
                af_block = auto_flip_flag_blocked(e.get('auto_flip_flag'))
                if af_block:
                    report.append(f'  -> auto-flip REFUSED for {eid}: {af_block} '
                                  f'(protected flags NEVER auto-flip)')
                else:
                    af_breached, af_detail = auto_flip_bar(
                        e, preset=_thr_resolved)
                    if af_breached is None:
                        report.append(f'  -> auto-flip skipped for {eid}: {af_detail}')
                    elif not af_breached:
                        # re-arm mirror of threshold_fired (review LOW-7): a
                        # cleared bar must allow a later re-met to packet again
                        if st.pop('auto_flip_fired', None):
                            report.append(f'  -> auto-flip re-armed for {eid} '
                                          f'(bar no longer met)')
                    else:
                        af_line, af_val = auto_flip_packet(e, st, now_iso,
                                                           af_breached, af_detail)
                        if af_line:
                            # append-success-only recording (review MED-4 contract)
                            pending_state.append((eid, 'auto_flip_fired', af_val))
                            problems += 1
                            kanban_lines.append(af_line)
                            report.append(f'  -> AUTO-FLIP-READY packet queued for {eid} '
                                          f'(flip {e.get("auto_flip_flag")})')

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

    # ── weekly LOOKAHEAD packet (calendar-drives-action layer 1/3; CEO 2026-10-31)
    # One packet per ISO week listing every open item due <=7d with its owner —
    # warns BEFORE the daily 24h packet (layer 2) and the deadline default
    # (layer 3), so every date gets three independent chances to be seen. Dedupe
    # key lives under the reserved '_tower' state id and follows the same
    # append-success-only contract as every other packet.
    try:
        tower_st = state.setdefault('_tower', {})
        iso = NOW.isocalendar()
        week_key = f'{iso.year}-W{iso.week:02d}'
        if tower_st.get('lookahead_fired_for') != week_key:
            up = []
            for e in entries:
                if e.get('status') != 'open':
                    continue
                d = parse_deadline(e.get('deadline'))
                if d is not None and timedelta(0) <= (d - NOW) <= timedelta(days=7):
                    up.append((d, e))
            up.sort(key=lambda x: x[0])
            items = ', '.join(
                f"{e.get('id', '?')} ({d.strftime('%m-%d')}, "
                f"{str(e.get('owner', '?'))[:28]})"
                for d, e in up) or 'none due in 7d'
            pending_state.append(('_tower', 'lookahead_fired_for', week_key))
            problems += 1
            kanban_lines.append(
                f'- [{now_iso}] shadow-disposition: 📅 LOOKAHEAD {week_key} — '
                f'{len(up)} item(s) due <=7d: {items}. '
                f'Full view: automation/ceo/control_tower.md')
    except Exception as ex:
        entry_errors += 1
        report.append(f'- LOOKAHEAD packet error: {type(ex).__name__}: {ex} '
                      f'(daily packets unaffected)')


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

    # control tower: rendered LAST so it carries the run's final problem/error
    # counts; a tower failure must never fail the run (packets already emitted).
    try:
        _render_control_tower(entries, now_iso, problems, entry_errors)
        log(f'control tower -> {CONTROL_TOWER}')
    except Exception as e:
        log(f'WARN: control tower render failed: {e}')

    for line in report:
        print(line)
    log(f'done — {problems} action(s) issued, {entry_errors} entry error(s)')
    return 0


# ── control tower (CEO APPROVE 2026-10-31, brief-control-tower) ──────────────
def _fmt_progress(e, run=True):
    """Progress line for an entry, or None when it has no progress_eval.
    NEVER raises — unknown key / evaluator error / malformed output all degrade
    to a rendered string (the tower must always render)."""
    name = e.get('progress_eval')
    if not name:
        return None
    if not run:
        return 'progress: (skipped in selfcheck)'
    fn = PROGRESS_EVALS.get(name)
    if fn is None:
        return f'progress: UNKNOWN eval {name!r} (deadline path unaffected)'
    try:
        d = fn(e)
    except Exception as ex:
        return f'progress: unavailable ({type(ex).__name__}: {ex})'
    if not isinstance(d, dict):
        return 'progress: evaluator returned non-dict'
    if 'error' in d:
        return f"progress: unavailable ({d['error']})"
    try:
        mark = 'OK' if d.get('met') else 'NOT MET'
        return (f"progress: {d['now']} vs >={d['target']} "
                f"{d.get('unit', '')} — {mark}")
    except Exception:
        return 'progress: malformed evaluator output'


def _build_control_tower(entries, now_iso, problems, entry_errors,
                         prev_tower_mtime=None, reg_mtime=None, run_progress=True):
    """Pure builder -> tower markdown string (selfcheck calls this without disk
    writes and without subprocess progress hooks)."""
    stale = prev_tower_mtime is not None and \
        (NOW.timestamp() - prev_tower_mtime) > 26 * 3600

    opens = [e for e in entries if e.get('status') == 'open']
    dones = [e for e in entries if e.get('status') == 'done']

    def _dl(e):
        return parse_deadline(e.get('deadline'))

    dated, undated = [], []
    for e in opens:
        d = _dl(e)
        (dated if d is not None else undated).append((d, e))
    dated.sort(key=lambda x: x[0])

    # review MED-2: memoize progress per build — entries render in BOTH their
    # date bucket and the trials section; without this each hook could run
    # twice (worst case 720s vs the service's 300s TimeoutStartSec).
    prog_cache = {}

    def _fmt_cached(e):
        key = e.get('id') or id(e)
        if key not in prog_cache:
            prog_cache[key] = _fmt_progress(e, run=run_progress)
        return prog_cache[key]

    def _bucket(lo, hi):
        return [(d, e) for d, e in dated if lo < d <= hi]

    overdue = [(d, e) for d, e in dated if d <= NOW]
    due24 = _bucket(NOW, NOW + timedelta(hours=24))
    due7 = _bucket(NOW + timedelta(hours=24), NOW + timedelta(days=7))
    due14 = _bucket(NOW + timedelta(days=7), NOW + timedelta(days=14))
    later = [(d, e) for d, e in dated if d > NOW + timedelta(days=14)]

    def _entry_block(d, e):
        days = (d.date() - NOW.date()).days
        tag = ('TODAY' if days == 0
               else f'T-{days}' if days > 0 else f'OVERDUE {-days}d')
        bar = str(e.get('bar') or e.get('threshold') or '—')
        bar = re.sub(r'^bar:\s*', '', bar)   # entries may self-prefix "bar: "
        if len(bar) > 120:
            bar = bar[:117] + '...'
        prog = _fmt_cached(e) or 'progress: —'
        dflt = str(e.get('default_action') or '—')
        if len(dflt) > 120:
            dflt = dflt[:117] + '...'
        return (f"- {d.strftime('%Y-%m-%d')} [{tag}] `{e.get('id', '?')}` "
                f"(owner: {e.get('owner', '?')})\n"
                f"  - bar: {bar}\n"
                f"  - {prog}\n"
                f"  - if silent: {dflt}")

    lines = [
        '# CONTROL TOWER — shadows, trials, decision calendar',
        f'generated {now_iso} by scripts/shadow_disposition.py (daily 08:15) — '
        f'REGENERATED FILE, do not hand-edit (edit data/shadow_disposition.json)',
    ]
    if stale:
        prev_s = (datetime.fromtimestamp(prev_tower_mtime, timezone.utc)
                  .isoformat(timespec='seconds') if prev_tower_mtime else 'NEVER')
        lines.append(
            f'> ⚠️ **STALE** — last render {prev_s} (>26h ago): the daily timer '
            f'likely missed a cycle. Re-run `python3 scripts/shadow_disposition.py` '
            f'before trusting the dates below.')
    lines.append(f'{len(opens)} open / {len(dones)} done / '
                 f'{len(entries)} registry entries')
    lines.append('')

    def _section(title, pairs):
        if not pairs:
            return
        lines.append(f'## {title} ({len(pairs)})')
        for d, e in pairs:
            lines.append(_entry_block(d, e))
        lines.append('')

    _section('🔴 OVERDUE — default packet issued; override needs decision + '
             'evidence within 24h', overdue)
    _section('🟠 DUE ≤24h', due24)
    _section('🟡 DUE ≤7d', due7)
    _section('📅 DUE 8–14d', due14)
    _section('LATER (>14d)', later)

    trials = [e for e in opens if e.get('kind') in ('trial', 'watch')]
    if trials:
        lines.append(f'## ⚗️ RUNNING TRIALS ({len(trials)})')
        for e in sorted(trials, key=lambda x: str(x.get('deadline') or '9999')):
            d = _dl(e)
            dstr = d.strftime('%Y-%m-%d') if d else 'undated'
            bar = str(e.get('bar') or e.get('threshold') or '—')
            bar = re.sub(r'^bar:\s*', '', bar)   # entries may self-prefix "bar: "
            if len(bar) > 120:
                bar = bar[:117] + '...'
            lines.append(f"- `{e.get('id', '?')}` — due {dstr} | "
                         f"owner: {e.get('owner', '?')}")
            lines.append(f"  - bar: {bar}")
            lines.append(f"  - {_fmt_cached(e) or 'progress: —'}")
        lines.append('')

    if dated:
        lines.append('## 📅 CALENDAR — every dated open item, date-ordered')
        by_date = {}
        for d, e in dated:
            by_date.setdefault(d.date(), []).append(e.get('id', '?'))
        for dt in sorted(by_date):
            delta = (dt - NOW.date()).days
            tag = ('TODAY' if delta == 0
                   else f'T-{delta}' if delta > 0 else f'OVERDUE {-delta}d')
            lines.append(f"- {dt.isoformat()} [{tag}]: "
                         f"{', '.join(by_date[dt])}")
        lines.append('')

    if undated:
        lines.append(f'## ⚠️ OPEN WITHOUT DEADLINE ({len(undated)}) — '
                     f'add one or they never fire a packet')
        for e in undated:
            bar = str(e.get('threshold') or '—')
            lines.append(f"- `{e.get('id', '?')}` (owner: {e.get('owner', '?')}) "
                         f"— {bar[:120]}")
        lines.append('')

    if dones:
        lines.append(f'## ✅ DONE / REVERTED ({len(dones)})')
        lines.append(', '.join(str(e.get('id', '?')) for e in dones))
        lines.append('')

    def _ts(t):
        return (datetime.fromtimestamp(t, timezone.utc).isoformat(timespec='seconds')
                if t else 'never')

    lines.append('---')
    lines.append(f'freshness: {"STALE" if stale else "FRESH"} | '
                 f'registry mtime: {_ts(reg_mtime)} | '
                 f'prev tower render: {_ts(prev_tower_mtime)} | '
                 f'last run: {problems} packet(s), {entry_errors} entry error(s)')
    return '\n'.join(lines) + '\n'


def _render_control_tower(entries, now_iso, problems, entry_errors):
    """Build + atomically write the tower (tmp+replace, same as _save)."""
    try:
        prev = os.path.getmtime(CONTROL_TOWER)
    except OSError:
        prev = None
    try:
        reg_m = os.path.getmtime(REGISTRY)
    except OSError:
        reg_m = None
    text = _build_control_tower(entries, now_iso, problems, entry_errors,
                                prev_tower_mtime=prev, reg_mtime=reg_m)
    tmp = f'{CONTROL_TOWER}.{os.getpid()}.tmp'   # review MED-4: pid-unique path
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, CONTROL_TOWER)


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

    # control-tower wiring (CEO build 2026-10-31) — the #102 class: code
    # present but the registry names a typo'd/unknown key would silently
    # render no progress forever.
    bad_pe = [x.get('id') for x in reg.get('entries', [])
              if isinstance(x, dict) and x.get('status') == 'open'
              and x.get('progress_eval')
              and x.get('progress_eval') not in PROGRESS_EVALS]
    chk(not bad_pe, f'all open progress_eval keys known (bad={bad_pe})')
    chk(set(PROGRESS_EVALS) >= {'wider_sl', 'extended_time', 'contrarian_live'},
        'progress evals registered: wider_sl, extended_time, contrarian_live')
    chk('_tower' not in {x.get('id') for x in reg.get('entries', [])
                         if isinstance(x, dict)},
        "reserved state key '_tower' is not used as a registry id (review LOW-5)")
    m = _RE_TIME_EXT.search('  Extended: WR improvement = +4.9pp, trades = 17079')
    chk(m is not None and m.group(1) == '4.9' and m.group(2) == '17079',
        'extended-time parses POSITIVE improvement +4.9pp (bug_hunter NEW-1)')
    m = _RE_TIME_EXT.search('  Extended: WR improvement = -15.6pp, trades = 17079')
    chk(m is not None and m.group(1) == '-15.6',
        'extended-time still parses negative improvement')
    # tower builder smoke: pure function, no disk, no subprocess hooks
    try:
        txt = _build_control_tower(
            [x for x in reg.get('entries', []) if isinstance(x, dict)],
            NOW.isoformat(), 0, 0, prev_tower_mtime=NOW.timestamp(),
            reg_mtime=NOW.timestamp(), run_progress=False)
        chk('# CONTROL TOWER' in txt and '## 📅 CALENDAR' in txt
            and 'do not hand-edit' in txt.splitlines()[1],
            'tower builder produces header + calendar (selfcheck path)')
        chk('STALE' not in txt.splitlines()[2:5], 'fresh prev-mtime -> no STALE banner')
        txt_first = _build_control_tower(
            [x for x in reg.get('entries', []) if isinstance(x, dict)],
            NOW.isoformat(), 0, 0, prev_tower_mtime=None,
            reg_mtime=NOW.timestamp(), run_progress=False)
        chk('⚠️ **STALE**' not in txt_first,
            'first render (prev=None) -> no STALE banner (fresh by definition)')
        txt_stale = _build_control_tower(
            [x for x in reg.get('entries', []) if isinstance(x, dict)],
            NOW.isoformat(), 0, 0, prev_tower_mtime=NOW.timestamp() - 30 * 3600,
            reg_mtime=NOW.timestamp(), run_progress=False)
        chk('⚠️ **STALE**' in txt_stale, 'stale prev-mtime -> STALE banner in header')
    except Exception as ex:
        chk(False, f'tower builder raised: {type(ex).__name__}: {ex}')

    # auto-flip packet (CEO 20261108T230547Z AUTO-FLIP POLICY) — pure-function
    # fixtures first: met bar -> packet text naming the flag + one-line command;
    # every no-packet path (dedupe/non-open/bar-not-met/no-flag) and both
    # evaluator resolutions (auto_flip_check preferred, threshold_eval reuse).
    fx = {'id': 'fixture-autoflip', 'status': 'open',
          'auto_flip_flag': 'FIXTURE_ADMISSION_FLAG'}
    ln, sv = auto_flip_packet(fx, {}, NOW.isoformat(), True, 'fixture bar 3/3')
    chk(ln is not None and '[AUTO-FLIP-READY]' in ln
        and 'fixture-autoflip bar met' in ln
        and 'FIXTURE_ADMISSION_FLAG' in ln and 'one-line command' in ln,
        'auto-flip: met bar -> [AUTO-FLIP-READY] packet names flag + command')
    chk(sv == NOW.isoformat(), 'auto-flip: state value returned for dedupe')
    chk(auto_flip_packet(fx, {'auto_flip_fired': 'x'}, NOW.isoformat(),
                         True, 'd')[0] is None,
        'auto-flip: already fired -> no second packet (state dedupe)')
    chk(auto_flip_packet(dict(fx, status='done'), {}, NOW.isoformat(),
                         True, 'd')[0] is None,
        'auto-flip: non-open entry -> no packet')
    chk(auto_flip_packet(fx, {}, NOW.isoformat(), False, 'd')[0] is None,
        'auto-flip: bar not met -> no packet')
    chk(auto_flip_packet({'id': 'no-flag', 'status': 'open'}, {},
                         NOW.isoformat(), True, 'd')[0] is None,
        'auto-flip: no auto_flip_flag -> no packet (opt-in only)')
    b, d = auto_flip_bar({'id': 'no-eval'})
    chk(b is None and 'no evaluator' in d,
        'auto-flip: entry without evaluator -> bar unknowable, no packet')
    chk(auto_flip_bar({'id': 'bad-eval',
                       'auto_flip_check': 'no_such_eval'})[0] is None,
        'auto-flip: unknown evaluator -> bar unknowable, no packet')
    THRESHOLD_EVALS['_fixture_bar_met'] = lambda e: (True, 'fixture bar met')
    b, d = auto_flip_bar({'id': 'fx2', 'threshold_eval': '_fixture_bar_met',
                          'auto_flip_polarity': 'true=met'})
    chk(b is True and 'true=met' in d,
        'auto-flip: threshold_eval reuse + declared polarity -> bar MET')
    b, d = auto_flip_bar({'id': 'fx2b', 'threshold_eval': '_fixture_bar_met'})
    chk(b is None and 'polarity' in d,
        'auto-flip: BREACH-style threshold_eval WITHOUT polarity declaration '
        '-> bar unknowable (no inverted packet)')
    b, d = auto_flip_bar({'id': 'fx3', 'auto_flip_check': '_fixture_bar_met',
                          'threshold_eval': 'no_such_eval'})
    chk(b is True,
        'auto-flip: auto_flip_check preferred over a threshold_eval name')

    # preset pass-through: a raising evaluator must NOT run when the main
    # threshold section already resolved it (no duplicate Postgres reads)
    def _fixture_boom(e):
        raise RuntimeError('must not run — preset should short-circuit')

    THRESHOLD_EVALS['_fixture_boom'] = _fixture_boom
    b, d = auto_flip_bar({'id': 'fx4', 'threshold_eval': '_fixture_boom',
                          'auto_flip_polarity': 'true=met'},
                         preset=('_fixture_boom', True, 'preset bar met'))
    chk(b is True and 'preset bar met' in d and 'must not run' not in d,
        'auto-flip: preset short-circuits the evaluator (no double run)')
    THRESHOLD_EVALS.pop('_fixture_boom', None)
    THRESHOLD_EVALS.pop('_fixture_bar_met', None)

    # protected-flag denylist (code, not prose)
    chk(auto_flip_flag_blocked('WINNER_CELL_SIZE_MULT') is not None,
        'auto-flip: WINNER_CELL_SIZE_MULT refused (money-sizing)')
    chk(auto_flip_flag_blocked('PM_TRAIL_ACTIVATE_PCT') is not None,
        'auto-flip: PM_TRAIL_* refused (CEO-protected)')
    chk(auto_flip_flag_blocked('FOO_MULT_ENABLED') is not None,
        'auto-flip: *_MULT flag refused (mult change)')
    chk(auto_flip_flag_blocked('some lowercase') is not None,
        'auto-flip: non-flag-name string refused')
    chk(auto_flip_flag_blocked('LINREG_FADE_STORM_SHADOW') is None,
        'auto-flip: ordinary gate flag NOT blocked (opt-in stays possible)')
    chk(auto_flip_packet(dict(fx, auto_flip_flag='WINNER_CELL_SIZE_MULT'),
                         {}, NOW.isoformat(), True, 'd')[0] is None,
        'auto-flip: protected flag cannot reach a packet (defense in depth)')

    reg_af = [x.get('id') for x in reg.get('entries', [])
              if isinstance(x, dict) and x.get('auto_flip_flag')]
    chk(not reg_af,
        f'no registry entry carries auto_flip_flag yet (opt-in; found={reg_af})')

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
