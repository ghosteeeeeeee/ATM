# Current State — brain_auditor Oct 22 2026-00:30 UTC

**Last Updated: 2026-10-22 00:30 UTC**
**Updated by: brain_auditor #65 — 0 trading-behavior changes (vacation soak day -2). HEADLINE: watchdog 65+ LONG-band handoff REJECTED-WITH-DATA — "only profitable band +$1.37/60%" is a 7d artifact: 14d 68T 33.8% −$0.20 / 30d 131T 40.5% −$0.87, sign flips both OOS windows (volume-breakout-long+ 10T 0W −$1.14 + pump-chain+ 21T 6W −$0.25 drag). No momentum-continuation signal ships on a false premise. LONG 45-55 death-band block re-REJECTED (z=−0.88 p>0.05, fk 19.8–27.1%). pump-chain− kill recheck (pre-reg date today): CANCELLED CONFIRMED (CONF_FLOOR captures 93% of bleed; kill destroys +$1.27 winners for −$0.04 residual). CONF_FLOOR=30 FINAL PRE-SHIP VERIFIED: PASS (would-block 40T 6W −$1.98, net save +$1.61, fk 6.3% of winners) — ships Oct 23 with CEO eyeball. Prior: brain_auditor #64 23:45.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** per `vacation_size_reduce.json` (file truth; live sizes $11.10/$22.10). Both resume legs still failing: 7d WR 36.3% AND PnL −$3.39 <0.
- **24h 35T 13W 37.1% −$0.99** — 22 losers, all shallow (max −$0.23). **7d 160T 58W 36.3% −$3.39.**
- **7d ARMED 63T 74.6% +$3.48 vs UNARMED 97T 11.3% −$6.87.** Exit family: atr_sl_hit 49T 1W −$3.45 + hard_max_loss 22T 0W −$2.65 = pre-trail death core; profit-monster-trail 37T 33W +$1.68. Wealth gap unchanged. 13/13 24h winners profit-monster-trail.
- **Regime: bear-leaning / LOW volume** — BTC below EMA300 ~84,600, continuum BELOW, acceleration POSITIVE (reclaim attempt plausible). 0 open = correct posture. Portfolio health: critical (watchdog).
- **Vacation mode ACTIVE to Oct 23** — shadow-first, no constants changes, no signal enable/disable. Protected flags 13/13 INTACT.
- **READINESS: when BTC reclaims EMA300 ~84,600 WITH volume → continuum-trend+ LONG (4/5 7d, 80% arm rate) is the setup. Signals ready, no config change needed.**

## THIS RUN — brain_auditor #65 (2026-10-22 00:30 UTC)

**0 trading-behavior changes. 1 watchdog handoff refuted, 1 kill recheck closed, 1 pre-ship verification passed.**

1. **HEADLINE — watchdog 65+ LONG band handoff REJECTED-WITH-DATA.** Watchdog deep_analysis: "entry signals cluster at RSI 45-60 (bleed band) — the profitable 65+ LONG band... needs a momentum-continuation entry path." Fresh PG rsi_14 bands: 7d 15T 60% **+$1.37** BUT 14d 68T 33.8% **−$0.20** AND 30d 131T 40.5% **−$0.87** — sign flips positive→negative at both OOS windows. Top 65+ drag: volume-breakout-long+ 10T 0W −$1.14, pump-chain+ 21T 6W −$0.25. Building a new signal family on a 7d artifact repeats the 2026-10-08 pattern-fail trap. **No momentum-continuation signal ships.** (Only 30d positive LONG band: 55-65 +$1.15/52% n=150 — but 7d −$1.13 / 14d −$0.70 sign-flip = also unstable, no band gate ships.)
2. **LONG 45-55 death-band hard block RE-REJECTED (fresh data).** Band negative all 3 windows (7d −$1.88 / 14d −$0.88 / 30d −$1.35) BUT band-vs-rest WR z=−0.88 p>0.05, fk 19.8–27.1% (>20% bar), and pump-chain+ carries +$1.10 of the 14d band. Death-zone ADVISORY already live at correct weight. No hard block.
3. **pump-chain− kill recheck (pre-reg date TODAY): CANCELLED CONFIRMED.** Paper criteria still MET (bare 14d 37T 8W 21.6% −$0.57) but CONF_FLOOR=30 captures 93% of bleed (conf<30 9T 0W −$0.53); all 8 bare winners conf≥30 (+$1.27); conf≥30 residual = wash (−$0.04). Kill destroys +$1.27 to catch −$0.04. Ship CONF_FLOOR only. Other kills all NOT MET: pump-chain+ 14d 54T +$0.96 | r2v2-long4 n=4 | hmacd n=13 | volume_spike≥2.0 n=12.
4. **CONF_FLOOR=30 FINAL PRE-SHIP VERIFICATION: PASS (ships Oct 23).** Would-block 14d: 40T 6W −$1.98 (pump-chain+ 23T −$1.28 | pump-chain− 9T −$0.53 | combo 7T −$0.12 | v6− 1T −$0.05). Winner-kill 6 × +$0.37 = 6.3% of 14d pump-chain winners (under 20% bar). **Net save +$1.61.** 7d consistent (31T 3W −$1.98). Scope leak small (conf<30 non-pump −$0.28, covered by other pre-regs). Code NOT yet staged — stage tomorrow with CEO eyeball.
5. **LOSING AUTOPSY 24h: 22 losers → 0 new patterns.** conf<30 floor-admits ×6 −$0.42 (Oct 23) | EXTREME drift LONGs ×4 −$0.40 (STX/INJ/PUMP/GRASS) | POL bb-bounce chop −$0.22 (rsi_drift stamp fired: detect 53.62→exec 61.76, drift 8.14) | SYRUP continuation+ stale_exit −$0.23 (n<20 watch) | BTC ai-trader-pending ×3 −$0.18 (CEO domain, ATR-SL pre-reg Oct 26) | WLD 41s false-peak (known). 13/13 winners profit-monster-trail — exit sound, entry side is the cancer.
6. **ARM-RATE WATCH 7d (never-arm families):** hl_copy_trader 0/6 | ai-trader-pending 0/9 | pump-chain− bare 0/10 −$0.58 | ai-trader-manual 1/13. Combo confirms edge: pump-chain−,v6− 3/9 arm +$0.31. Best arm: continuum-trend+ 4/5 80%.
7. **LAST-RUN VERIFY all PASS** — rsi_drift stamp LIVE 1/1 (POL #16349 rsi_detect=53.62 rsi_exec=61.76 drift=8.14 — only trade since ship) | ARM-GAP code live position_manager.py:1314–1341 | floor-45 0 violations since 2026-10-21 02:46 | doji 0 opens since kill 2026-10-16 20:40 | size-reduce 0.5x file truth | protected **13/13** (PM_TRAIL_ACTIVATE_PCT=0.004, PM_TRAIL_DISTANCE_PCT=0.002).

## PRIOR RUN #64 (2026-10-21 23:45 UTC, condensed)

**0 trading-behavior changes. Watchdog handoff items 1+2 closed with data (both REJECTED), 1 pre-registration, 1 drift flag.**

1. **HEADLINE — WATCHDOG HANDOFF ANSWERED: stop-width vs ATR has NO causal effect on WR.** Bucket ALL 7d trades by SL/ATR regardless of outcome: <1x 27T 37% −$0.10 | 1–1.5x 29T 28% −$1.07 | 1.5–2x 14T 36% −$0.56 | ≥2x 89T 37% −$1.83. 14d narrow<1.5 (110T 38W 34.5%) vs wide≥1.5 (238T 86W 36.1%): **z=−0.29 p=0.774.** The handoff's premise (atr_sl_hit avg SL 1.85×ATR vs winners 2.97×ATR) is **selection-on-outcome** — a stop can only be hit if it is near; same trap as the 2026-10-08 failed analyses. Widening stops would not raise WR, only loss size. **No stop-width change.**
2. **HANDOFF ITEM 2 — exposure cap REJECTED-WITH-DATA.** Concurrent same-direction opens 7d: conc≤2 106T 38.7% −$1.09 vs conc≥3 54T 29.6% −$2.30, **z=−1.13 p=0.258.** And the 19:00 cluster structurally defeats an open-window cap: BTC 15:06 / NEO 16:42 / SOL 17:14 / POL 18:30 opened across **3.5 hours**, all stopped within **120 seconds** (18:59–19:01) by one BTC candle = −$0.33 = 56% of the day's loss. A concurrent-position cap is the only shape that could catch it, and it fails significance at n=54. Monitor only.
3. **pump-chain+ confidence edge measured — CONF_FLOOR=30 validated, RAISE REJECTED.** 30d conf<70 39T 17.9% −$1.74 vs conf≥70 42T 47.6% +$2.75 = **p=0.0046 significant**, but the conf<30 portion is exactly what CONF_FLOOR=30 (ships Oct 23) captures. The 30→70 increment is **sign-unstable**: 7d 4T −$0.18 / 14d 11T **+$0.24** / 30d 16T −$0.46. Ship the floor at 30 only; residual 30–70 stays on the Oct 24 schedule.
4. **LOSING AUTOPSY 24h: 24 losers → 0 new patterns.** conf<30 floor-admits ×6 (CFX 29.5, INJ 29.5, pump-chain-v6- 22.5/27.7, pump-chain+ 27/29.5) −$0.37 = covered Oct 23 | pump-chain+ 5T 0W −$0.32 | TAT timeouts ×3 −$0.16 (containing) | counter-trend LONGs STX/PUMP/GRASS/INJ | POL bb-bounce chop | SYRUP continuation+ stale_exit −$0.23 (n<20) | WLD 41s false-peak class. **13/14 winners profit-monster-trail — exit sound, entry side is the cancer.**
5. **CREATIVE / PRE-REGISTERED: ai-trader-pending ATR-scaled stop.** Sole emitter while AI_TRADER_ENABLED=False (watchdog pending path, has --sl/--target, respects kill switch): 9 BTC trades since Oct 19, **1W 8L −$0.28, 0/9 reached +0.40% arm (avg MFE 0.156)**, SL 0.113–0.300% vs BTC 15m ATR 0.145–0.293% → **SL/ATR 0.72–2.07 (avg 1.49) = stops inside one 15m candle's noise.** R:R ranged 0.77–8.13 with no relation to outcome (sole winner had the worst R:R 0.77, n=1 no conclusion). n=9 <20 → **recheck Oct 26** (~3/day); flip proposal only if n≥20 ∧ armed-rate <20% ∧ PnL<0 ∧ SL≥2×ATR does not inflate avg loss >50%. CEO domain (CEO arms these).
6. **DRIFT FLAG (low, no change):** `MIN_EXEC_CONFIDENCE = 40` hardcoded at decider_run.py:3442 — CEO's 2026-10-10 50→40 floor lives outside hermes_constants.py, so it never appears in the constants diff/audit trail. Refactor candidate for post-vacation.
7. **LAST-RUN VERIFY all PASS** — rsi_drift stamp LIVE 1/1 (POL #16349 open 18:30 drift 8.14; only 1 trade opened since ship = low traffic not a gap) | ARM-GAP code live position_manager.py:1314–1341 | floor-45 0 violations since 02:46 | doji 0 opens since kill 2026-10-16 20:40 | size-reduce 0.5x file truth | protected **13/13** (PM_TRAIL_ACTIVATE_PCT=0.004, PM_TRAIL_DISTANCE_PCT=0.002).

## PRIOR RUN #63 (2026-10-21 22:40 UTC, condensed)

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
- **PUMP_CHAIN_CONF_FLOOR=30 — PRE-SHIP VERIFIED #65 (PASS, ships Oct 23 CEO eyeball):** would-block 14d 40T 6W −$1.98 | winner-kill 6 × +$0.37 = 6.3% of pump-chain winners (under 20% bar) | **net save +$1.61** | 7d consistent 31T 3W −$1.98 | scope leak small (conf<30 non-pump −$0.28, covered elsewhere). Code NOT yet staged — stage Oct 23. LIVE PROOF: CFX #16347 entered conf 29.5.
- **rsi_drift severity gate — criteria LOCKED #61:** n≥20 stamped AND would-block WR<30% AND would-keep WR>45% AND net save>$1.00 AND winner-kill<20%
- **Arm-rate size dampen — PRE-REGISTERED #61** (shadow at vacation-end): 0.5x size when 7d arm-rate <15% AND n≥10; flip only if shadow net-positive with 0 winner-kill
- **LONG volume_spike≥2.0 chase-dampen — PRE-REGISTERED #63:** flip at 14d n≥20 ∧ PnL<0 ∧ WR<30% → 0.5x proposal (now 12T −$0.55)
- **Opposite-side signal audit** — method validated; re-run at n≥200 losers + generation-time signal log if available
- **Peak-price sanity gate SHADOW** — close-time tick comparison is the only valid vehicle (WLD/ZRO false-peak class, bug_hunter P1)
- **coin_regime COUNTER 0.5x dampen** — flip at cell n≥20 with WR<30% (LONG cell n=17, SHORT n=5)
- **SHORT×EXTREME 0.5x size dampen shadow** (14d 59T 23.7% −$1.18) — correct shape; blanket EXTREME block rejected
- **r2v2-long4 kill criteria** — 14d 4T 0W −$0.27, n=4 <20: kill only if 14d n≥20 AND PnL<0 AND WR<30%
- **hmacd family kill-criteria** — 14d 13T −$0.79, n=13 <20, criteria locked
- **hl_copy_trader watch** — 14d 11T 27% −$0.20, n<20; CEO domain
- **stale_exit cohort watch** — SYRUP −$0.23 today, continuation+ 4T/24h −$0.18 n<20
- **pp-cond shadow flip** — failed bars, re-eval vacation-end
- **post-arm breakeven ratchet** — blocked on escalation #17 candle OOS
- **pump-chain+ decay kill criteria — PRE-REGISTERED #62:** trigger = 14d n≥20 ∧ PnL<0 ∧ WR<30% at Oct 23 → Option A to CEO; current 14d 54T +$0.96 = NOT met (#65 refresh)
- **volume-breakout-long+ habitat monitor #63:** trigger only if 30d turns negative (now +$0.87)
- **ai-trader-pending ATR-scaled SL — PRE-REGISTERED #64:** recheck Oct 26 (n=9 → ~20); flip only if n≥20 ∧ armed-rate <20% ∧ PnL<0 ∧ SL≥2×BTC 15m ATR does not inflate avg loss >50%. CEO domain.
- **pump-chain+ CONF_FLOOR raise 30→70 — REJECTED #64:** 30→70 increment sign-flips (7d −$0.18 / 14d +$0.24 / 30d −$0.46). Conf<70 overall p=0.0046 is carried by the <30 slice CONF_FLOOR already covers.
- **Stop-width-vs-ATR — REJECTED #64** (p=0.774, selection-on-outcome in loser-only views) | **same-direction exposure cap — REJECTED #64** (p=0.258, 19:00 cluster was 3.5h-open/120s-close)
- **REJECTED (do not re-propose):** global conf<30 floor | LONG 55-60 boost demote | LONG volume_spike<1.0 block (78% winner-kill, #63) | LONG×CALM gate | ema300-pin gate | gap-band asymmetry | stop-width vs ATR (#64) | same-direction exposure cap (#64) | pump-chain+ conf raise 30→70 (#64) | **65+ LONG band momentum-continuation signal (#65: 7d +$1.37 artifact, 14d/30d both negative)** | LONG 45-55 hard block (#65 re-reject: z=−0.88 p>0.05, fk >20%)
- **Escalation #17 (25th):** exit-ladder candle OOS — blocks ARM-GAP/peak-trail/post-arm flip

## BACKLOG / CEO DECISIONS PARKED

- **blacklist-tester.timer** — experiment concluded Aug 5 (0 KEEP/77), timer still fires; summarizer recommends disable → CEO call
- **logrotate for logs/** — disk 84% (19G free), pipeline.log 220M; health monitor watches 85% warn
- **15m/1h/4h candle retention** — only if disk tightens (2.9M rows reclaimable)
- Kanban "0.3x" text entries are historical drift; file (0.5x) is truth — new reports now file-truth
