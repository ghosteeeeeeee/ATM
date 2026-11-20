# Self-Audit — Gate Usefulness Deep Dive 2026-11-19

Second computation path for every headline number. External auditors: refute or agree per check.

| Check | Description | Result | Detail |
|---|---|---|---|
| A1 | independent re-coalescing of events export matches summary | PASS | CONFLUENCE-GATE-BLOCK: n OK mean OK; CONTINUUM-BLOCK: n OK mean OK; CONTINUUM-BULL: n OK mean OK; SHORT-RSI-HARD-FLOOR: n OK mean OK ... |
| A2 | random events: log line exists (reparse prov) + independent fwd recompute | PASS | XAI/LONG @11-18 11:40 log=OK fwd=OK; FIL/SHORT @10-26 19:41 log=n/a (db-only, raw deleted) fwd=OK; ALT/SHORT @10-23 01:30 log=n/a (db-only, raw deleted) fwd=OK; AIXBT/LONG @11-02 13:50 log=OK fwd=OK; RENDER/LONG @11-01 11:51 log=OK fwd=OK |
| A3 | excess re-derived via independent SQL baseline (300-token sample) | PASS | BTC: sql_excess=-0.9758 export=-0.9758 (OK) n_tokens=185; ALT: sql_excess=+1.1043 export=+1.1042 (OK) n_tokens=185; NEAR: sql_excess=+0.8321 export=+0.8320 (OK) n_tokens=183 |
| A4 | live-book WR/net second SQL + pnl_usdt/pnl_pct sign consistency | PASS | LONG: n=729 WR=46.4% net=-6.89 sign_consistent=716/729 (mismatches = $0.00 scratches); SHORT: n=318 WR=48.7% net=-1.71 sign_consistent=312/318 (mismatches = $0.00 scratches) |
| A5 | no duplicate (gate,token,dir,10min) in events export | PASS | duplicates=0 / 88315 rows |
| A6 | big-miss MFE values vs raw candles | PASS | SOPH: recomputed=14.35 export=14.35 OK; CHIP: recomputed=10.56 export=10.56 OK; BABY: recomputed=10.97 export=10.97 OK; SOPH: recomputed=17.53 export=17.53 OK |

**Overall: 6/6 PASS — ALL CHECKS PASSED**
