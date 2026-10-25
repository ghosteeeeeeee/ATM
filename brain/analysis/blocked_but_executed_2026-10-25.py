#!/usr/bin/env python3
"""BLOCKED-but-EXECUTED cohort — CONTINUUM-BLOCK toothless at the confluence gate.

brain_auditor #138 (2026-10-25). Root cause: signal_compactor Layer B sets
_btc_mom_ok_for_bypass=False and logs "[CONTINUUM-BLOCK] ... BLOCKED", but that
flag only gates the LONG/SHORT-NEUTRAL blocks (signal_compactor:2949/3040/3067).
The CONFLUENCE gate's "backtested standalone" pass path (3455-3495) and the
HOTSET-FINAL / PENDING-APPROVE / SAFETY-FILTER standalone bypasses never read it,
so bb-bounce-v2-long+ and friends execute in the same cycle the block printed.

Measured cohort = blocks whose token+direction produced an EXEC within 180s.

PRE-REGISTERED enforcement criteria (locked before running this script):
  - cohort n >= 20
  - net pnl_usdt > 0 saved (i.e. cohort net < 0)
  - fkA (cohort winners / direction-filtered winners closed in the same 14d window — code matches this wording) < 20%
  - both 15d/period split halves net-negative (no single-period carry)
  - binomial p vs base WR < 0.05 (cohort WR worse than window base WR)
  Ship = enforce _btc_mom_ok_for_bypass at the confluence standalone pass.
  Any fail = COLLECT, no enforcement, criteria closed.
"""
import re
import sys
import datetime
import psycopg2

LOG = "/root/.hermes/logs/pipeline.log"
WIN = "14 days"
EXEC_SLACK_S = 65   # one pipeline cycle — 180s spanned ~3 cycles and admitted stale-pair matches (bug-hunter #138)

pat_block = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[(?:CONTINUUM-BLOCK|CONTINUUM-BULL)\] (\S+) (LONG|SHORT) BLOCKED")
pat_exec = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+EXEC: (\S+) (LONG|SHORT) @")


def parse_log(path=LOG):
    blocks, execs = [], []
    with open(path, errors="ignore") as f:
        for line in f:
            m = pat_block.match(line)
            if m:
                blocks.append((m.group(1), m.group(2), m.group(3)))
                continue
            m = pat_exec.match(line)
            if m:
                execs.append((m.group(1), m.group(2), m.group(3)))
    return blocks, execs


def ts(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def match_pairs(blocks, execs, slack=EXEC_SLACK_S):
    used, pairs = set(), []
    for bts, tok, d in blocks:
        b = ts(bts)
        for i, (ets, etok, ed) in enumerate(execs):
            if i in used or etok != tok or ed != d:
                continue
            e = ts(ets)
            if b <= e <= b + datetime.timedelta(seconds=slack):
                pairs.append((bts, ets, tok, d))
                used.add(i)
                break
    return pairs


def join_trades(pairs):
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    out = []
    for bts, ets, tok, d in pairs:
        e = ts(ets)
        cur.execute(
            """SELECT id, signal, pnl_usdt, status, open_time
               FROM trades WHERE token=%s AND direction=%s AND open_time BETWEEN %s AND %s
               ORDER BY ABS(EXTRACT(EPOCH FROM (open_time - %s))) LIMIT 1""",
            (tok, d, e - datetime.timedelta(seconds=30),
             e + datetime.timedelta(seconds=180), e))
        row = cur.fetchone()
        if row and row[3] == "closed":
            out.append({"block": bts, "exec": ets, "token": tok, "dir": d,
                        "id": row[0], "signal": row[1], "pnl": float(row[2])})
    conn.close()
    return out


def binom_p(k, n, p0):
    """One-sided P(X <= k) under Binomial(n, p0) — cohort WR worse than base."""
    from math import comb
    return sum(comb(n, i) * p0**i * (1 - p0)**(n - i) for i in range(k + 1))


def report(cohort, direction='LONG'):
    if not cohort:
        print("no cohort"); return
    n = len(cohort)
    w = [c for c in cohort if c["pnl"] > 0]
    net = sum(c["pnl"] for c in cohort)
    wr = 100.0 * len(w) / n
    t0 = ts(min(c["exec"] for c in cohort))
    t1 = ts(max(c["exec"] for c in cohort))
    by_t = sorted(cohort, key=lambda c: c["exec"])   # rank split — wall-clock mid skewed to n:7
    half1, half2 = by_t[:max(1, n // 2)], by_t[max(1, n // 2):]

    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute(f"""SELECT COUNT(*) FILTER (WHERE pnl_usdt > 0), COUNT(*)
                    FROM trades WHERE status='closed' AND direction=%s
                      AND close_time > NOW() - INTERVAL '{WIN}'""", (direction,))
    base_w, base_n = cur.fetchone()
    conn.close()
    base_wr = (base_w / base_n) if base_n else 0.5

    p = binom_p(len(w), n, base_wr)
    print(f"cohort n={n}  {len(w)}W/{n - len(w)}L  WR {wr:.1f}%  net {net:+.2f}")
    print(f"period {t0} .. {t1}")
    print(f"half1 n={len(half1)} net {sum(c['pnl'] for c in half1):+.2f} | "
          f"half2 n={len(half2)} net {sum(c['pnl'] for c in half2):+.2f}")
    print(f"base {WIN}: {base_w}/{base_n} = {100 * base_wr:.1f}%  cohort-vs-base binom p={p:.4f}")
    fka = (100.0 * len(w) / base_w) if base_w else 999.0
    fkb = 100.0 * len(w) / n
    print(f"fkA (cohort winners / base winners {WIN}) = {len(w)}/{base_w} = {fka:.1f}%")
    print(f"fkB (cohort winners / cohort trades)     = {fkb:.1f}%")
    print("criteria: n>=20 | net<0 | fkA<20% | both halves net<0 | p<0.05")
    ok = (n >= 20 and net < 0 and fka < 20 and bool(half1) and bool(half2)
          and all(sum(c['pnl'] for c in h) < 0 for h in (half1, half2)) and p < 0.05)
    print("VERDICT:", "PASS — enforcement may ship" if ok else "FAIL — COLLECT, no ship")
    from collections import Counter
    print("by signal:", Counter(c["signal"] for c in cohort).most_common())
    print("by dir:", Counter(c["dir"] for c in cohort))


def selfcheck():
    b = [("2026-10-25 07:15:00", "SAGA", "LONG"), ("2026-10-25 07:16:00", "SAGA", "LONG"),
         ("2026-10-20 10:00:00", "AAA", "LONG")]
    e = [("2026-10-25 07:15:18", "SAGA", "LONG"), ("2026-10-25 08:00:00", "SAGA", "LONG"),
         ("2026-10-20 10:02:00", "AAA", "LONG"), ("2026-10-21 11:00:00", "BBB", "LONG")]
    pairs = match_pairs(b, e, slack=180)
    assert len(pairs) == 2, pairs          # SAGA 07:15 + AAA; SAGA 07:16 unmatched
    assert pairs[0][2] == "SAGA" and pairs[1][2] == "AAA"
    assert binom_p(5, 42, 0.44) < 0.5 < binom_p(30, 42, 0.44)
    r = re.compile(r"x")
    assert pat_block.match("2026-10-25 07:15:00   🚫 [CONTINUUM-BLOCK] SAGA LONG BLOCKED — BTC bearish structure")
    assert pat_block.match("2026-10-25 07:15:00   🚫 [CONTINUUM-BULL] KAA SHORT BLOCKED — x")
    assert pat_exec.match("2026-10-25 07:15:18 EXEC: SAGA LONG @ $0.017820 conf=61%")
    print("selfcheck PASS")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
        sys.exit(0)
    blocks, execs = parse_log()
    pairs = match_pairs(blocks, execs)
    print(f"blocks={len(blocks)} execs={len(execs)} blocked-yet-executed={len(pairs)}")
    cohort = join_trades(pairs)
    print(f"matched closed trades={len(cohort)}")
    short_c = [c for c in cohort if c["dir"] == "SHORT"]
    if short_c:
        print(f"-- SHORT side (informational, n={len(short_c)}) --")
        report(short_c, "SHORT")
        print()
    print("-- LONG side (the enforcement verdict) --")
    report([c for c in cohort if c["dir"] == "LONG"])
