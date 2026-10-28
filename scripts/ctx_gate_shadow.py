#!/usr/bin/env python3
"""
ctx_gate_shadow.py — Counterfactual tracker for the context-gate rules conversion.

CEO 2026-10-27 item 4, per the automatic-implementation skill (Phase 2/4).
The deterministic rules (decider_run._ctx_rules_shadow) run BESIDE the LLM in
shadow mode and never touch the live decision. This script reads the agreement
rows they write and produces the enforce/relax/reject recommendation.

The LLM's real job is NAYing trades the rule gate passed (75 NAY / 5 WARN / 0 GO
all-time). The question the shadow answers: does a deterministic port reproduce
the LLM's NAY-vs-not decision closely enough to remove the subprocess from the
trade hot-path?

Decision rules (skill Phase 4):
  agreement >= 90% and n >= 15   -> PROPOSE ENFORCE (rules safe to take over)
  agreement 75-89% and n >= 15   -> MONITOR (extend shadow, inspect disagreements)
  agreement < 75% and n >= 15    -> REJECT / rework rules (too many divergences)
  n < 15                         -> INSUFFICIENT DATA (extend shadow)

Modes:
  --report        aggregate + recommendation (default)
  --disagreements print the disagreeing rows (what to inspect)
  --since-hours N restrict to last N hours

Usage: python3 scripts/ctx_gate_shadow.py [--report] [--disagreements] [--since-hours 168]
"""
import os
import sys
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SHADOW_DB = '/root/.hermes/brain/ctx_gate_shadow.db'
MIN_N = 15          # sample-size floor before any recommendation
ENFORCE_BAR = 0.90  # agreement >= this -> propose enforce
MONITOR_BAR = 0.75  # agreement >= this (but < ENFORCE_BAR) -> monitor


def log(msg):
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] [ctx_gate_shadow] {msg}', flush=True)


def _rows(since_hours=None):
    if not os.path.exists(SHADOW_DB):
        return []
    conn = sqlite3.connect(SHADOW_DB)
    try:
        c = conn.cursor()
        # tolerate a missing llm_verdict column (older schema) gracefully
        cols = [r[1] for r in c.execute("PRAGMA table_info(shadow_events)").fetchall()]
        if 'llm_verdict' not in cols:
            return []
        q = "SELECT ts, token, direction, source, rules_verdict, llm_verdict, agree FROM shadow_events"
        args = []
        if since_hours:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
            q += " WHERE ts >= ?"
            args.append(cutoff)
        q += " ORDER BY id DESC"
        return c.execute(q, args).fetchall()
    finally:
        conn.close()


def report(since_hours=None):
    rows = _rows(since_hours)
    if not rows:
        log('no shadow rows yet — shadow not collecting (is CONTEXT_GATE_RULES_SHADOW on, and has the pipeline run?)')
        return

    # NULL agree = LLM hard-failed (SKIP). Not a real verdict on either side —
    # exclude from the agreement ratio or it inflates agreement (review #7).
    scored = [r for r in rows if r[6] is not None]
    skipped = len(rows) - len(scored)
    n = len(scored)
    if n == 0:
        log(f'{len(rows)} rows but all are SKIP (LLM fail-closed) — no verdicts to score yet')
        return

    agree = sum(1 for r in scored if r[6] == 1)
    rate = agree / n if n else 0.0

    # Verdict distribution both sides
    rules_dist = {}
    llm_dist = {}
    for r in rows:
        rules_dist[r[4]] = rules_dist.get(r[4], 0) + 1
        llm_dist[r[5]] = llm_dist.get(r[5], 0) + 1

    log('─── CTX-GATE RULES SHADOW REPORT ───')
    log(f'n={n} scored  agreement={rate*100:.1f}% ({agree}/{n})' + (f'  [{skipped} SKIP rows excluded]' if skipped else ''))
    log(f'rules verdicts: {rules_dist}')
    log(f'LLM verdicts:   {llm_dist}')

    # The decision that matters: does rules-NAY match LLM-NAY?
    both_nay = sum(1 for r in scored if r[4] == 'NAY' and r[5] == 'NAY')
    llm_nay = sum(1 for r in scored if r[5] == 'NAY')
    rules_nay = sum(1 for r in scored if r[4] == 'NAY')
    log(f'NAY agreement: LLM NAY {llm_nay}, rules NAY {rules_nay}, both {both_nay}')

    if n < MIN_N:
        log(f'← INSUFFICIENT DATA (n={n} < {MIN_N}) — extend shadow (need >=7 days)')
    elif rate >= ENFORCE_BAR:
        log(f'← PROPOSE ENFORCE (agreement {rate*100:.1f}% >= {ENFORCE_BAR*100:.0f}%, n>=15)')
        log('  Next: CEO decision to flip CONTEXT_GATE_RULES_SHADOW=False. Requires explicit sign-off.')
    elif rate >= MONITOR_BAR:
        log(f'← MONITOR (agreement {rate*100:.1f}% in {MONITOR_BAR*100:.0f}-{ENFORCE_BAR*100:.0f}%) — inspect disagreements, extend shadow')
    else:
        log(f'← REJECT / REWORK (agreement {rate*100:.1f}% < {MONITOR_BAR*100:.0f}%) — rules diverge too often; do NOT enforce')


def disagreements(since_hours=None):
    rows = _rows(since_hours)
    dis = [r for r in rows if r[6] == 0]
    if not dis:
        log('no disagreements recorded')
        return
    log(f'─── {len(dis)} DISAGREEMENTS ───')
    for ts, token, direction, source, rv, lv, _ in dis[:50]:
        log(f'{ts[:19]} {token} {direction} [{source}]: rules={rv} vs LLM={lv}')
    if len(dis) > 50:
        log(f'... and {len(dis)-50} more')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--disagreements', action='store_true')
    ap.add_argument('--since-hours', type=int, default=None)
    args = ap.parse_args()
    run_all = not (args.report or args.disagreements)
    if run_all or args.report:
        report(args.since_hours)
    if args.disagreements:
        disagreements(args.since_hours)
    return 0


if __name__ == '__main__':
    sys.exit(main())
