# Current State — brain_auditor Oct 21 2026-22:40 UTC

**Last Updated: 2026-10-21 22:40 UTC**
**Updated by: brain_auditor #63 — 0 trading-behavior changes (vacation soak). HEADLINE: pump-chain- kill recheck (due Oct 22) verdict pre-computed = CANCEL blanket kill — CONF_FLOOR=30 (ships Oct 23) captures 93% of the bare bleed (conf<30 9T −$0.53 of −$0.57) while kill would destroy all 8 winners +$1.27 to catch a −$0.04 wash residual; re-evaluate conf≥30 residual Oct 24 (then v6-requirement Option A, not kill). volume_spike<1.0 block REJECTED (holds 78% of winners); LONG volume_spike≥2.0 chase-dampen PRE-REGISTERED. rsi_drift/ARM-GAP/floor-45/doji/size-reduce all verified holding. Prior: brain_auditor #62 21:45.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** per `vacation_size_reduce.json` (file truth; live sizes $11.10/$22.10). Both resume legs still failing: 7d WR 35.8% AND PnL −$3.46 <0.
- **24h 39T 14W 35.9% −$1.09** — 25 losers, all shallow. **7d 162T 58W 35.8% −$3.46.**
- **7d ARMED 63T 74.6% +$3.48 vs UNARMED 99T 11.1% −6.94.** Exit family: TRAIL 48T 85.4% +$3.13 vs CHOP 114T 14.9% −$6.59. Wealth gap unchanged.
- **Regime: CHOP PIN** — BTC AT EMA300, 15m SHORT_BIAS vs 4h LONG_BIAS conflict, market_phase CALM, vol LOW. No directional edge at index level.
- **Open 0 (flat)** — correct posture. Portfolio health: critical (watchdog).
- **Vacation mode ACTIVE to Oct 23** — shadow-first, no constants changes, no signal enable/disable. Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #63 (2026-10-21 22:40 UTC)

**0 trading-behavior changes. 1 kill verdict (collision evidence), 1 pre-registration, 1 rejection with data.**

1. **HEADLINE — pump-chain- kill recheck verdict (due Oct 22), computed now with collision analysis:** paper criteria MET (bare 14d 37T 8W 21.6% −$0.57, 30d 117T −$1.19) **BUT** — conf≥30 residual = 28T 8W **−$0.04 wash** | **all 8 bare winners are conf≥30 (+$1.27)** | conf<30 portion 9T 0W −$0.53 = **93% of bleed, fully captured by CONF_FLOOR=30** (ships Oct 23) | all pump-chain SHORT conf≥30 = 35T 10W **+$0.26 positive** | combo v6-confirm 11T +$0.26. **Kill over floor = destroy +$1.27 winners to catch −$0.04. VERDICT: CANCEL blanket kill, ship CONF_FLOOR only.** Oct 24 residual recheck: if conf≥30 bare n≥20 ∧ PnL<0 ∧ WR<30% → v6-requirement gate (Option A), not kill. Confidence HIGH.
2. **WATCHDOG STEERS: 001 VERIFIED-KNOWN** (12/20 streak = chop family CHOP 22T −$1.73 vs TRAIL 17T +$0.64; portfolio already flat; scheduled Oct 23 ships address it) | **002 REFUTED-PARTIAL** (#61 opposite-side p=0.116 stands; STX wrong-side example now SQL-visible: coin_regime SHORT_BIAS conf 49 stamped on losing LONG r2v2-long4; COUNTER LONG cohort 17T 41.2% −$0.42 — flip criteria n≥20 ∧ WR<30% **not met**, monitor).
3. **LOSING AUTOPSY 25 losers → 0 new patterns:** conf<30 floor-admits ×6 (COMP/CRV/CFX SHORTs + pump-chain+ CFX,BLUR,INJ — covered Oct 23) | pump-chain+ TAT timeouts ×3 −$0.16 (mechanism containing) | counter-trend LONGs STX/PUMP/GRASS/INJ EXTREME | POL bb-bounce chop −$0.22 | SYRUP continuation+ stale_exit −$0.23 largest (n<20 watch) | BTC pending ×3 CEO | WLD 1-min atr_trail_hit = known false-peak class. **13/14 winners profit-monster-trail — exit sound, entry side is the cancer.**
4. **REJECTED-WITH-DATA: LONG volume_spike<1.0 block/dampen** — <1.0 is the DEFAULT state (214/268 14d LONGs) containing **79/101 = 78% of winners** → catastrophic winner-kill. Logged so never re-proposed. (volume_spike 1.0–2.0 is the only positive cell: 14d 24T 54% +$0.35 / 7d 13T 69% +$0.64 — suggestive, n small, no action.)
5. **PRE-REGISTERED: LONG volume_spike≥2.0 chase-dampen** — 14d 12T 33.3% −$0.55, 7d 6T −$0.31 (same sign both windows): entering after a ≥2x spike = chasing an extended move. Flip at 14d n≥20 ∧ PnL<0 ∧ WR<30% → 0.5x size proposal. Currently n=12, monitor.
6. **SIGNAL DEEP-DIVE: volume-breakout-long+** 14d 16T 18.8% −$0.76 but **30d 24T +$0.87 arm 8.3% → kill stays REJECTED** (same basis as Oct 20); 14d bleed = HIGH/EXTREME hard_max_loss 9T −$1.08 offset by stale_exit +$0.42, habitat n<20 → criteria-locked monitor (trigger only if 30d turns negative).
7. **LAST-RUN VERIFY all PASS** — rsi_drift stamp LIVE 1/1 (POL open 18:30, drift 8.14) | ARM-GAP LIVE (SOL 19:01:17 line; qualifying closes since = 1/1 = 100% capture) | floor-45 0 violations since 02:46 | pump-chain+ HIGH block 0 since 03:05 | **doji 0 opens since kill commit 2026-10-16 20:40** (10 closes in my coarse query were ALL pre-kill — NOT a leak) | size-reduce 0.5x | protected 13/13.

## PRIOR RUN #62 (2026-10-21 21:45 UTC, condensed)

**0 trading-behavior changes. 1 pre-registration, 2 rejections with data.**

1. WATCHDOG P3 SHORT 40-55 worst-cell COVERAGE DECOMPOSITION: 14/20 = pump-chain conf<30 (CONF_FLOOR ships Oct 23), 3 pre-Oct-16 non-pump (SHORT_MIDBAND covers), 3 residual wash → no new change.
2. PRE-REGISTERED pump-chain+ decay kill criteria (trigger at Oct 23; 14d +$0.96 = NOT met).
3. REJECTED: global conf<30 floor (96% of bleed is pump-chain, pump-scoped floor captures it) | LONG_RSI_SWEET_SPOT_BOOST demote (7d/14d/30d sign-flip instability).
4. rsi_drift + ARM-GAP stamps verified firing; pump-chain midband exemption comment drift re-verify stays Oct 23 schedule.

## OLDER RUNS (condensed)

- **#61 20:56** — watchdog wrong-side REFUTED (opposite-side audit p=0.116, 85% no opposing setup = chop); LONG×CALM + ema300-pin gates REJECTED-WITH-DATA; STANDALONE_BYPASS exemption = CEO decree not drift.
- **#60 17:45** — shipped rsi_detect/rsi_exec/rsi_drift stamp (decider_run.py:5019, zero-behavior). Staleness filter + blanket EXTREME block REJECTED-WITH-DATA.
- **daily_orchestrator 17:00** — fixed `$0` shell-expansion corruption (48 strings), size-reduce reporting file-truth, auto_1hr regime-based kill policy.
- **#59 16:39** — WLD #16341 MFE false-peak root-caused (round-number 0.60); peak-sanity shadow pre-registered (close-time tick census vehicle).

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)

- **pump-chain- kill — VERDICT #63: CANCEL blanket kill** (collision: CONF_FLOOR captures 93% of bleed; kill destroys 8 winners +$1.27 for −$0.04 residual). Final disposition with CEO eyeball Oct 23. Oct 24: conf≥30 residual recheck → v6-requirement Option A only if n≥20 ∧ PnL<0 ∧ WR<30%.
- **PUMP_CHAIN_CONF_FLOOR=30** — pump-chain conf<30 14d **40T 15.0% −$1.98**; blocks 6 winners +$0.64 = **net +$1.34** (fresh #63). Ships Oct 23. LIVE PROOF: CFX #16347 entered conf 29.5.
- **rsi_drift severity gate — criteria LOCKED #61:** n≥20 stamped AND would-block WR<30% AND would-keep WR>45% AND net save>$1.00 AND winner-kill<20%
- **Arm-rate size dampen — PRE-REGISTERED #61** (shadow at vacation-end): 0.5x size when 7d arm-rate <15% AND n≥10; flip only if shadow net-positive with 0 winner-kill
- **LONG volume_spike≥2.0 chase-dampen — PRE-REGISTERED #63:** flip at 14d n≥20 ∧ PnL<0 ∧ WR<30% → 0.5x proposal (now 12T −$0.55)
- **Opposite-side signal audit** — method validated; re-run at n≥200 losers + generation-time signal log if available
- **Peak-price sanity gate SHADOW** — close-time tick comparison is the only valid vehicle (WLD/ZRO false-peak class, bug_hunter P1)
- **coin_regime COUNTER 0.5x dampen** — flip at cell n≥20 with WR<30% (LONG cell n=17, SHORT n=5)
- **SHORT×EXTREME 0.5x size dampen shadow** (14d 59T 23.7% −$1.18) — correct shape; blanket EXTREME block rejected
- **r2v2-long4 kill criteria** — 14d 4T 0W −$0.27, n=4 <20: kill only if 14d n≥20 AND PnL<0 AND WR<30%
- **hmacd family kill-criteria** — 14d 12T −$0.65, n=12 <20, criteria locked
- **hl_copy_trader watch** — 14d 11T 27% −$0.20, n<20; CEO domain
- **stale_exit cohort watch** — SYRUP −$0.23 today, continuation+ 4T/24h −$0.18 n<20
- **pp-cond shadow flip** — failed bars, re-eval vacation-end
- **post-arm breakeven ratchet** — blocked on escalation #17 candle OOS
- **pump-chain+ decay kill criteria — PRE-REGISTERED #62:** trigger = 14d n≥20 ∧ PnL<0 ∧ WR<30% at Oct 23 → Option A to CEO; current 14d 61T +$0.97 = NOT met
- **volume-breakout-long+ habitat monitor #63:** trigger only if 30d turns negative (now +$0.87)
- **REJECTED (do not re-propose):** global conf<30 floor | LONG 55-60 boost demote | LONG volume_spike<1.0 block (78% winner-kill, #63) | LONG×CALM gate | ema300-pin gate | gap-band asymmetry
- **Escalation #17 (24th):** exit-ladder candle OOS — blocks ARM-GAP/peak-trail/post-arm flip

## BACKLOG / CEO DECISIONS PARKED

- **blacklist-tester.timer** — experiment concluded Aug 5 (0 KEEP/77), timer still fires; summarizer recommends disable → CEO call
- **logrotate for logs/** — disk 84% (19G free), pipeline.log 220M; health monitor watches 85% warn
- **15m/1h/4h candle retention** — only if disk tightens (2.9M rows reclaimable)
- Kanban "0.3x" text entries are historical drift; file (0.5x) is truth — new reports now file-truth
