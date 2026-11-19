# Self-Audit — Gate Usefulness Deep Dive 2026-11-19

Second computation path for every headline number. External auditors: refute or agree per check.

| Check | Description | Result | Detail |
|---|---|---|---|
| A1 | independent re-coalescing of events export matches summary | PASS | CONFLUENCE-GATE-BLOCK: n OK mean OK; CONTINUUM-BLOCK: n OK mean OK; CONTINUUM-BULL: n OK mean OK; SHORT-RSI-HARD-FLOOR: n OK mean OK ... |
| A2 | random events: log line exists (reparse prov) + independent fwd recompute | PASS | ETH/LONG @10-26 19:00 log=n/a (db-only, raw deleted) fwd=OK; LDO/LONG @10-22 23:20 log=n/a (db-only, raw deleted) fwd=OK; LDO/LONG @11-02 16:02 log=OK fwd=OK; HYPE/LONG @11-01 13:50 log=OK fwd=OK; HYPE/SHORT @10-31 16:06 log=OK fwd=OK |
| A3 | excess re-derived via independent SQL baseline (300-token sample) | PASS | BIGTIME: sql_excess=+0.1731 export=+0.1731 (OK) n_tokens=185; HYPE: sql_excess=-0.6649 export=-0.6650 (OK) n_tokens=185; ALGO: sql_excess=-0.2242 export=-0.2242 (OK) n_tokens=183 |
| A4 | live-book WR/net second SQL + pnl_usdt/pnl_pct sign consistency | PASS | LONG: n=729 WR=46.4% net=-6.89 sign_consistent=716/729 (mismatches = $0.00 scratches); SHORT: n=318 WR=48.7% net=-1.71 sign_consistent=312/318 (mismatches = $0.00 scratches) |
| A5 | no duplicate (gate,token,dir,10min) in events export | PASS | duplicates=0 / 81707 rows |
| A6 | big-miss MFE values vs raw candles | PASS | ICP: recomputed=13.91 export=13.91 OK; CASHCAT: recomputed=10.21 export=10.21 OK; CHIP: recomputed=10.56 export=10.56 OK; FOGO: recomputed=17.15 export=17.15 OK |

**Overall: 6/6 PASS — ALL CHECKS PASSED**
