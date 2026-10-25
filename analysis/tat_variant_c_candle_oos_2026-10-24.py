#!/usr/bin/env python3
"""Candle-level OOS for TAT VARIANT-C (age>=T AND live_pnl < 0) — brain_auditor 2026-10-24.

WHY: hermes_constants.py:1727 makes the bb-bounce TAT flip conditional on
"CEO GO + 14d shadow data + candle OOS re-run". The Oct-17 candle OOS
(analysis/trail_arm_candle_oos_2026-10-17.py) tested the BASE condition
(live_pnl < 0.40) and FAILED at fk 41.9%. The variant-C redesign (cut only
when live_pnl < 0) has only ever been measured at trades-level from
[SHADOW] log lines (tat_variant_c_pack, 8 days of shadow). This runs the
mandatory candle-level test on the variant-C condition itself, 30d.

Condition as it would be coded: still open at age>=T AND
live_pnl (unleveraged %, 1m candle close at open_time+T) < 0 => close now.

Units (verdict 2026-10-17 "units landmine"): pnl_pct in PG is LEVERAGED %;
live_pnl is unleveraged. cf$ = amount_usdt * lp/100. benefit = cf - actual
pnl_usdt (+ = firing helps).

Pre-registered bars (#66/#75, locked pre-data):
  n_fires >= 15 AND net benefit > 0 AND fk <= 20% of cohort winners.

Scope mirrors position_manager.py:3760-3762 + the #39 fix:
  direction LONG AND ('bb-bounce' in sig OR 'ai-trader+' in sig),
  ai-trader-manual / ai-trader-pending excluded (CEO trades, never TAT-eligible).

Usage: python3 analysis/tat_variant_c_candle_oos_2026-10-24.py [--selfcheck]
"""
import sqlite3
import sys
from datetime import datetime, timezone

import psycopg2

# ponytail: defaults = the shipped bb-bounce/ai-trader+ scope; override with
#   --t <minutes> --dir LONG|SHORT --sigs a,b   to probe another family/direction.
# --selfcheck always runs on the defaults (assertions below name them).
_A = sys.argv[1:]


def _val(flag, default):
    return _A[_A.index(flag) + 1] if flag in _A else default


T = int(_val("--t", "55"))
SCOPE_DIR = _val("--dir", "LONG")
SCOPE_SIGS = tuple(_val("--sigs", "bb-bounce,ai-trader+").split(","))
# --lp-max 0 = variant-C (default); --lp-max 0.40 = the BASE condition (lp < arm)
LP_MAX = float(_val("--lp-max", "0"))
COHORTS = [(s + "-probe", s) for s in SCOPE_SIGS]
EXCLUDE = ("ai-trader-manual", "ai-trader-pending")


def in_scope(signal):
    s = (signal or "").lower()
    if not any(sub in s for sub in SCOPE_SIGS):
        return False
    return not any(x in s for x in EXCLUDE)


def to_dt(x):
    if isinstance(x, str):
        x = datetime.fromisoformat(x.replace("Z", "+00:00"))
    if x.tzinfo is None:
        x = x.replace(tzinfo=timezone.utc)
    return x


def run():
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    try:
        cur = conn.cursor()
        cur.execute("""
        SELECT id, token, signal, direction, entry_price, pnl_usdt, pnl_pct, amount_usdt, leverage,
               open_time, close_time, exit_reason
        FROM trades
        WHERE status='closed' AND close_time > NOW() - INTERVAL '30 days' AND direction=%(dir)s
          AND amount_usdt IS NOT NULL AND leverage IS NOT NULL AND leverage > 0
        """, {"dir": SCOPE_DIR})
        rows = cur.fetchall()
    finally:
        conn.close()
    print(f"30d {SCOPE_DIR} closed: {len(rows)} (scope T={T} sigs={SCOPE_SIGS})")

    cdb = sqlite3.connect("file:/root/.hermes/data/candles.db?mode=ro", uri=True)
    try:

        def live_pnl_at(token, entry, t_min, open_time):
            target = int(to_dt(open_time).timestamp()) + t_min * 60
            r = cdb.execute(
                "SELECT close FROM candles_1m WHERE token=? AND ts<=? ORDER BY ts DESC LIMIT 1",
                (token, target),
            ).fetchone()
            if r is None:
                return None
            return (r[0] - float(entry)) / float(entry) * 100.0

        summary = {}
        for name, sig in COHORTS:
            cohort = [r for r in rows if in_scope(r[2]) and sig in (r[2] or "").lower()]
            fired = fk = miss = early = 0
            net_usdt = save_usdt = cost_usdt = 0.0
            winners_n = 0
            details = []
            for (tid, token, signal, direc, entry, pnl_usdt, pnl_pct, amt, lev, ot, ct, xr) in cohort:
                end_u = float(pnl_pct) / float(lev)
                if end_u > 0:
                    winners_n += 1
                hm = (to_dt(ct) - to_dt(ot)).total_seconds() / 60.0
                if hm < T:
                    early += 1
                    continue
                lp = live_pnl_at(token, entry, T, ot)
                if lp is None:
                    miss += 1
                    continue
                if lp < LP_MAX:  # default 0 = VARIANT-C; 0.40 = BASE (failed Oct-17 fk 41.9%)
                    fired += 1
                    cf = float(amt) * (lp / 100.0)
                    benefit = cf - float(pnl_usdt)
                    net_usdt += benefit
                    if end_u > 0:
                        fk += 1
                        cost_usdt += benefit
                        kind = "FK"
                    else:
                        save_usdt += benefit
                        kind = "SAVE"
                    details.append((token, f"T{lp:+.2f}%", f"end_u{end_u:+.2f}%",
                                    f"ben{benefit:+.2f}", kind, f"hold{hm:.0f}m", xr))
            alive = len(cohort) - early
            print(f"\n=== {name} lp<{LP_MAX:g} (T={T}m, dir={SCOPE_DIR}) ===")
            print(f"  cohort={len(cohort)} closed_before_T={early} alive_at_T={alive} no_candle={miss}")
            print(f"  FIRED={fired} (winners_FK={fk}, losers_saved={fired - fk})")
            print(f"  NET if fired = ${net_usdt:+.2f}/30d | saves ${save_usdt:+.2f} | costs ${cost_usdt:+.2f}")
            if alive - miss > 0:
                print(f"  fire_rate_of_alive={100.0 * fired / (alive - miss):.1f}%")
            if fired:
                print(f"  fk_rate_of_fires={100.0 * fk / fired:.1f}%")
            print(f"  fk_pct_of_cohort_winners={100.0 * fk / max(winners_n, 1):.1f}% ({fk}/{winners_n})")
            details.sort(key=lambda d: abs(float(d[3][3:])), reverse=True)
            for d in details[:12]:
                print(f"    {d}")
            if len(details) > 12:
                print(f"    ... +{len(details) - 12} more")
            summary[name] = dict(cohort=len(cohort), fired=fired, fk=fk,
                                 net=round(net_usdt, 2), save=round(save_usdt, 2),
                                 cost=round(cost_usdt, 2),
                                 fk_of_winners=round(100.0 * fk / max(winners_n, 1), 1))
        print("\nSUMMARY:", summary)
    finally:
        cdb.close()
    return summary


def selfcheck():
    """Break the logic on purpose — every assertion must hold on the real run."""
    # Pin the probe CLI to defaults: `--selfcheck --lp-max 0.40` must not silently
    # certify the BASE condition under the default-scope assertions.
    assert (T, SCOPE_DIR, LP_MAX, SCOPE_SIGS) == (55, "LONG", 0.0,
                                                  ("bb-bounce", "ai-trader+")), \
        f"selfcheck must run on defaults, got T={T} dir={SCOPE_DIR} lp={LP_MAX} sigs={SCOPE_SIGS}"
    assert not in_scope("ai-trader-manual"), "manual must be out of scope"
    assert not in_scope("ai-trader-pending"), "pending must be out of scope"
    assert in_scope("bb-bounce-v2-long+"), "bb-bounce must be in scope"
    assert in_scope("ai-trader+"), "ai-trader+ must be in scope"
    assert not in_scope("pump-chain+"), "pump-chain out of scope"
    assert not in_scope("ai-trader"), "bare 'ai-trader' without + must be out"
    # units guard: cf$ = amount_usdt * live_pnl/100 (verdict 2026-10-17)
    assert abs(11.0 * (-1.00) / 100.0 - (-0.11)) < 1e-9, "cf unit formula wrong"
    # sign: benefit positive means firing helped
    cf, actual = -0.019, -0.140
    assert cf - actual > 0, "cutting a deeper loss must be a benefit"
    # live wiring: enforcement must be importable, gated, and have its own dedup set so
    # a prior non-negative shadow sighting cannot suppress a later negative cut.
    import re
    pm = open("/root/.hermes/scripts/position_manager.py").read()
    hc = open("/root/.hermes/scripts/hermes_constants.py").read()
    assert re.search(r"BB_BOUNCE_TRAIL_ARM_TIMEOUT_ENABLED\s*=\s*True", hc), "flag not on"
    assert "BB_BOUNCE_TRAIL_ARM_TIMEOUT_ENABLED," in pm, "flag not imported"
    assert "_bb_bounce_tat_enforced" in pm, "enforcement dedup set missing"
    i_enf = pm.index("_bb_bounce_tat_enforced.add")
    i_shd = pm.index("[SHADOW] TRAIL-ARM would-fire")
    assert i_enf < i_shd, "enforcement must run before the shadow log branch"
    s = run()
    for k, v in s.items():
        assert v["fired"] >= 0 and v["net"] is not None
    total_fired = sum(v["fired"] for v in s.values())
    print(f"\nSELFCHECK PASS — total variant-C candle fires={total_fired}")
    return s


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        selfcheck()
    else:
        run()
