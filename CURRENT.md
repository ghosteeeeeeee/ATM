# Current State — brain_auditor #137 2026-10-25 10:40 UTC
**Last Updated: 2026-10-25 10:40 UTC**
**Updated by: brain_auditor #137. Prior: #136 09:45 + correction 10:05 (preserved in git history).**

## HEADLINE #137 — 2 STEER/DRIFT ITEMS CLOSED WITH EVIDENCE; 1 OBSERVABILITY SHIP
1. **Watchdog recommendation #5 ("which entry path skips `_signal_metadata`") = ALREADY FIXED, cohort is STALE.**
   brain.py entry-metadata backfill (#117, 2026-10-24) is live: **0 trades opened after 2026-10-24 carry a
   NULL `rsi_14`**, backfill marker present on the 2 fills that needed it. The flagged "12 LONGs NULL meta_rsi
   16.7% = worst band" rows are all **Oct 18–23, i.e. pre-ship**, and 10/12 are BTC `ai-trader-manual/pending`
   (CEO-domain). → **CLOSED, no new code owed.**
2. **Recurring Sunday 03:00 `Self-healing test: FAIL` (3rd occurrence) = TRIAGED TODAY by health_monitor**
   (commit `83f99f71`): `dispatcher/dispatcher.py` absent since Sep 1 + `hermes-better-coder.service` disabled
   → SKIP branch for parked subsystem. **Verify the SKIP prints at the next run (Sun Nov 1 03:00).**
3. **SHIP: `profit_monster.py:489` `[TRAIL] … activated` line now carries `trade_id={tid}`** (zero-behavior,
   py_compile PASS, legacy+new-line parse self-check PASS). Closes the `pm_activation_coverage` disclosure
   (≤0.4pp token-window over-credit from 1 overlapping same-token pair) for the uncovered-n≥20 re-eval.
   **Diff confined to lines 486–494 — the spider-tier veto block (517–523) is byte-untouched, its one-line
   revert story is unchanged.** Correct-by-traffic until a trade arms.

## CREATIVE (mandate) — EMA300 TRANSITION GATE MEASURED THEN REJECTED-WITH-DATA
BTC 1m `continuum_states`, ≥100-close streak transitions, 30d: **100 reclaims + 87 loses ≈ 6 events/day**
(p50 streak 6 / p90 122 → the ≥100 threshold does not isolate rare events). Forward 4h: reclaim mean
**−0.054%** (46/100 pos), lose mean **−0.096%** (35/87 pos) = no edge; our own post-event trades
reclaim-LONG n=253 44.3% `+1.73` / lose-SHORT n=97 46.4% `+0.03` = wash. Consistent with #61
(`ema300_position` bands rejected, p>0.05 every window). **Logged closed — do not re-propose.**

## LOSING AUTOPSY 48h — WRONG-SIDE REFUTED 61st CONSECUTIVE RUN
Adverse-first `recovery_replay.py` (selfcheck PASS): **24h n=4 = 2 never-adverse / 2 recovered / 0 NEVER** ·
**48h n=13 = 3 / 5 / 5**. NEVER = ALT `−0.17` / CC `−0.15` / ZRO `−0.11` `volume-buildup-` shorts (structural
never-recover class) + BTC pending `−0.08` + PUMP r2v2 `−0.01` — all tiny. 0 new patterns.
Valid refs: #61 p=0.116, #84 t=−0.04. Winning side = flat.

## WATCHDOG TRIAGE (10:14 cycle)
**0 steers, 0 open, health good = CORRECT.** Regime = **THAWING**: regime_5m aggregate 113 SHORT → 0 SHORT
(09:30→10:15) while BTC still under 1m EMA300 (566 closes, gap −0.16%), vol LOW, 15m+4h scanners SHORT_BIAS —
sources disagree = chop, so flat book is the right posture. Mid-band LONG steer condition still holds (z≈1.99
confounded — not escalated, per the watchdog's own caution). Structural non-participation (100 blocked / 99
single-type shorts) — the short-gate loosening review **due today was already run and CLOSED** (#129
SLOPE-FILTER `+0.98` fails bar; #76 pre-reg candidates all fail).

## SHADOW SOURCES (verified this run)
| source | rows | status | answerable |
|---|---|---|---|
| contrarian_shadow + outcome join | 808 / 536 joinable | ✅ re-ran this run | pump-chain- flip **64.0% n=339** (Oct-27 PROMOTE stands); btc-pump-rider+ 25% = do NOT flip |
| floor_admit join | **644 ep** | ✅ join SHIPPED #132, selfcheck PASS | floor_only 48.2% vs always_admit 38.2%, p=0.126 → **COLLECT to Nov-15** |
| oscillator_shadow | 24,598 JSONL | 🧊 frozen by design, `actual_outcome` null on all | none |
| wyckoff_shadow | 304 | ⏳ no outcome column | none |
| rr_shadow_audit_7d | dict, mtime 21.4d | ☠️ orphaned | none |

`shadow_trader --report`: 20,404 signals; gates healthy (CONFLUENCE-EXPIRY 10,310 blocked, would_win 48%,
avg −0.12); exit A/B pm_trail `+2,803` vs hard_max `−4,407`.

## CEO STACK
1. **UNIVERSAL POST-ARM TRAIL FLOOR D=0.20 GO** — escalation #17 measurement complete (#136 bypass `+2.368`
   30d p=0.019 ALL bars; PM control `+0.276` = no PM change; pm_elig COLLECT). Shadow-line ship vehicle.
2. pump-chain+ NO-KILL (30d `+1.84`, kill MET-by-letter) → CONF_FLOOR fkA 41.7% ruling → pump-chain TAT
   BASE-vs-VARIANT-C
3. **VETO WINDOW on the spider tier fix** (revert = `profit_monster.py:517-523`, one line — unchanged by #137)
4. UGB-BE pending (PT subsumes) · Oct-27 contrarian PROMOTE + coin_regime n≥50 + mid-band dampen re-measure
5. Nov-15 floor_admit 30d same-sign (644ep)

## NUMBERS (PG this run)
24h **14T 10W 71.4% `+$0.72` GREEN** (LONG 9T 6W `+0.41` / SHORT 5T 4W `+0.31`) | 7d 123T 43.9% `−$0.57`
| 30d 689T 43.8% `−$2.10`
14d **ARMED(mfe≥0.40) 157T 110W `+$9.17` vs UNARMED 163T 10W `−$12.89`**
14d exits: **TRAIL 111T 98W `+$9.24`** vs **HML 68T 0W `−$6.60`** + other `−$6.16`
7d exits: **PM-trail 43T 38W `+$2.59`** vs stop-family (HML 15 + atr_sl 26 + stale 3 + hard_sl 4) **48T 0W `−$4.32`**
→ trend/chop law unchanged: the whole bleed is pre-arm (chop entries), not exits.

## SIGNAL QUALITY — 0 NEW TARGETS
sub-50% WR n≥15 14d: bb-bounce-v2-long+ 34T 41.2% `−1.01` (in flight) · ai-trader+ 23T (disabled) ·
doji-bottom-long 16T (killed Oct 16) · pump-chain+ 46T 28.3% (CEO NO-KILL) · pump-chain- 35T 22.9%
(Oct-27 PROMOTE) · ai-trader-pending 16T (CEO) · ai-trader-manual 15T `+0.34`. Every sufficient-n bleed
cohort is killed, disabled, in flight, or pre-registered to a dated ruling.

## LAST-RUN VERIFY (#134/#135/#136 + health_monitor) — ALL PASS
spider fix (post-fix floors sane, no negative-floor lines) · `trail_distance_oos --selfcheck` PASS ·
`pm_activation_coverage --selfcheck` PASS · `be_at_arm_replay --selfcheck` PASS ·
`floor_admit_outcome_join --selfcheck` PASS (644ep) · UGB-PT correct-by-traffic ·
**`hermes_constants.py` git diff EMPTY** · **CEO_PROTECTED_FLAGS 13/13** · **SIGNAL_REGISTRY 86 signals
bb_bounce present** · **size-reduce file absent = 1.0x** · **session lock absent** ·
**0 new uncaught Tracebacks 2026-10-25** (only the pre-fix 03:00 self-healing one) ·
`[TRAIL]` parse self-check (legacy + trade_id) PASS.

## NEXT ACTIONS
1. CEO ruling: **universal post-arm trail floor D=0.20** → v6 exit-stack, shadow line first
2. CEO veto window on the spider tier fix (one-line revert)
3. Oct 27: contrarian pump-chain- PROMOTE (64.0% n=339 OOS) + coin_regime n≥50 + mid-band dampen re-measure
4. PM activation-coverage re-eval at uncovered n≥20 (now 13) — joins now use the new `trade_id` field
5. Nov 1: confirm Sunday audit prints `Self-healing test: SKIP` (health_monitor fix)
6. bb-bounce-v2-long+ stays in flight — needs compactor co-signal stamp before bypass-removal can be measured
7. Nov-15: floor_admit 30d same-sign (644ep)
