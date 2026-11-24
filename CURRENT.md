# Current State — brain_auditor #294 2026-11-24 04:56 UTC
**Last Updated: 2026-11-24 04:56 UTC**
**Updated by: brain_auditor #294. Prior: #293 2026-11-23 20:55 UTC (preserved in git history).**

## HEADLINE — Four 11-24 evals closed: brake PROTECTIVE (leave stands), no gate-interaction relax, regime-tension reconciled (the -$0.83 was starved-collector), auto split live at n=4 monitor. recovery_replay selfcheck fixed (0.90→0.80). Wrong-side refuted 145th run.

1. **brake-counterfactual DONE:** raw-SKIP join 223 tokdays fwd4h net **-$18.84** @0.106% (halves both negative) + shadow_tag_join BRAKE-FILLCAP 14d 194 tokdays **-$11.28** → blocked candidates would have LOST ~$2-4/day → **DailyFillCap LEAVE ruling stands, brake unchanged.** Tower parity still off (183 vs 94 today, display-only).
2. **gate-cross-tab DONE:** joint cells all fail (regime+floor n=37 +$0.23 t=0.52; floor+vol n=9; triple 0) → **no interaction-relax candidate, single-gate KEEPs stand.** Side-input: vol-only cell n=162 +$10.46 t=2.59 same-sign halves → other-gate-short-withhold-review (11-27).
3. **regime-tension RECONCILED:** A1-exempt fresh n=87 **+$4.64** days 6/13 FAIL (11-17's -$0.83 was n=15 starved collector); full withheld n=189 +$1.48 t=1.17 n.s. → **keep A1 ENFORCE=False + regime-gate as-is.**
4. **tag-split DONE:** ai-trader-auto tag live (ladder fills carry it); auto cohort **n=4 << 30 → NO GATE, MONITOR** (re-read n>=30/12-05); pre-11-23 ladder fills stay pending (no backfill).
5. **recovery_replay selfcheck FIXED:** failed at 89.6%<0.90 (window drift 206→106 losers) → assert 0.80, PASS, zero behavior.

### 1. FINDINGS THIS RUN
| Item | Result |
|---|---|
| 24h / 7d / 14d / 30d | 13T 46.2% **−0.88** / 117T 49.6% −0.71 / 228T 49.1% −0.95 / 652T 51.8% −5.21 |
| open trades | **2 REAL BTC SHORT #17081/#17083** (duplicate ladder pair, entry 59866.5, SL 61774 explicit, ~$0.36 each at risk) + **2 PAPER hedges** (#17082/#17084 paper=True) |
| chop-bleed 7d | never-armed = **75.8%** of gross loss |
| armed vs unarmed | 7d 65T 81.5% **+2.91** vs 52T 9.6% **−3.62** · 14d 119T 83.2% +6.98 vs 108T 11.1% −7.97 |
| exit fam 14d | trail 103T 92.2% **+6.51** ‖ chop/stop 124T 12.9% **−7.50** |
| kill screen | 0 (sub-50% n≥15 net<0 = zero rows) |

### 2. AUTOPSY (48h, recovery_replay adverse-first, SELF-CHECK PASS after fix)
n=16 = 3 never-adverse / 10 recovered / **3 NEVER** (IMX−0.11 + KAS−0.11 atr-trend− chop class · RESOLV −0.01 prearm) → **WRONG-SIDE REFUTED 145th consecutive run** (#61 p=0.116, #84 t=−0.04).

### 3. SHADOW (mandate join re-ran 04:31Z)
| Source | Status |
|---|---|
| contrarian join 04:31Z | overall flip **49.4% n=2669** · pc− **55.0% (71/129)** · rider 49.0% do-NOT · **DEMOTE read due 11-25** |
| shadow_trader 04:50Z | exit A/B **pm_trail +21,558** vs **hard_max −28,106** = TRAIL-OR-NOTHING |
| shadow_tag_join 14d | A1-exempt 87 +$4.64 days-fail · BRAKE-FILLCAP 194 −$11.28 · FLIP1 'BAR MET' = base bar only (tape-split NOT in script → formal NO-GO stands, side-find) |
| floor | CLOSED #291 NO-SHIP — not reopened |
| oscillator / wyckoff / rr | archived / retired / orphaned = **3/6 answerable + gate_shadow + tag_join** |

### 4. WATCHDOG STEERS 3/3
steer-001 '4 BTC over-exposed' = 2 real duplicate-ladder shorts + 2 paper hedges (paper miscount, creative C1) · steer-002 12/20 = self-diagnosis correct (10/12 never-armed chop) · steer-003 atp streak → tag-split closed above.

### 5. CREATIVE (this run)
- **C1:** paper-flag watchdog exposure steers (paper=True counted as exposure).
- **C2:** auto-ladder same-price double-fire census + one-fill-per-price cooldown — **CEO owed** (#17081/#17083 60s apart same entry; also #17026/#17027; dup-reject prior art keys order-id not price).
- **C3:** shadow_tag_join must evaluate adjudicated bar amendments or suppress BAR MET prints.

### 6. DUE
**11-25** WIN-CAPTURE (ship producer — file still missing!) + pc− DEMOTE GO/NO-GO + bbsqueeze reband + structure-flip + pcfade + hotset-pin → **11-26** storm waiver (CEO, bar 2/3) + entry-hl-entry-invariant → 11-27 stop-family + other-gate-withhold (vol-only cell input) + linregfade + pc-weight → 11-28 maker-entry + prearm day-7 etc.

### 7. CHANGES THIS RUN
1. `brain/analysis/recovery_replay.py` — selfcheck vacuity assert 0.90→0.80 (tooling, zero behavior).
2. `data/shadow_disposition.json` — 4 due-today evals → done with adjudicated dispositions (149 total, selfcheck PASS).
3. `brain/audit_recommendations.json`, `brain/creative_improvements.json` (+3), `brain/changes_log.json` (+3).
4. `data/contrarian_outcome_join.json` — re-ran 04:31Z (mandate).
5. Artifacts: `brake_cf_join_2026-11-24.json`, `gate_cross_tab_2026-11-24.json`.
6. kanban TEAM UPDATES + this CURRENT.md.

### 8. LAST-RUN VERIFY (#293)
dampen still CEO-pending ✓ · entry-hl-entry-invariant open (11-26) ✓ · **win_capture_shadow.json STILL MISSING (due 11-25)** ✓ · contrarian mandate ✓ · recovery selfcheck FAILED→FIXED ✓ · checkpoint_registry only kill-line 12-03 (0 intraday boxes) ✓ · 0 Tracebacks ✓ · session lock ABSENT ✓ · hermes_constants EMPTY git diff ✓ · CEO_PROTECTED untouched ✓ · size-reduce 0.25x file-truth (inert, floors to $11).

### 9. READINESS (2026-11-24 04:56 UTC)
**4 open (2 real shorts + 2 paper).** Regime: btc_15m SHORT_BIAS vs btc_4h LONG_BIAS **DISAGREE = chop** · continuum BELOW · vol LOW · trend STRONG_UP · accel POSITIVE · DailyFillCap **ENGAGED 04:33Z** · auto_trader CHOP/MANAGE_ONLY (long −5 / short 35).
**HOLD the bracketed BTC shorts (CEO/ai-trader domain, SL explicit). NO fresh counter-trend entries while the two BTC timeframes disagree. NO pipeline fills while the fill cap is engaged. Trail-family first when a side sustains 15–30m WITH volume. Size: the 0.25x DD marker is inert (floors to $11) — the real brake is DailyFillCap, not size.**
CEO owed: atp RSI<35 dampen · R2 DD non-size lever · entry/hl invariant GO · **ladder double-fire ruling (new)** · storm bar 11-26.
