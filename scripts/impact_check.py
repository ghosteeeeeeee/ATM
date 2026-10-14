#!/usr/bin/env python3
"""Impact-checker: verify brain_auditor (and other) config changes actually worked.

Reads brain/changes_log.json, queries brain Postgres for the affected signal's
post-change cohort vs pre-change baseline, prints PASS/FAIL/THIN per change.

Usage:
    python3 scripts/impact_check.py            # changes from last 7d
    python3 scripts/impact_check.py --days 14  # wider window
    python3 scripts/impact_check.py --agent brain_auditor
"""
import json, os, sys, re
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import *  # noqa

import psycopg2


def extract_signal(change_text, file_name):
    """Best-effort signal name from change text/file. ponytail: heuristic, not perfect."""
    text = (change_text or "") + " " + (file_name or "")
    m = re.search(r'\b([a-z0-9]+(?:[-_][a-z0-9]+)+[+-]?)\b', text.lower())
    known = re.findall(
        r'\b(pump-chain[-_]?v?[0-9]*[+-]?|bb-squeeze\+?|bb-bounce-v[23]-long\+?|'
        r'volume-breakout-long\+?|volume-buildup[+-]?|volume-breakout-short-|'
        r'ai-trader\+?|oversold-bounce\+?|doji-bottom-long|hmacd_mtf[-+]*|'
        r'r2v2-long[0-9]|r2-trend-long[0-9]|trend-ride\+?|accel-300-?|'
        r'continuum[-a-z]*[+-]?)\b', text.lower())
    if known:
        return known[0]
    return m.group(1) if m else None


def cohort_stats(cur, signal, since_ts, direction=None):
    """Post-change trades for signal since timestamp."""
    sql = """
        SELECT COUNT(*), COALESCE(ROUND(SUM(pnl_usdt),2),0),
               ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1)
        FROM trades
        WHERE status='closed' AND signal LIKE %s AND open_time >= %s
    """
    params = [f"%{signal}%", since_ts]
    if direction:
        sql += " AND direction=%s"
        params.append(direction)
    cur.execute(sql, params)
    return cur.fetchone()


def baseline_stats(cur, signal, since_ts, until_ts, direction=None):
    sql = """
        SELECT COUNT(*), COALESCE(ROUND(SUM(pnl_usdt),2),0),
               ROUND(100.0*SUM(CASE WHEN pnl_usdt > 0 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),1)
        FROM trades
        WHERE status='closed' AND signal LIKE %s AND open_time >= %s AND open_time < %s
    """
    params = [f"%{signal}%", since_ts, until_ts]
    if direction:
        sql += " AND direction=%s"
        params.append(direction)
    cur.execute(sql, params)
    return cur.fetchone()


def main():
    days = 7
    agent = None
    for i, a in enumerate(sys.argv):
        if a == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
        if a == "--agent" and i + 1 < len(sys.argv):
            agent = sys.argv[i + 1]

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    changes_path = os.path.join(repo_root, "brain", "changes_log.json")
    if not os.path.exists(changes_path):
        print("no changes_log.json")
        return
    changes = json.load(open(changes_path))

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()

    print(f"=== impact check: changes since {cutoff} (agent={agent or 'all'}) ===")
    for c in changes:
        if c.get("timestamp", "") < cutoff:
            continue
        if agent and c.get("agent") != agent:
            continue
        ctype = c.get("type", "")
        if ctype in ("report",):
            continue
        signal = extract_signal(c.get("change", ""), c.get("file", ""))
        direction = None
        ctxt = (c.get("change", "") + " " + c.get("file", "")).upper()
        if "LONG" in ctxt and "SHORT" not in ctxt:
            direction = "LONG"
        elif "SHORT" in ctxt and "LONG" not in ctxt:
            direction = "SHORT"
        if not signal:
            print(f"[{c['timestamp'][:16]}] {ctype}: {c.get('change','')[:70]} — SKIP (no signal parsed)")
            continue
        ts = c.get("timestamp", "").replace("T", " ")[:19]
        post = cohort_stats(cur, signal, ts)
        base = baseline_stats(cur, signal, (now - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"), ts)
        n, pnl, wr = post
        bn, bpnl, bwr = base
        verdict = "THIN" if n < 5 else ("PASS" if (pnl or 0) >= 0 else "FAIL")
        print(
            f"[{c['timestamp'][:16]}] {ctype} {signal}: "
            f"post {n}T {wr}% {pnl:+}$ | pre14d {bn}T {bwr}% {bpnl:+}$ → {verdict}"
        )

    conn.close()


if __name__ == "__main__":
    main()
