# Self-Audit — Gate Usefulness Deep Dive 2026-11-19

Second computation path for every headline number. External auditors: refute or agree per check.

| Check | Description | Result | Detail |
|---|---|---|---|
| A1 | independent re-coalescing of events export matches summary | **FAIL** | CONFLUENCE-GATE-BLOCK: n MISMATCH(5661 vs 3425) mean OK; CONTINUUM-BLOCK: n MISMATCH(3574 vs 2816) mean OK; CONTINUUM-BULL: n MISMATCH(3063 vs 2362) mean OK; LONG-NEUTRAL: n MISMATCH(2689 vs 1784) mean OK ... |
| A2 | random events: log line exists (reparse prov) + independent fwd recompute | **FAIL** | IO/SHORT @11-11 08:49 log=MISSING fwd=OK; GMT/SHORT @10-14 02:21 log=n/a (db-only, raw deleted) fwd=MISMATCH; SUSHI/LONG @10-06 00:57 log=n/a (db-only, raw deleted) fwd=MISMATCH; GRASS/SHORT @11-16 12:05 log=MISSING fwd=OK; GRASS/SHORT @10-25 23:37 log=n/a (db-only, raw deleted) fwd=OK |
| A3 | excess re-derived via independent SQL baseline (300-token sample) | PASS | ICP: sql_excess=+0.5655 export=+0.5655 (OK) n_tokens=185; CHIP: sql_excess=-0.3658 export=-0.3658 (OK) n_tokens=185 |
| A4 | live-book WR/net second SQL + pnl_usdt/pnl_pct sign consistency | PASS | LONG: n=729 WR=46.4% net=-6.89 sign_consistent=716/729 (mismatches = $0.00 scratches); SHORT: n=318 WR=48.7% net=-1.71 sign_consistent=312/318 (mismatches = $0.00 scratches) |
| A5 | no duplicate (gate,token,dir,10min) in events export | PASS | duplicates=0 / 106357 rows |
| A6 | big-miss MFE values vs raw candles | PASS | ICP: recomputed=13.91 export=13.91 OK; CASHCAT: recomputed=10.21 export=10.21 OK; CHIP: recomputed=10.56 export=10.56 OK; FOGO: recomputed=17.15 export=17.15 OK |

**Overall: 4/6 PASS — 2 FAILURES REQUIRE CORRECTION**
