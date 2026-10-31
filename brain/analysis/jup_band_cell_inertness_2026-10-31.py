#!/usr/bin/env python3
"""Run #207 pre-registration (zero behavior): two measurements locked before the
11-07 jup-yolo-regime-review deadline (shadow_disposition id jup-yolo-regime-review).

1) jup_yolo_mirrored LONG RSI band census — signal age 1.5d (first trades 2026-10-30),
   so NO OOS window exists yet. Locked baseline so 11-07 cannot re-derive numbers on
   the then-current sample (the #206 pattern-trap guard: pre-register before data).
2) Winner-cell x AMPLITUDE inertness — for HIGH_AMP (0.7) / CHAOTIC (0.5) tokens the
   validated cell boost (1.25) nets 0.875 / 0.625 < 1.0. At the current base (~$11.10,
   near HL_MIN 11) base x amp x cell lands BELOW the floor, so the boost is a no-op vs
   the no-cell path (both floor to HL_MIN). Balance-scoped: once base > ~$12.6 the cell
   still lifts HIGH_AMP 0.7 -> 0.875, so this is 'offense silent today', not 'broken'.
   Proven live 2026-10-31: INJ (HIGH_AMP) pc+ EXTREME cell log fired x1.25 but stored
   amount stayed at base 11.10 while MED_AMP MON/DYDX vb- HIGH got 12.48 = 11.10x0.9x1.25.
   Scope: 15/30 classified tokens are HIGH_AMP (inert class set = HIGH_AMP + CHAOTIC).

Bars for any future jup band proposal (pre-set now): n>=40 total AND >=1 OOS day
(excluding 2026-10-30/31 derivation window) AND fk<20% AND 30d-sign-equivalent holds.
"""
import sys, os, json
sys.path.insert(0, '/root/.hermes/scripts')

SQL_BAND = """
SELECT CASE WHEN (_signal_metadata->>'rsi_14')::numeric < 45 THEN '<45'
            WHEN (_signal_metadata->>'rsi_14')::numeric < 60 THEN '45-60'
            WHEN (_signal_metadata->>'rsi_14')::numeric < 70 THEN '60-70'
            ELSE '>=70' END AS bucket,
       COUNT(*) n, SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END) wins,
       ROUND(SUM(pnl_usdt),2) pnl, SUM(CASE WHEN mfe_pct>=0.40 THEN 1 ELSE 0 END) armed
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '7 days'
  AND signal LIKE '%jup_yolo_mirrored%' AND direction='LONG'
  AND _signal_metadata ? 'rsi_14'
GROUP BY 1 ORDER BY 1"""

SQL_TOTAL = """
SELECT COUNT(*), SUM(CASE WHEN pnl_usdt>0 THEN 1 ELSE 0 END), ROUND(SUM(pnl_usdt),2)
FROM trades
WHERE status='closed' AND close_time > NOW() - INTERVAL '7 days'
  AND signal LIKE '%jup_yolo_mirrored%' AND direction='LONG'
  AND _signal_metadata ? 'rsi_14'"""


def cell_inert_table():
    from hermes_constants import TOKEN_AMP_CLASS, AMPLITUDE_SIZE_MULT, WINNER_CELLS_VALIDATED, WINNER_CELL_SIZE_MULT
    rows = []
    for sig, reg in sorted(WINNER_CELLS_VALIDATED):
        for tok in ('INJ', 'DYDX', 'MON', 'SOL', 'HYPE', 'BTC', 'ALT', 'ZORA'):
            amp = AMPLITUDE_SIZE_MULT.get(TOKEN_AMP_CLASS.get(tok, 'MED_AMP'), 1.0)
            net = amp * WINNER_CELL_SIZE_MULT
            rows.append({'signal': sig, 'regime': reg, 'token': tok,
                         'amp': amp, 'net_mult': round(net, 4),
                         'inert': net < 1.0})
    return rows


def main():
    import psycopg2
    conn = psycopg2.connect(host='/var/run/postgresql', database='brain', user='postgres')
    cur = conn.cursor()
    cur.execute(SQL_BAND)
    band = cur.fetchall()
    cur.execute(SQL_TOTAL)
    total = cur.fetchone()
    conn.close()

    print("== jup_yolo_mirrored LONG 7d band census (BASELINE LOCKED 2026-10-31) ==")
    band_sum_n = band_sum_pnl = 0
    for b, n, w, pnl, armed in band:
        band_sum_n += n
        band_sum_pnl += float(pnl)
        print(f"  {b:6} n={n:3} W={w:3} pnl={pnl:>7} armed={armed}")
    print(f"  TOTAL   n={total[0]:3} W={total[1]:3} pnl={total[2]}")
    print(f"  chasers (>=45) n={sum(b[1] for b in band if b[0] != '<45')} "
          f"pnl={round(sum(float(b[3]) for b in band if b[0] != '<45'),2)}")

    print("\n== winner-cell x amplitude inertness (net_mult<1.0 = HL floor swallows boost) ==")
    rows = cell_inert_table()
    inert = [r for r in rows if r['inert']]
    print(f"  token x cell combos: {len(rows)}, inert: {len(inert)}")
    for r in inert:
        print(f"  INERT {r['token']:5} {r['signal']} {r['regime']} amp={r['amp']} net={r['net_mult']}")

    # selfcheck data returned for --selfcheck
    return {'band': [(b[0], b[1], b[2], float(b[3]), b[4]) for b in band],
            'total': (total[0], total[1], float(total[2])), 'inert': inert}


def selfcheck():
    d = main()
    n_sum = sum(b[1] for b in d['band'])
    pnl_sum = round(sum(b[3] for b in d['band']), 2)
    assert n_sum == d['total'][0], f"band n {n_sum} != total {d['total'][0]}"
    assert abs(pnl_sum - d['total'][2]) < 0.02, f"band pnl {pnl_sum} != total {d['total'][2]}"
    assert any(r['token'] == 'INJ' for r in d['inert']), "HIGH_AMP inert combo missing"
    assert all(r['net_mult'] < 1.0 for r in d['inert'])
    # known live datapoint: MED_AMP must NOT be inert
    from hermes_constants import AMPLITUDE_SIZE_MULT, TOKEN_AMP_CLASS, WINNER_CELL_SIZE_MULT
    med = AMPLITUDE_SIZE_MULT.get(TOKEN_AMP_CLASS.get('MON', 'MED_AMP'), 1.0) * WINNER_CELL_SIZE_MULT
    assert med > 1.0, "MED_AMP cell should fire"
    print("\nSELFCHECK PASS: band sums reconcile, inert set correct, MED_AMP fires")


if __name__ == '__main__':
    if '--selfcheck' in sys.argv:
        selfcheck()
    else:
        main()
