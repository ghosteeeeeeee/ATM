#!/usr/bin/env python3
"""goal_metrics_check.py — the goal-704ed65e verifier. Run every goal round.

RESTRUCTURED metrics 2026-11-22 (CEO verdict 20261122T194418Z + T approval 2026-11-22):
expectancy set replaces the WR target — "we want net positive". WR is diagnostic only.
Target source: CEO edge-diagnosis verdict 20261122T194418Z + registry goal-metric-restructure.
All numbers from PG (source of truth); fees = synthetic 0.09% RT of amount_usdt (BUG-073/099).

FORMAL KPI LAYERS (CEO verdict 20261122T221140Z "APPROVE WITH MODIFICATIONS — existing
surfaces only"; registry kpi-framework-formal):
  Tier H  = the 9 gates below + the WR info line = the FROZEN 10 (T approved 11-22,
            unchanged — no relitigation). Reported as the health pass-count x/10.
  Tier N  = NS1 (same number as the net $/trade gate) + NS2 (gated here; was the
            book-30d info line).
  Tier R  = R1 30d max drawdown of the DAILY cumulative fee-net curve, vs equity.
  --kanban appends FAIL lines to automation/ceo/ceo_kanban.md (shadow_disposition
  packet shape). Passive-display metrics never alert. WR never gates.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

import psycopg2

FEE = 0.0009

# Verdict 20261122T221140Z targets (frozen; registry kpi-framework-formal)
NS2_TARGET = -2.00        # rolling 30d fee-net, >=
R1_TARGET_PCT = -50.0     # 30d max DD as % of current equity, >=
EQUITY_FLOOR = 10.0       # below this -> CRITICAL + kill-switch rec to T
TIER_H_CONSEC_ALERT = 2   # Tier-H gate FAILing >=2 consecutive runs -> kanban

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          '.goal_metrics_state.json')
KANBAN = '/root/.hermes/automation/ceo/ceo_kanban.md'
NS1_LABEL_KEY = 'net $/trade 7d'   # the Tier-H gate that IS NS1 (kanban dedupe key)


def _equity():
    """Current account equity via the EXISTING clearinghouse read
    (hyperliquid_exchange.get_account_value_curl — the same reader trade_watchdog's
    D3 heat gate and the MoE $15.51 read use). Live read-only /info call, ~0.7s.
    None = the READ FAILED (callers degrade to dollar-DD instead of inventing a
    number). A genuine 0.0 balance is returned as 0.0, NOT None — otherwise the
    equity-floor CRITICAL would go silent exactly at the value it exists for."""
    try:
        sys.path.insert(0, '/root/.hermes/scripts')
        from hyperliquid_exchange import get_account_value_curl
        r = get_account_value_curl()
        if not isinstance(r, dict) or r.get('account_value') is None:
            return None
        return float(r['account_value'])
    except Exception:
        return None


def collect():
    """Run every check once, no printing.

    Returns dict:
      lines         — print order: the frozen Tier-H block, book info, NS2, R1
      ok            — every GATE passed (Tier H + NS2 + R1)
      h_checks      — [(passed, label)] for the 9 frozen Tier-H gates
      health_pass   — Tier-H PASS count (the x/10 numerator)
      health_total  — 10 = 9 gates + the WR diagnostic line (frozen Tier-H line set)
      ns1, ns2, r1_dd_usd, r1_dd_pct, equity — formal KPI values (None = unmeasurable)
    """
    c = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = c.cursor()
    out = []
    ok = True
    h_checks = []

    def chk(cond, label, tier='H'):
        nonlocal ok
        cond = bool(cond)
        ok = ok and cond
        out.append(f"{'PASS' if cond else 'FAIL'}  {label}")
        if tier == 'H':
            h_checks.append((cond, label))

    # 1. jup share of rolling-50 closed (target < 35%)
    cur.execute("""SELECT COUNT(*) FILTER (WHERE signal LIKE '%jup_yolo%'), COUNT(*)
        FROM (SELECT * FROM trades WHERE status='closed' ORDER BY close_time DESC LIMIT 50) t""")
    j, n = cur.fetchone()
    chk(j / n < 0.35 if n else False,
        f"jup share rolling-50: {j}/{n} = {100*j/n:.0f}% (target <35%)")

    # 2. HML 7d (target <15 hits AND net > -$2.00)
    cur.execute("""SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0), COALESCE(SUM(pnl_usdt - amount_usdt*%s),0)
        FROM trades WHERE status='closed' AND exit_reason='hard_max_loss'
        AND close_time > NOW()-INTERVAL '7 days'""", (FEE,))
    hn, hp, hnet = cur.fetchone()
    chk(hn < 15, f"HML 7d count: {hn} (target <15)")
    chk(float(hnet) > -2.00, f"HML 7d net-of-fees: {float(hnet):+.2f} (target >-2.00)")

    # 3. net daily (24h and 72h, net-of-fees; target >=0 sustained 72h)
    for hrs in (24, 72):
        cur.execute(f"""SELECT COALESCE(SUM(pnl_usdt - amount_usdt*{FEE}),0), COUNT(*)
            FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '{hrs} hours'""")
        s, n = cur.fetchone()
        if hrs == 24:
            chk(float(s) >= 0, f"net 24h (fees in): {float(s):+.2f} over {n}T (target >=0)")
        else:
            chk(float(s) >= 0, f"net 72h (fees in): {float(s):+.2f} over {n}T (target >=0 = sustained)")

    # 4. direction ratio of fills last 48h LONG:SHORT (target <2:1)
    cur.execute("""SELECT COUNT(*) FILTER (WHERE direction='LONG'), COUNT(*) FILTER (WHERE direction='SHORT')
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '48 hours'""")
    nl, ns = cur.fetchone()
    ratio = (nl / ns) if ns else float('inf')
    chk(ratio < 2.0, f"fill ratio 48h LONG:SHORT = {nl}:{ns} = {ratio:.1f}:1 (target <2:1)")

    # 5. EXPECTANCY SET (RESTRUCTURED — CEO verdict 20261122T194418Z, T approval 2026-11-22:
    #    the old "fleet WR >=55%" target optimized the losing population (payoff<1.0 group =
    #    23 signals -$9.21 at WR 54.7%); WR is now DIAGNOSTIC ONLY, never a target.)
    # 5a. net $/trade fee-adj 7d (baseline -$0.0124; target >0 sustained 7d) = **NS1**
    cur.execute("""SELECT COUNT(*), COALESCE(SUM(pnl_usdt - amount_usdt*%s),0)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '7 days'""", (FEE,))
    n7, s7 = cur.fetchone()
    ns1 = float(s7) / n7 if n7 else 0.0
    chk(n7 > 0 and ns1 > 0,
        f"net $/trade 7d: {ns1:+.4f} over {n7}T (target >0 sustained; baseline -0.0124)")
    # 5b. fleet payoff ratio 14d (baseline ~1.05; target >=1.2)
    cur.execute("""SELECT COALESCE(AVG(pnl_usdt - amount_usdt*%s) FILTER (WHERE pnl_usdt > 0),0),
        COALESCE(AVG(pnl_usdt - amount_usdt*%s) FILTER (WHERE pnl_usdt < 0),0), COUNT(*)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'""", (FEE, FEE))
    aw, al, np_ = cur.fetchone()
    payoff = (float(aw) / abs(float(al))) if float(al) else 0.0
    chk(np_ >= 30 and payoff >= 1.2,
        f"fleet payoff 14d: {payoff:.2f} (aw {float(aw):+.3f} / al {float(al):+.3f}) over {np_}T (target >=1.2; baseline ~1.05)")
    # 5c. cost % notional RT 14d = synthetic fee + atr_sl stop-overshoot (exit_slippage_pct)
    #     (baseline ~0.22% = 0.10 fee + 0.12 overshoot; target <=0.15%)
    #     UNITS: exit_slippage_pct is stored as PERCENT (verified 2026-11-22: stored value ==
    #     ABS(exit-stop)/stop*100, e.g. 0.1063 == 0.1063%) — divide by 100 before * amount.
    cur.execute("""SELECT COALESCE(SUM(amount_usdt),0),
        COALESCE(SUM(amount_usdt*0.0009),0),
        COALESCE(SUM(CASE WHEN exit_reason='atr_sl_hit' THEN amount_usdt*COALESCE(exit_slippage_pct,0)/100.0 ELSE 0 END),0)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'""", ())
    tot_not, fee_sum, over_sum = cur.fetchone()
    cost_pct = (float(fee_sum) + float(over_sum)) / float(tot_not) * 100 if float(tot_not) else 99.0
    chk(cost_pct <= 0.15,
        f"cost % notional RT 14d: {cost_pct:.3f}% (fee {float(fee_sum)/float(tot_not)*100 if float(tot_not) else 0:.3f}% + overshoot {float(over_sum)/float(tot_not)*100 if float(tot_not) else 0:.3f}%) (target <=0.15%; baseline ~0.22%)")
    # WR = DIAGNOSTIC ONLY (no target) — reported, never gated (10th frozen Tier-H line)
    cur.execute("""SELECT COUNT(*), 100.0*SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END)/COUNT(*)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '14 days'""")
    wn, w = cur.fetchone()
    out.append(f"info  WR 14d (diagnostic, NO target): {float(w):.1f}% over {wn}T")

    health_pass = sum(1 for p, _ in h_checks if p)
    health_total = len(h_checks) + 1   # + the WR info line = the frozen 10 lines

    # book context (informational, not gated)
    for w_ in ('24 hours', '7 days'):
        cur.execute(f"""SELECT COUNT(*), ROUND(SUM(pnl_usdt)::numeric,2),
            ROUND(SUM(pnl_usdt - amount_usdt*{FEE})::numeric,2)
            FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '{w_}'""")
        b = cur.fetchone()
        out.append(f"info  book {w_}: {b[0]}T gross {b[1]} net {b[2]}")

    # NS2 (Tier N, GATED since verdict 20261122T221140Z — this was the book-30d info line)
    cur.execute(f"""SELECT COUNT(*), ROUND(SUM(pnl_usdt)::numeric,2),
        ROUND(SUM(pnl_usdt - amount_usdt*{FEE})::numeric,2)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '30 days'""")
    b30 = cur.fetchone()
    ns2 = float(b30[2])
    chk(ns2 >= NS2_TARGET,
        f"NS2 rolling 30d fee-net: {b30[0]}T gross {b30[1]} net {b30[2]} "
        f"(target >={NS2_TARGET:.2f}; baseline -10.32)", tier='N')

    # R1 (Tier R): 30d max drawdown = peak-to-trough of the DAILY cumulative fee-net
    # curve over 30d (curve starts at 0 at the window edge), as % of current equity.
    # DAILY aggregation — NOT trade-level (a trade-level cum would read intra-window
    # noise as drawdown and is a different number than the verdict's -76% baseline).
    cur.execute(f"""SELECT close_time::date, COALESCE(SUM(pnl_usdt - amount_usdt*{FEE}),0)
        FROM trades WHERE status='closed' AND close_time > NOW()-INTERVAL '30 days'
        GROUP BY 1 ORDER BY 1""")
    cum = peak = 0.0
    dd = 0.0
    for _d, s in cur.fetchall():
        cum += float(s)
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    eq = _equity()
    r1_pct = (dd / eq * 100.0) if (eq is not None and eq > 0) else None
    if r1_pct is None:
        why = ('equity UNAVAILABLE (clearinghouse read failed)' if eq is None
               else f'equity {eq:.2f} non-positive, % undefined')
        out.append(f"info  R1 30d max DD (daily cum fee-net): {dd:+.2f} — {why}; "
                   f"% gate skipped this run (degrade to dollars, never invent equity)")
    else:
        chk(r1_pct >= R1_TARGET_PCT,
            f"R1 30d max DD (daily cum fee-net): {dd:+.2f} = {r1_pct:.1f}% of equity "
            f"{eq:.2f} (target >={R1_TARGET_PCT:.0f}% of equity; baseline -76%)",
            tier='R')

    cur.close()
    c.close()
    return {
        'lines': out, 'ok': ok, 'h_checks': h_checks,
        'health_pass': health_pass, 'health_total': health_total,
        'ns1': ns1, 'ns2': ns2, 'r1_dd_usd': dd, 'r1_dd_pct': r1_pct, 'equity': eq,
    }


# ── consecutive-run state (for the >=2 Tier-H alert rule) ──────────────────────
def _load_state():
    """FAIL-OPEN: an unreadable/corrupt/non-dict state file resets to {} (counters
    restart from zero). A bad file must never crash the verifier and must never
    fabricate a >=2 consecutive alert — losing history costs one alert at most."""
    try:
        with open(STATE_FILE) as f:
            s = json.load(f)
        return s if isinstance(s, dict) else {}
    except Exception:
        return {}


def _save_state(state):
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(STATE_FILE), suffix='.tmp')
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=1)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        if tmp:
            try:
                os.unlink(tmp)
            except Exception:
                pass
        print(f"WARN  goal-metrics state save failed ({e}) — counters not persisted",
              file=sys.stderr)


def _update_state(h_checks, now_iso):
    """Bump per-gate consecutive-fail counters on EVERY run (not just --kanban):
    'consecutive verifier runs' must count all verifier runs. Returns {key: n}.

    Fail-open twice over: an unreadable file resets everything (see _load_state),
    and a per-key value that is not a plain non-negative integer reads as 0. A
    valid-but-wrong integer is indistinguishable from truth and is trusted."""
    st = _load_state()
    consec = st.get('consec')
    if not isinstance(consec, dict):
        consec = {}
    for passed, label in h_checks:
        key = label.split(':', 1)[0].strip()
        v = consec.get(key, 0)
        try:
            n = int(v)
            if n != v or n < 0 or n > 10000:   # strings/bools/negatives/absurd = garbage
                n = 0
        except Exception:
            n = 0                      # fail-open on garbage values
        consec[key] = 0 if passed else n + 1
    st['consec'] = consec
    st['updated_at'] = now_iso
    _save_state(st)
    return consec


# ── kanban (verdict 20261122T221140Z §3 alerting rules) ────────────────────────
def _kanban_lines(r, consec, now_iso):
    """FAIL lines only: NS1, NS2, R1, Tier-H gates failing >=2 consecutive runs,
    equity < $10. Passive-display metrics (jup/HML/pair/ratio/cost/arm-rate) and WR
    never alert. Dedupe by label key so NS1 is not double-reported as Tier-H."""
    lines, seen = [], set()

    def add(key, text):
        if key not in seen:
            seen.add(key)
            lines.append(text)

    if r['ns1'] is not None and r['ns1'] <= 0:
        add(NS1_LABEL_KEY,
            f"- [{now_iso}] goal-metrics: ❌ [KPI-FAIL] NS1 net $/trade 7d = "
            f"{r['ns1']:+.4f} (target >0) — Tier-N north-star, verdict 20261122T221140Z")
    if r['ns2'] is not None and r['ns2'] < NS2_TARGET:
        add('NS2',
            f"- [{now_iso}] goal-metrics: ❌ [KPI-FAIL] NS2 rolling 30d fee-net = "
            f"{r['ns2']:+.2f} (target >={NS2_TARGET:.2f}; baseline -10.32)")
    if r['r1_dd_pct'] is not None and r['r1_dd_pct'] < R1_TARGET_PCT:
        add('R1',
            f"- [{now_iso}] goal-metrics: ❌ [KPI-FAIL] R1 30d max DD = "
            f"{r['r1_dd_usd']:+.2f} ({r['r1_dd_pct']:.1f}% of equity {r['equity']:.2f}) "
            f"(target >={R1_TARGET_PCT:.0f}% of equity; baseline -76%)")
    for passed, label in r['h_checks']:
        if passed:
            continue
        key = label.split(':', 1)[0].strip()
        try:
            n = int(consec.get(key, 0))
        except Exception:
            n = 0
        if n >= TIER_H_CONSEC_ALERT:
            add(key,
                f"- [{now_iso}] goal-metrics: ⚠️ [TIER-H] {label} — FAIL x{n} "
                f"consecutive verifier runs (alert at >=2, verdict 20261122T221140Z)")
    if r['equity'] is not None and r['equity'] < EQUITY_FLOOR:
        add('equity',
            f"- [{now_iso}] goal-metrics: 🔴 [CRITICAL] equity ${r['equity']:.2f} < "
            f"${EQUITY_FLOOR:.0f} floor — RECOMMEND kill-switch review to T "
            f"(report-only: no switch, no flag, no trade path touched)")
    return lines


def _append_kanban(lines, now_iso):
    """Append-only, in the shadow_disposition packet shape (blank line + run header
    + one '- [{ts}] goal-metrics: ...' line per alert). Never rewrites the file."""
    if not lines:
        return
    try:
        with open(KANBAN, 'a') as f:
            f.write(f'\n## goal_metrics run {now_iso} ({len(lines)} action(s))\n')
            f.write('\n'.join(lines) + '\n')
    except Exception as e:
        print(f"WARN  kanban append failed ({e}) — alerts not delivered",
              file=sys.stderr)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    want_kanban = '--kanban' in argv
    now_iso = datetime.now(timezone.utc).isoformat(timespec='seconds')

    r = collect()
    consec = _update_state(r['h_checks'], now_iso)
    klines = _kanban_lines(r, consec, now_iso) if want_kanban else []
    if want_kanban:
        _append_kanban(klines, now_iso)

    print("GOAL-704ed65e METRICS", "-" * 50)
    for line in r['lines']:
        print(" ", line)
    print("RESULT:", "ALL PASS" if r['ok'] else "NOT YET (goal active)")
    if want_kanban:
        print("KANBAN:", (f"{len(klines)} line(s) -> {KANBAN}" if klines
                          else "no FAIL lines — nothing appended"))
    return 0 if r['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
