#!/usr/bin/env python3
"""Stop-tighten SCOPE-widen counterfactual (audit #237, 2026-11-08).

STATUS 2026-11-08 later same day (CEO consult 20261108T180116Z): SCOPE WIDENED
AND SHIPPED — STOP_TIGHTEN_SOURCES is now 8 names matched by SUBSTRING (see
scripts/hermes_constants.py:761). SCOPE_IN/SCOPE_OUT below stay FROZEN at the
pre-widen split so re-running this script reproduces the CEO's numbers; they are
NOT the live scope anymore. Two caveats recorded in registry
amplify-stoptighten-scope-widen: (a) this is ceiling math, not the 1m/5m
candle-walk that threshold limb (i) names; (b) restricted to the population the
change actually covers (the new 6 + jup combos) the net limb runs $0.88/30d
pace vs the $1.00/30d bar, while the full out-of-scope population this script
measures runs $1.88/30d pace.

At authoring time STOP_TIGHTEN_SOURCES covered only
('jup_yolo_mirrored','volume-buildup-') but the
stop-family bleed (hard_max_loss + atr_sl_hit) sits on BOTH sides of that scope
line. This script measures the out-of-scope half:

  1. 14d out-of-scope stop-family bleed (n, pnl_usdt)
  2. Counterfactual ceiling: for losers whose actual price move exceeded the
     0.75% cap, saving = (move% - 0.75) * amount_usdt / 100  [pnl_usdt units,
     UNITS RULE #193 — never compare raw price move to stored pnl_pct]
  3. fk: out-of-scope WINNERS that touched >=0.75% adverse during the hold
     (these are the winners a 0.75% clamp would have killed)
  4. Weekly same-sign check over 30d

Bars (pre-registered with this script, proposal amplify-stoptighten-scope-widen):
  n>=30 stop-family losers out-of-scope ∧ fk <=20% of out-of-scope winners ∧
  walk-confirmed net >= +$1.00/30d ∧ 30d weekly same-sign.

Mechanics note: tpsl_utils.stop_tighten_sl is called at 6 ATR-SL placement
sites (decider_run x3, position_manager, hl_sync_guardian, self_close_watcher),
each passing `source` through — extending STOP_TIGHTEN_SOURCES is a zero-code
tuple change. Prerequisite before any ship: confirm each target signal's SL
actually flows through one of those sites (signals with no ATR-SL placement
get no clamp).
"""
import sys
import psycopg2

SCOPE_OUT = ("signal NOT IN ('jup_yolo_mirrored','volume-buildup-')")
SCOPE_IN = ("signal IN ('jup_yolo_mirrored','volume-buildup-')")
CAP = 0.75


def _conn():
    return psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')


def run(window_days=14):
    conn = _conn()
    cur = conn.cursor()
    out = {}

    cur.execute(f"""
        SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0)
        FROM trades WHERE status='closed'
          AND exit_reason IN ('hard_max_loss','atr_sl_hit')
          AND close_time > NOW() - INTERVAL '{window_days} days'
          AND {SCOPE_OUT}""")
    n, bleed = cur.fetchone()
    out['n_stop_family'] = int(n)
    out['bleed'] = round(float(bleed), 2)

    # ceiling: losers beyond cap
    cur.execute(f"""
        SELECT COALESCE(SUM(CASE WHEN ABS(entry_price-exit_price)/entry_price*100 > {CAP}
                         THEN 1 ELSE 0 END),0),
               COALESCE(SUM(CASE WHEN ABS(entry_price-exit_price)/entry_price*100 > {CAP}
                    THEN (ABS(entry_price-exit_price)/entry_price*100 - {CAP})
                         * amount_usdt / 100 ELSE 0 END),0)
        FROM trades WHERE status='closed'
          AND exit_reason IN ('hard_max_loss','atr_sl_hit') AND pnl_usdt < 0
          AND close_time > NOW() - INTERVAL '{window_days} days'
          AND {SCOPE_OUT}""")
    beyond_n, saving = cur.fetchone()
    out['beyond_cap_n'] = int(beyond_n)
    out['ceiling_saving'] = round(float(saving), 2)

    # fk: out-of-scope winners touching >= CAP adverse
    cur.execute(f"""
        SELECT COUNT(*),
               COALESCE(SUM(CASE WHEN mae_pct >= {CAP} THEN 1 ELSE 0 END),0),
               COALESCE(SUM(CASE WHEN mae_pct >= {CAP} THEN pnl_usdt ELSE 0 END),0)
        FROM trades WHERE status='closed' AND pnl_usdt > 0
          AND close_time > NOW() - INTERVAL '{window_days} days'
          AND {SCOPE_OUT} AND mae_pct IS NOT NULL""")
    winners, fk_n, fk_pnl = cur.fetchone()
    out['winners'] = int(winners)
    out['fk_n'] = int(fk_n)
    out['fk_pct'] = round(100.0 * fk_n / winners, 1) if winners else 0.0
    out['fk_pnl_at_risk'] = round(float(fk_pnl), 3)
    out['net_ceiling'] = round(out['ceiling_saving'] - out['fk_pnl_at_risk'], 2)

    # weekly same-sign 30d
    cur.execute(f"""
        SELECT date_trunc('week', close_time)::date, SUM(pnl_usdt)
        FROM trades WHERE status='closed'
          AND exit_reason IN ('hard_max_loss','atr_sl_hit')
          AND close_time > NOW() - INTERVAL '30 days'
          AND {SCOPE_OUT}
        GROUP BY 1 ORDER BY 1""")
    weeks = [(str(w), round(float(p), 2)) for w, p in cur.fetchall()]
    out['weeks_30d'] = weeks
    out['weeks_negative'] = sum(1 for _, p in weeks if p < 0)
    out['weeks_total'] = len(weeks)

    # in-scope reference
    cur.execute(f"""
        SELECT COUNT(*), COALESCE(SUM(pnl_usdt),0)
        FROM trades WHERE status='closed'
          AND exit_reason IN ('hard_max_loss','atr_sl_hit')
          AND close_time > NOW() - INTERVAL '{window_days} days'
          AND {SCOPE_IN}""")
    in_n, in_bleed = cur.fetchone()
    out['in_scope_n'] = int(in_n)
    out['in_scope_bleed'] = round(float(in_bleed), 2)

    conn.close()
    return out


def bars(o):
    return {
        'n>=30': o['n_stop_family'] >= 30,
        'fk<=20%': o['fk_pct'] <= 20.0,
        'net_ceiling>=$1.00/30d_pace': o['net_ceiling'] * 30 / 14 >= 1.00,
        'weekly_same_sign_30d': o['weeks_total'] > 0 and o['weeks_negative'] == o['weeks_total'],
    }


def main():
    o = run()
    print("=== stop-tighten SCOPE-widen counterfactual (out-of-scope half) ===")
    for k in ('n_stop_family', 'bleed', 'beyond_cap_n', 'ceiling_saving',
              'winners', 'fk_n', 'fk_pct', 'fk_pnl_at_risk', 'net_ceiling',
              'in_scope_n', 'in_scope_bleed', 'weeks_negative', 'weeks_total'):
        print(f"  {k}: {o[k]}")
    print(f"  weeks_30d: {o['weeks_30d']}")
    b = bars(o)
    print("BARS:")
    for k, v in b.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    verdict = all(b.values())
    print(f"VERDICT: {'ALL BARS PASS (walk still required before ship)' if verdict else 'FAIL - do not ship'}")
    return 0 if verdict else 1


def selfcheck():
    """Assert hand-computable identities on the live query."""
    o = run()
    assert o['n_stop_family'] >= 30, "sample below bar"
    # ceiling cannot exceed |bleed|
    assert o['ceiling_saving'] <= abs(o['bleed']) + 1e-6, "ceiling exceeds bleed"
    # net = ceiling - fk risk
    assert abs(o['net_ceiling'] - (o['ceiling_saving'] - o['fk_pnl_at_risk'])) < 1e-6
    # fk_pct in [0,100]
    assert 0 <= o['fk_pct'] <= 100
    # beyond_n <= loser stop-family n (stop-family exits are ~all losers)
    assert 0 <= o['beyond_cap_n'] <= o['n_stop_family']
    # units sanity: ceiling must be positive-only sum
    assert o['ceiling_saving'] >= 0
    # weekly windows: every 30d week negative for same-sign claim
    assert o['weeks_total'] >= 4, "30d should hold ~4-5 week buckets"
    print(f"SELFCheck PASS: n={o['n_stop_family']} bleed={o['bleed']} "
          f"beyond={o['beyond_cap_n']} ceiling={o['ceiling_saving']} fk={o['fk_pct']}% "
          f"net={o['net_ceiling']} weeks {o['weeks_negative']}/{o['weeks_total']} neg")
    return 0


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        sys.exit(selfcheck())
    sys.exit(main())
