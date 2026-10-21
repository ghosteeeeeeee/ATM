# Current State — brain_auditor Oct 21 2026-21:45 UTC

**Last Updated: 2026-10-21 21:45 UTC**
**Updated by: brain_auditor #62 — 0 trading-behavior changes (vacation soak). Watchdog P3 worst-cell COVERAGE DECOMPOSITION: 14/20 of SHORT 40-55 bleed = pump-chain conf<30 (CONF_FLOOR ships Oct 23), residual after scheduled ships = wash → no new change. pump-chain+ decay criteria PRE-REGISTERED (14d window still +$0.96 = kill not met). 2 rejections with data (global conf floor, 55-60 boost demote). rsi_drift + ARM-GAP stamps verified firing. Prior: brain_auditor #61 20:56.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** per `vacation_size_reduce.json` (file truth; live sizes $11.10/$22.10). Both resume legs still failing: 7d WR 36.0% AND PnL −$3.48 <0.
- **24h 41T 15W 36.6% −$1.03** — 25 losers, max single loss −$0.23 (shallow). **7d 164T 59W 36.0% −$3.48.**
- **7d ARMED 63T 74.6% +$3.48 vs UNARMED 100T 11.0% −$7.00** (30d: armed 296T +$20.23 vs unarmed 438T −$29.04). Wealth gap unchanged.
- **Regime: CHOP PIN** — BTC AT EMA300 ~150m, 15m SHORT_BIAS vs 4h LONG_BIAS conflict, market_phase CALM, vol NORMAL, trend_quality STRONG_UP (4h residue). No directional edge at index level.
- **Open 0 (flat)** — correct posture until the EMA300 pin resolves. Portfolio health: critical.
- **Vacation mode ACTIVE to Oct 23** — shadow-first, no constants changes, no signal enable/disable. Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #62 (2026-10-21 21:45 UTC)

**0 trading-behavior changes. 1 pre-registration, 2 rejections with data.**

1. **WATCHDOG P3 (SHORT 40-55 worst cell, n=20 p=0.003) COVERAGE DECOMPOSITION — new measurement:** 14T −$0.58 = pump-chain conf<30 (covered by CONF_FLOOR=30 Oct 23) | 3T −$0.34 = pre-Oct-16 non-pump (SHORT_MIDBAND block now covers non-pump 45-55) | 3T −$0.07 = conf≥30 pump residual (wash n=3). ETH rsi 40.7 = pre-revert/exec-drift (stamp now covers). **Residual after Oct 22/23 ships ≈ wash → NO new change needed; scheduled ships cover the worst cell.**
2. **PRE-REGISTERED: pump-chain+ decay kill criteria** (watchdog P2): trigger = 14d n≥20 ∧ PnL<0 ∧ WR<30% at Oct 23 → Option A (HIGH/EXTREME habitat gate or 0.7x demote) to CEO. Currently 7d 21T 19% −$0.26 / 24h 6T 0W −$0.32 but 14d 54T +$0.96 = kill NOT met (rejected 7 prior times on positive 14d). Criteria locked BEFORE window flips.
3. **REJECTED-WITH-DATA: global conf<30 floor** — non-pump conf<30 14d 11T 6W −$0.10 / 7d 6T −$0.02 = wash; 96% of conf<30 bleed (−$1.98 of −$2.08) is pump-chain, pump-scoped floor captures it. Logged so not re-proposed.
4. **REJECTED-WITH-DATA: LONG_RSI_SWEET_SPOT_BOOST demote** — 55-60 band 7d −$0.96 / 14d −$0.08 / 30d +$1.13 = sign-flip temporal instability (same class as rejected staleness filter); 30d t=2.20 evidence wins. Boost stays 10.
5. **LAST-RUN VERIFY all PASS** — rsi_drift stamp LIVE 1/1 (POL drift 8.14) | ARM-GAP LIVE (19:01:17 SOL line, 100% capture, 0 ERROR) | floor-45 0 violations since 02:46 | pump-chain+ HIGH block 0 since 03:05 | doji 0 since Oct 16 | size-reduce 0.5x | protected 13/13.
6. **LOSING AUTOPSY 25 losers → 0 new patterns:** conf<30 floor-admits ×6 −$0.42 (ships Oct 23) | pump-chain+ TAT ×3 −$0.16 contained | coin_regime COUNTER longs (POL/MET/PUMP/STX/NEO, collecting n=17<20) | BTC pendings ×3 CEO | SYRUP stale_exit n<20 | SOL unarmed MFE 0.97 = ARM-GAP logged. 13/14 winners profit-monster-trail.
7. **DRIFT CHECK: pump-chain midband exemption** (decider_run.py:2114) cites dead "+$0.42 pocket", fresh 7d 17T −$0.65 — but 14/17 is conf<30 covered by Oct 23 floor; residual wash → re-verify stays on Oct 23 schedule (run #48 pre-reg), no acceleration.

## PRIOR RUN #61 (2026-10-21 20:56 UTC, condensed)

**0 trading-behavior changes. All candidate gates failed verification bars.**

1. **WATCHDOG steer-002 "wrong-side trades" REFUTED (new measurement).** Opposite-side signal existence audit: for each trade, was there an OPPOSITE-direction signal in `signals_hermes_runtime.signals` within ±10m of open? **7d losers 16/104 = 15.4% | winners 4/58 = 6.9% | z=1.57 p=0.116 NOT significant.** 85% of losers had NO opposing setup anywhere in the roster → we are not on the wrong side of a signaled move, there is no other side → **chop, stay flat** (not flip direction). Caveat: table is 8581/8650 EXPIRED roster rows; generation-time blocks never insert → opposing setups undercounted. Directional evidence only.
2. **REJECTED-WITH-DATA: LONG × market_phase CALM gate** — 7d 11/37=29.7% −$1.78 vs other-LONG 37/84=44.0% −$0.54 **p=0.069** | 14d p=0.128 | 30d p=0.139. Negative direction consistent at all 3 windows but **p>0.05 everywhere** AND winner-kill 11/48 = **22.9% > 20% bar**. Logged so it is not re-proposed.
3. **REJECTED-WITH-DATA: ema300_position chop-pin gate** — 14d at open: ABOVE 141T 36.9% −$2.19 / AT 137T 37.2% −$1.18 / BELOW 78T 30.8% −$0.66. All three lose, WR ranges overlap → pin position is not the variable; chop entries are.
4. **VERIFIED NOT-DRIFT: STANDALONE_BYPASS × chop_detector exemption** — `signal_compactor.py:1427` exempts 144 bypass signals; comment cites **CEO 2026-10-01 decree** ("proven edge, explicitly allowed to fire solo"). Intentional. Not reported as a bug.
5. **LAST-RUN VERIFY: all PASS** — rsi_drift stamp **LIVE** (1 stamp: POL #16349 detect 53.62 → exec 61.76 drift 8.14, lost −0.22, coin_regime SHORT_BIAS conf 8) | ARM-GAP **LIVE** (`[ARM-GAP] SOL LONG MFE=0.97% trail=FALSE exit=atr_sl_hit pnl=-1.23% peakTrail@0.3%=+0.66% trade=16346`, 1 qualifying close / 1 line = 100% capture, 0 ERROR) | SHORT floor-45 (2 SHORT opens since 02:46, 0 violations) | doji (0 opens since kill) | pump-chain+ HIGH block (0 opens since 03:05) | size-reduce 0.5x | protected 13/13.
6. **LOSING AUTOPSY 25 losers → 0 new patterns.** Cohorts: pump-chain+ TAT timeouts ×3 (−$0.16, contained), conf<30 floor-admits ×5 (−$0.34), EXTREME chop longs ×6 (−$0.54), BTC ai-trader-pending ×3 (CEO domain), SYRUP stale_exit (n<20). All shallow.
7. **coin_regime counterfactual: HOLD COLLECTING** — 14d stamped n=48: ALIGNED LONG 22T 45.5% +$0.24 | COUNTER LONG 17T 41.2% −$0.42 | ALIGNED SHORT 4T | COUNTER SHORT 5T. Pre-reg criteria (cell n≥20 AND WR<30%) **not met**.

## OLDER RUNS (condensed)

- **#60 17:45** — shipped rsi_detect/rsi_exec/rsi_drift stamp (decider_run.py:5019, zero-behavior). Staleness filter + blanket EXTREME block both REJECTED-WITH-DATA.
- **daily_orchestrator 17:00** — fixed `$0` shell-expansion corruption (48 strings), size-reduce reporting drift (prompts now file-truth), auto_1hr blanket-kill instruction replaced with regime-based kill policy.
- **#59 16:39** — WLD #16341 MFE false-peak root-caused (round-number 0.60, zero supporting ticks → false trail arm → premature exit); peak-sanity shadow pre-registered (close-time tick census is the only valid vehicle).

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)

- **pump-chain- kill recheck Oct 22 (TOMORROW)** — bare 14d **37T 21.6% −$0.57 arm 21.6%** still MET; combo 11T +$0.26; bare vs combo arm gap = confirmation premium (structural case for Option A v6-requirement gate)
- **PUMP_CHAIN_CONF_FLOOR=30** — pump-chain conf<30 14d **40T 15.0% −$1.98**; blocks 6 winners +$0.64 = **net +$1.34** (fresh). Ships Oct 23. LIVE PROOF: CFX #16347 entered conf 29.5.
- **rsi_drift severity gate — criteria LOCKED #61** (before data): n≥20 stamped AND would-block WR<30% AND would-keep WR>45% AND net save>$1.00 AND winner-kill<20%
- **Arm-rate size dampen — PRE-REGISTERED #61** (shadow at vacation-end): 0.5x size when 7d arm-rate <15% AND n≥10; flip only if shadow net-positive with 0 winner-kill
- **Opposite-side signal audit** — method validated; re-run at n≥200 losers + generation-time signal log if available
- **Peak-price sanity gate SHADOW** — DB-only census FAILED; close-time tick comparison is the only valid vehicle (WLD/ZRO false-peak class, bug_hunter P1)
- **coin_regime COUNTER 0.5x dampen** — flip at cell n≥20 with WR<30% (LONG cell n=17, SHORT n=5)
- **SHORT×EXTREME 0.5x size dampen shadow** (14d 59T 23.7% −$1.18) — correct shape; blanket EXTREME block rejected
- **r2v2-long4 kill criteria** — 14d 4T 0W −$0.27, n=4 <20: kill only if 14d n≥20 AND PnL<0 AND WR<30%
- **hmacd family kill-criteria** — 14d 13T −$0.79, n=13 <20, criteria locked
- **hl_copy_trader watch** — 14d 12T 25% −$0.24, n<20; CEO domain
- **stale_exit cohort watch** — 3T/7d −$0.62 0%; SYRUP −$0.23 today
- **pp-cond shadow flip** — failed bars, re-eval vacation-end
- **post-arm breakeven ratchet** — blocked on escalation #17 candle OOS
- **pump-chain+ decay kill criteria — PRE-REGISTERED #62:** trigger = 14d n≥20 ∧ PnL<0 ∧ WR<30% at Oct 23 recheck → Option A (HIGH/EXTREME habitat gate or 0.7x demote) to CEO; current 7d 21T 19% −$0.26 / 14d +$0.96 = NOT met
- **REJECTED #62 (do not re-propose):** global conf<30 floor (non-pump wash 11T −$0.10/14d) | LONG 55-60 sweet-spot boost demote (7d/14d/30d sign-flip instability)
- **Escalation #17 (24th):** exit-ladder candle OOS — blocks ARM-GAP/peak-trail/post-arm flip

## BACKLOG / CEO DECISIONS PARKED

- **blacklist-tester.timer** — experiment concluded Aug 5 (0 KEEP/77), timer still fires; summarizer recommends disable → CEO call
- **logrotate for logs/** — disk 84% (19G free), pipeline.log 220M; health monitor watches 85% warn
- **15m/1h/4h candle retention** — only if disk tightens (2.9M rows reclaimable)
- Kanban "0.3x" text entries are historical drift; file (0.5x) is truth — new reports now file-truth
