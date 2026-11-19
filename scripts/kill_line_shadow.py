#!/usr/bin/env python3
"""
kill_line_shadow.py — per-signal-source kill-line shadow monitor (LOG-ONLY).

CEO deep run 20261108T023937Z item I (pre-authorized, OAK-SHADOW), built by D5
for run 20261119T141548Z. automatic-implementation Phase 1: compute + log ONLY.
This script does NOT import decider/signals/position_manager/hermes_constants,
does NOT write to any DB (SELECT only), and has ZERO trading-path effect —
no auto-disable, no blocking, fail-open (exit 0 on any error).

KILL LINE (pre-registered, decision 20261108T023937Z row I):
    line = 2.0 x worst CUMULATIVE-PnL DRAWDOWN of the source during the TRAIN
    baseline (first 60d of a 90d realized window; last 30d = validate split,
    same data-anchored split as scripts/streak_analysis.py).

    PROVENANCE CAVEAT (read before trusting any number): there is NO per-source
    backtested drawdown in this repo — only realized trade history (PostgreSQL
    brain `trades`). Every line here is a REALIZED drawdown, not a tested one,
    and is therefore PROVISIONAL until a backtest baseline exists. A historical
    max is never a hard bound (Wallace mining rule — the next drawdown may be
    deeper than anything seen).

Modes:
    (default)  monitor: current DD per registry source vs its line, distance
               logged to data/kill_line_shadow.jsonl every run, ALERT line at
               >=80% of line consumed (the pre-registered "shadow logs
               approach always" limb), CROSS at >=100% reported log-only.
    --derive   rebuild brain/kill_line_registry.json from the realized baseline
    --selfcheck assert-based math check, no DB (exit 1 on failure)

PRE-REGISTERED ENFORCE LIMB (never runs in this script, never unattended):
    auto-disable of a source ONLY on (a) actual line CROSS, AND (b) negative
    PnL over that source's next 10 closed trades, AND (c) explicit CEO
    approval. Review auto-surfaces 2026-12-03 via data/checkpoint_registry.json
    + data/shadow_disposition.json (deadline default = KEEP SHADOW log-only).

TUNING VALUES (analysis/monitor params — deliberately in this header as CLI
defaults, NOT hermes_constants: the CEO decision authorized "standalone
scripts + systemd timers, no constants edit at all", and importing
hermes_constants would drag trading code into a shadow-only monitor):
    KILL_LINE_MULT   = 2.0   pre-reg: 2x worst baseline DD (decision row I)
    ALERT_PCT        = 0.80  pre-reg: approach limb = 80% of line consumed
    DEFAULT_DAYS     = 90    baseline lookback (streak_analysis parity)
    DEFAULT_TRAIN_DAYS = 60  first 60d train derive / last 30d validate
    DEFAULT_WINDOW_DAYS = 30 current-DD measurement window (validate-span scale)
    MIN_TRAIN_N      = 10    no line below this many train trades (thin-source
                             floor; freq_deviation_shadow MIN_BASELINE_N parity)

Usage:
    python3 scripts/kill_line_shadow.py                  # monitor run
    python3 scripts/kill_line_shadow.py --window-days 7  # shorter window
    python3 scripts/kill_line_shadow.py --derive         # refresh registry
    python3 scripts/kill_line_shadow.py --selfcheck      # math check
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import psycopg2
    from _secrets import BRAIN_DB_DICT
    from paths import HERMES_DATA
except Exception as e:
    # fail-open covers import time too — a missing dep must not fail the timer
    # (result-4 bug_hunter finding on freq_deviation_shadow: module-level
    # imports outside the handler crashed the unit; keep them inside)
    print(f'[KL-SHADOW] ERROR import failed: {type(e).__name__}: {e}', flush=True)
    sys.exit(0)

PREFIX = '[KL-SHADOW]'

# ── pre-registered / tuning constants (see module docstring) ────────────────
KILL_LINE_MULT = 2.0        # CEO 20261108T023937Z row I: line = 2x worst DD
ALERT_PCT = 0.80            # pre-reg: alert when >=80% of line consumed
CROSS_PCT = 1.00            # report CROSS at >=100% consumed (log-only ever)
DEFAULT_DAYS = 90           # derive window (streak_analysis parity)
DEFAULT_TRAIN_DAYS = 60     # train = first 60d, validate = last 30d
DEFAULT_WINDOW_DAYS = 30    # monitor: current-DD trailing window
MIN_TRAIN_N = 10            # thin-source floor for having a line at all
ALERT_DEDUP_HOURS = 24      # one error_alerts.md entry per source / 24h

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, 'brain', 'kill_line_registry.json')
STATE_FILE = os.path.join(HERMES_DATA, 'kill_line_shadow.jsonl')
ERROR_ALERTS = '/root/.hermes/automation/error_alerts.md'

# Exact query, printed on every run for reproducibility (n = params[0]).
SQL = (
    "SELECT close_time, signal, pnl_usdt "
    "FROM trades "
    "WHERE status = 'closed' "
    "  AND close_time > NOW() - make_interval(days => %s) "
    "ORDER BY close_time ASC"
)


def log(msg):
    print(f'{PREFIX} {msg}', flush=True)


def fetch_trades(days: int) -> list:
    """Read-only: (close_time, source, pnl_usdt) rows in the trailing window.

    SELECT only; cursor and connection closed in finally (repo convention).
    NULL pnl_usdt counts as 0.0 contribution (no drawdown effect).
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**BRAIN_DB_DICT)
        cur = conn.cursor()
        cur.execute(SQL, (days,))
        rows = []
        for close_time, signal, pnl in cur.fetchall():
            source = (signal or '').strip() or '(none)'
            rows.append((close_time, source, float(pnl) if pnl is not None else 0.0))
        return rows
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


def max_drawdown(pnls) -> float:
    """Peak-to-trough max drawdown of the running cumulative sum (>= 0)."""
    cum = peak = dd = 0.0
    for p in pnls:
        cum += p
        if cum > peak:
            peak = cum
        if peak - cum > dd:
            dd = peak - cum
    return dd


def by_source(rows) -> dict:
    """Group (close_time, source, pnl) into source -> [pnl] (input is time-sorted)."""
    out = defaultdict(list)
    for _ct, source, pnl in rows:
        out[source].append(pnl)
    return out


# ── derive mode ─────────────────────────────────────────────────────────────
def derive(days: int, train_days: int) -> None:
    rows = fetch_trades(days)
    if not rows:
        log('derive: no trades in window — registry unchanged')
        return
    anchor = rows[-1][0]                       # data-anchored, not wall clock
    split_dt = anchor - timedelta(days=days - train_days)

    grouped = defaultdict(list)
    for close_time, source, pnl in rows:
        grouped[source].append((close_time, pnl))

    sources, skipped = {}, {}
    for source, seq in sorted(grouped.items()):
        train = [p for ct, p in seq if ct <= split_dt]
        val = [p for ct, p in seq if ct > split_dt]
        if len(train) < MIN_TRAIN_N:
            skipped[source] = f'n_train={len(train)} < {MIN_TRAIN_N} (thin — no line)'
            continue
        dd_train = max_drawdown(train)
        sources[source] = {
            'line_usdt': round(KILL_LINE_MULT * dd_train, 4),
            'train_max_dd_usdt': round(dd_train, 4),
            'n_train': len(train),
            'val_max_dd_usdt': round(max_drawdown(val), 4),
            'n_val': len(val),
            'provisional': True,   # realized, not backtested — see brain/kill_lines.md
        }

    reg = {
        '_doc': ('Pre-committed kill lines, one per signal source. line = '
                 f'{KILL_LINE_MULT}x worst train-baseline realized cumulative-PnL '
                 'drawdown. REALIZED not backtested — PROVISIONAL until a '
                 'backtest baseline exists; historical max is never a hard bound. '
                 'Human-readable provenance: brain/kill_lines.md. '
                 'Refresh: python3 scripts/kill_line_shadow.py --derive'),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'sql': ' '.join(SQL.split()),
        'params': {'days': days, 'train_days': train_days,
                   'min_train_n': MIN_TRAIN_N, 'multiplier': KILL_LINE_MULT},
        'window': {'anchor_close_time': str(anchor),
                   'train_cutoff': str(split_dt),
                   'train_days': train_days, 'validate_days': days - train_days},
        'provenance': ('realized (PostgreSQL brain trades, status=closed) — '
                       'NOT a tested/backtest baseline'),
        'sources': sources,
        'skipped': skipped,
    }
    os.makedirs(os.path.dirname(REGISTRY), exist_ok=True)
    tmp = REGISTRY + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(reg, f, indent=1, sort_keys=True)
        f.write('\n')
    os.replace(tmp, REGISTRY)

    log(f'derive: window={days}d train={train_days}d '
        f'anchor={anchor} split={split_dt} n_trades={len(rows)}')
    log(f'derive: {len(sources)} line(s) written, {len(skipped)} skipped (thin)')
    for source, s in sorted(sources.items()):
        log(f'derive LINE source={source} train_dd={s["train_max_dd_usdt"]} '
            f'line={s["line_usdt"]} n_train={s["n_train"]} val_dd={s["val_max_dd_usdt"]}')
    for source, why in sorted(skipped.items()):
        log(f'derive SKIP source={source} {why}')
    print_sql(days)


def print_sql(n_days: int) -> None:
    log(f'SQL: {" ".join(SQL.split())}')
    log(f'params: ({n_days},)   window: trailing {n_days}d, status=closed, '
        f'ordered by close_time ASC')


# ── monitor mode ────────────────────────────────────────────────────────────
def load_registry() -> dict:
    with open(REGISTRY) as f:
        return json.load(f)


def load_recent_alerts(hours) -> list:
    if not os.path.exists(STATE_FILE):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    try:
        with open(STATE_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if not ev.get('alert'):
                        continue
                    ts = datetime.fromisoformat(ev['ts'])
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        recent.append(ev)
                except (ValueError, KeyError):
                    continue
    except OSError:
        return []
    return recent


def append_state(ev: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'a') as f:
        f.write(json.dumps(ev) + '\n')


def append_error_alert(source: str, msg: str) -> bool:
    """auditor_verify.py convention: '## Error Alerts — <ts>' + bullet."""
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    try:
        with open(ERROR_ALERTS, 'a') as f:
            f.write(f'\n## Error Alerts — {ts}\n')
            f.write(f'- **[WARN]** (kill_line_shadow): `{source}`: {msg}\n')
        return True
    except OSError:
        return False


def status_of(pct: float) -> str:
    if pct >= CROSS_PCT:
        return 'CROSS'
    if pct >= ALERT_PCT:
        return 'APPROACH'
    return 'OK'


def monitor(window_days: int) -> None:
    reg = load_registry()
    reg_sources = reg.get('sources', {})
    if not reg_sources:
        log('registry has no sources — run --derive first')
        return

    rows = fetch_trades(window_days)
    if not rows:
        # bug_hunter F1: DB-up-but-0-rows must not read as an all-clear —
        # empty result is a data/query failure, never "everything healthy"
        log(f'ERROR fetch_trades returned 0 rows (window={window_days}d) — '
            'NOT an all-clear: table missing/renamed or query failure. '
            'Investigate DB before trusting next run.')
        return
    groups = by_source(rows)
    cur_dd = {s: max_drawdown(p) for s, p in groups.items()}
    recent_alerts = load_recent_alerts(ALERT_DEDUP_HOURS)

    n_approach = n_cross = 0
    for source in sorted(reg_sources):
        line = float(reg_sources[source].get('line_usdt', 0.0) or 0.0)
        dd = cur_dd.get(source, 0.0)
        n = len(groups.get(source, ()))
        if line <= 0:
            # line == 0 means the train baseline had no drawdown — nothing to
            # consume; log and skip the ratio (division guard, never a crash)
            log(f'source={source} dd={dd:.4f} line=0.0 status=NO-LINE '
                f'(re-derive needed) n={n}')
            continue
        pct = dd / line
        status = status_of(pct)
        if status == 'CROSS':
            n_cross += 1
        elif status == 'APPROACH':
            n_approach += 1

        ev = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'source': source,
            'window_days': window_days,
            'n_window': n,
            'current_dd_usdt': round(dd, 4),
            'line_usdt': line,
            'pct_consumed': round(pct, 4),
            'status': status,
            'alert': status in ('APPROACH', 'CROSS'),
            'provisional': bool(reg_sources[source].get('provisional', True)),
        }
        append_state(ev)
        log(f'source={source} dd={dd:.4f} line={line:.4f} '
            f'consumed={pct:.1%} n_window={n} status={status}')

        if ev['alert']:
            msg = (f'KILL LINE {status} source={source} consumed={pct:.1%} of line '
                   f'(dd={dd:.4f} line={line:.4f}, window={window_days}d, n={n}) — '
                   'SHADOW log-only, no disable; enforce needs line CROSS + '
                   'next-10-trade negative PnL + explicit CEO approval')
            log(f'ALERT {msg}')
            dedup = any(a.get('source') == source for a in recent_alerts)
            if not dedup:
                wrote = append_error_alert(source, msg)
                log(f'error_alerts.md {"appended" if wrote else "write FAILED"} '
                    f'(source={source})')

    unreg = sorted(s for s in cur_dd if s not in reg_sources)
    if unreg:
        log(f'{len(unreg)} unregistered source(s) traded in window (no line): '
            + ', '.join(unreg))
    log(f'checked {len(reg_sources)} registered source(s) '
        f'(window={window_days}d, trades={len(rows)}), '
        f'{n_approach} APPROACH, {n_cross} CROSS, {len(unreg)} unregistered — '
        'LOG-ONLY, nothing disabled')
    print_sql(window_days)


# ── selfcheck ───────────────────────────────────────────────────────────────
def selfcheck() -> None:
    # max_drawdown: the only nontrivial math in this script
    assert max_drawdown([1.0, -2.0, 3.0]) == 2.0, 'dd mixed'
    assert max_drawdown([5.0, 5.0, 5.0]) == 0.0, 'dd no-drawdown'
    assert max_drawdown([-1.0, -1.0]) == 2.0, 'dd from-zero peak'
    assert max_drawdown([]) == 0.0, 'dd empty'
    assert max_drawdown([0.0]) == 0.0, 'dd zero trade'
    # pre-registered limbs
    assert KILL_LINE_MULT * 2.0 == 4.0, 'line multiplier'
    assert status_of(0.7999) == 'OK', 'below 80pct'
    assert status_of(0.80) == 'APPROACH', 'approach boundary inclusive'
    assert status_of(1.0) == 'CROSS', 'cross boundary inclusive'
    assert status_of(1.5) == 'CROSS', 'over line'
    log('selfcheck PASS (10 asserts)')


def main():
    p = argparse.ArgumentParser(
        description='Kill-line shadow monitor (log-only; SELECT-only; fail-open)')
    p.add_argument('--derive', action='store_true',
                   help='rebuild brain/kill_line_registry.json from the realized baseline')
    p.add_argument('--selfcheck', action='store_true',
                   help='run assert-based math checks (no DB) and exit')
    p.add_argument('--days', type=int, default=DEFAULT_DAYS,
                   help=f'--derive baseline lookback in days (default {DEFAULT_DAYS})')
    p.add_argument('--train-days', type=int, default=DEFAULT_TRAIN_DAYS,
                   help=f'--derive train span in days (default {DEFAULT_TRAIN_DAYS})')
    p.add_argument('--window-days', type=int, default=DEFAULT_WINDOW_DAYS,
                   help=f'monitor current-DD window in days (default {DEFAULT_WINDOW_DAYS})')
    args = p.parse_args()

    if args.selfcheck:
        selfcheck()
    elif args.derive:
        derive(args.days, args.train_days)
    else:
        monitor(args.window_days)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'{PREFIX} ERROR {type(e).__name__}: {e}', flush=True)
        # fail-open exit 0 for the timer path (freq parity); --selfcheck keeps
        # a real exit code so its asserts can gate anything
        sys.exit(1 if '--selfcheck' in sys.argv else 0)
