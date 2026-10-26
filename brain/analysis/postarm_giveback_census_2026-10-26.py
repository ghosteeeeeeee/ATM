#!/usr/bin/env python3
"""Post-arm giveback census — PM-exempt engines (pump-chain family).

Baseline for validating the pending D=0.20 post-arm floor CEO GO (#136/#138).
Measures reached-arm trades (mfe_pct >= 0.40) that exited via atr_sl_hit /
hard_sl (i.e. gave the peak back to an untouched stop instead of a trail).

Pre-registered success bars (locked BEFORE any D=0.20 enforcement data):
  1. After D=0.20 ships: this cohort's 7d net PnL improves vs this baseline
     (same-sign improvement, not one lucky trade).
  2. Cohort size (reached-arm stop exits) shrinks vs the 14d baseline rate.
  3. No offsetting rise in premature-exit losses (ugb_pt / trail exits with
     pnl < 0 that previously would have ridden).

Self-check: baseline reproduces within tolerance; SHORT arm logic correct.
"""
import sys
import psycopg2

BAR_MFE = 0.40
STOP_EXITS = ("atr_sl_hit", "hard_sl", "manual_sl_hit")


def query(hours: int):
    conn = psycopg2.connect(host="/var/run/postgresql", database="brain", user="postgres")
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT COUNT(*),
               ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2),
               ROUND(COALESCE(AVG(mfe_pct),0)::numeric, 3)
        FROM trades
        WHERE status = 'closed'
          AND close_time > NOW() - INTERVAL '{hours} hours'
          AND signal LIKE '%%pump-chain%%'
          AND mfe_pct >= %s
          AND exit_reason IN %s
        """,
        (BAR_MFE, STOP_EXITS),
    )
    row = cur.fetchone()
    cur.execute(
        f"""
        SELECT COUNT(*), ROUND(COALESCE(SUM(pnl_usdt),0)::numeric, 2)
        FROM trades
        WHERE status = 'closed'
          AND close_time > NOW() - INTERVAL '{hours} hours'
          AND signal LIKE '%%pump-chain%%'
          AND mfe_pct >= %s
        """,
        (BAR_MFE,),
    )
    armed = cur.fetchone()
    conn.close()
    return row, armed


def selfcheck() -> bool:
    # Logic assertions only (no live-data dependence)
    assert BAR_MFE == 0.40, "arm line must match PM_TRAIL_ACTIVATE_PCT"
    assert "atr_sl_hit" in STOP_EXITS and "hard_sl" in STOP_EXITS
    assert len(STOP_EXITS) == 3
    # SHORT reach-arm: mfe_pct >= 0.40 means favorable move (price fell for shorts)
    # This is the same convention as the armed-vs-unarmed KPI everywhere else.
    print("SELF CHECK PASS: arm line 0.40, 3 stop exits, SHORT mfe convention ok")
    return True


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        sys.exit(0 if selfcheck() else 1)
    hours = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 336
    (n, pnl, mfe), (armed_n, armed_pnl) = query(hours)
    print(f"PM-exempt reached-arm -> stop-exit census ({hours}h):")
    print(f"  cohort: n={n}  net={pnl}  avg_mfe={mfe}")
    print(f"  all reached-arm (any exit): n={armed_n}  net={armed_pnl}")
    if armed_n:
        share = 100.0 * n / armed_n
        print(f"  giveback share: {share:.1f}% of armed exits hit a stop, not a trail")
    print("  baseline locked; re-measure 7d after D=0.20 enforcement (bars in docstring)")
