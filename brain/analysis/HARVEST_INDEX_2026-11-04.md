# HARVEST INDEX — goal-704ed65e evidence pack (2026-11-04)

T's mandate: harvest 6,356 closed trades + ~100k shadow events, figure out what works, ship it.
This index points at every artifact; the verifier is the single source of goal truth.

## Verifier (run every goal round — never claim, always run)
`python3 brain/analysis/goal_metrics_check.py` → 7 metrics vs CEO targets (rc=0 only when ALL pass)
Baseline round 4: **0/7 PASS** (jup 64%, HML 33/−$4.73, net24h −$0.95, net72h −$3.76, ratio 2.9:1, fleet WR 51.4%)

## Artifacts
| # | File | Headline |
|---|---|---|
| 1 | `fleet_net_30d_2026-11-03.md` | 19/22 signal cells net-negative; only winners = ai-trader-manual, pc- fade combo, r2v2-long3; fees $9.47 of −$17.07 net |
| 2 | `hml_decomposition_2026-11-03.md` | HML = 46% of ALL 30d losses (−$17.10/−$37.39); carriers pump-chain+ 21, jup 20; entries mid-band 45-60 (not extremes); metadata RSI coverage only 27% (data gap) |
| 3 | `hml_backstop_overlap_2026-11-04.md` | Units-guarded: 1.0% stop-tighten cap INERT vs −0.80% HML (115/150 cuts inside 1.0); 0.75% pre-empts 31/33 in-scope → CEO shipped 0.75+ENFORCE |
| 4 | `fade_dumptape_2026-11-04.md` | Fade LONGs on dump tape: n=12 +$0.32 7/12W — the "rebranding" is PROFITABLE on crashes; 11-10 decision pre-answered (KEEP) |

## CEO execution package (consult 20261104, verdict APPROVE)
SHIP LIVE: ① stop-tighten 1.0→0.75 + ENFORCE=True (HML fix) ② jup share cap 64%→<35%
③ LONG-bypass block in SHORT_BIAS (worst cell 94T −$0.65) ④ amplify bb-squeeze+/warrior-sr±
SHADOW: probe retune 0.80 (11-14), fade Z-FLIP (11-10), hl_copy re-filter (11-17)
REFUTED: "old winners phased out" (all kills data-backed; nothing to restore)
Execution agent: a98de02d (in flight at index time); then guardian restart + review + bug_hunter gates.

## Related standing items (registry 69+ entries)
- stop-tighten-enforce-eval (11-14) · rsi-ceiling-75-live revert rule (11-10) ·
  short-shadow-join-builder (11-16) · gate-shadow-dedup-convention (token-day dedup ALWAYS) ·
  long-bypass-regime-shadow (superseded to LIVE per CEO) · harvest-ship-2026-11-04 (metrics, 11-07)
