# Current State — brain_auditor Oct 22 2026-01:44 UTC

**Last Updated: 2026-10-22 01:44 UTC**
**Updated by: brain_auditor #66 — 0 trading-behavior changes (vacation soak final day). HEADLINE: TAT flip-readiness measured at 14/15 valid unique fires — base variant NET +3.39pp but fk 50% fails bar; variant-C (fire only at negative pnl) 5 SAVE +8.79pp / 0 KILL fk 0%. Flip criteria LOCKED pre-15th-fire: 15 fires ∧ variant-C fk<20% ∧ net>0 ∧ CEO GO. pump-chain− kill recheck date reached → CANCEL confirmed (CONF_FLOOR collision). pump-chain+ decay kill NOT MET (14d +$0.02). hmacd kill-criteria MOOT (already disabled). coin_regime first analysis executed n=48: ALIGNED 42.3% +$0.10 vs COUNTER 31.8% −$0.61, p≈0.45 → COLLECT. Hotset-stall handoff NOT-A-BUG (gates actively firing). CONF_FLOOR=30 ships Oct 23 unchanged. Prior: brain_auditor #65 00:37.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** per `vacation_size_reduce.json` (file truth). Both resume legs still failing: 7d WR 36.7% AND PnL −$3.26 <0.
- **24h 33T 13W 39.4% −$0.87** — 20 losers never-armed chop, 13/13 winners trail-armed. **7d 158T 36.7% −$3.26.**
- **7d ARMED 63T 74.6% +$3.48 vs UNARMED 95T 11.6% −$6.74** (30d: 234T 78.2% +$16.79 vs 340T 19.7% −$21.74). Wealth gap unchanged.
- **Regime: bottoming repair / LOW volume (0.64)** — BTC below EMA300 ~84,400, continuum BELOW, scanner flipped LONG_BIAS, acceleration POSITIVE. 0 open flat 6h = correct (CONTINUUM-BLOCK 55 + BTC-CHOP 26 firing). Portfolio health: critical (watchdog).
- **Vacation mode ACTIVE to Oct 23** — shadow-first, no constants changes. Protected flags 13/13 INTACT.
- **READINESS: BTC reclaim EMA300 ~84,419 WITH volume → continuum-trend+ LONG (14d 8T 75% WR, 75% arm). Lose 84,180 with volume → SHORT only at RSI 55-65.**

## THIS RUN — brain_auditor #66 (2026-10-22 01:45 UTC)

**0 trading-behavior changes (vacation soak final day). 1 scheduled kill disposition closed, 1 flip-readiness measured, 1 first-analysis executed, 1 handoff refuted.**

1. **HEADLINE — TAT flip-readiness measured: 14/15 valid unique fires.** Counted `[SHADOW] TRAIL-ARM would-fire` lines in pipeline.log with Oct-20 scope fix (bb-bounce + ai-trader+ only; manual/pending excluded): 9 valid pre-Oct20 + 5 since = **14, one short of the 15-fire flip bar.** First-fire counterfactual (min age per trade vs actual close): **base variant 7 SAVE +13.14pp / 7 KILL −9.75pp = NET +3.39pp but fk 7/14 = 50% FAILS the fk<20% bar** (worst kills: DOGE #16321 fire +0.31→actual +3.64 = −3.33pp; AIXBT #16330 −2.45pp). **variant-C (fire only when live_pnl<0 at T): 5 SAVE +8.79pp / 0 KILL = fk 0%** — passes fk bar, saves every never-armed loser at ~−0.2% instead of −1.7..−3.5%. **Flip criteria LOCKED before the 15th fire arrives: 15 valid fires ∧ variant-C fk<20% ∧ net>0 ∧ CEO GO.** Re-eval the moment fire #15 prints (likely within days at current cadence).
2. **pump-chain− kill recheck (pre-registered date TODAY): CANCEL CONFIRMED — final disposition.** Fresh: bare 14d 37T 8W 21.6% −$0.57 (EXTREME 33T −$0.43 / NORMAL 4T −$0.14), arm-rate 21.6%. Paper trigger MET but collision evidence from #63 stands: CONF_FLOOR=30 captures 93% of bleed; all 8 bare winners conf≥30 (+$1.27); kill residual = −$0.04. **Kill destroys +$1.27 to catch −$0.04 → no kill.** CONF_FLOOR ships Oct 23; conf≥30 residual recheck Oct 24 (Option A v6-requirement only if n≥20 ∧ PnL<0 ∧ WR<30%).
3. **pump-chain+ decay kill criteria: NOT MET (#66 refresh).** 14d 53T 30.2% **+$0.02** (needs PnL<0 ∧ WR<30 ∧ n≥20). 7d 21T 19.0% −$0.26 = the decay watch. Recheck Oct 23 per pre-registration. (Kill rejected 8x on positive-14d now.)
4. **hmacd kill-criteria: CLOSED MOOT.** HMACD_MTF_PLUS/MINUS already False (killed Oct 13/15), last trade Oct 13 — n can never reach the 20 bar. Criteria retired instead of lingering forever.
5. **coin_regime ALIGNED vs COUNTER — first full execution (pre-registered n≥20 threshold met).** 14d stamped cohort n=48: **ALIGNED 26T 42.3% +$0.10 vs COUNTER 22T 31.8% −$0.61.** LONG ALIGNED 22T 45.5% +$0.24 / LONG COUNTER 17T 41.2% −$0.42 / SHORT COUNTER **0/5 −$0.19.** Two-proportion z on WR: **p≈0.45 NOT significant**; n=48 just under the 50 regime-level bar. Direction is consistent with the thesis (counter loses both directions) but **COLLECT, do not ship.** SHORT×COUNTER dampen pre-reg cell still n=5 <20.
6. **WATCHDOG TRIAGE: 001 REJECT-SHALLOW** (12/20 lost but 24h −$0.87/33T, same cohorts, no mechanism failing) | **002 REFUTED-STANDS** (20 losers = never-armed chop; 13/13 winners trail-armed; opposite-side audit p=0.116 → winning side is NO TRADE) | **handoff hotset-stall NOT-A-BUG** — hotset.json rewritten 01:32, gates actively firing (CONTINUUM-BLOCK 55, BTC-CHOP-GATE 26, CONFLUENCE 8, VOL-GATE 6, HOT-SET 3). Generation-time blocks never insert into approved[], so empty approved is by design, not a stalled path. Fix remains the reclaim/breakdown trigger, not looser gates.
7. **LOSING AUTOPSY 20 losers → 0 new patterns.** 7 hard_max_loss mid-band LONGs (PUMP/STX/POL/INJ×2/XPL — RSI 50-65, volume_spike 0.22-0.69, gap +0.3..+1.2 chasing, MFE~0) | 3 counter shorts bounce-stopped (CFX/CRV/COMP) | trail-then-small-loss ×2 (SYRUP/GOAT noise). **rsi_14 does NOT separate: losers 32-71, winners 22-73** — arm/no-arm is the discriminator, not entry RSI or direction. All cohorts already covered by CONF_FLOOR (Oct 23) + floor-45 + midband block.
8. **REJECTED-WITH-DATA: same-token re-entry cooldown** — 14d re-entries after same-day loss 65T 33.8% −$0.62 vs fresh-entry 288T 35.8% −$4.36; 2pp WR gap = wash. Logged so it is not re-proposed.
9. **LAST-RUN VERIFY all PASS** — rsi_drift stamp 1/1 (only 1 trade opened since ship = coverage 100%, no path gap) | ARM-GAP 1 line (SOL) 0 ERROR | floor-45 0 SHORT opens in 8h | doji 0 since Oct 17 | volume-breakout/hmacd kills 0 leaks | size-reduce 0.5x file truth | protected **13/13**.
10. **CONF_FLOOR=30 fresh pre-ship (ships Oct 23 unchanged):** conf<30 pump-chain 14d 40T 6W −$1.98 15.0% vs conf≥30 75T 30.7% +$1.33 → net save +$1.61, fk 6.3%.

## OLDER RUNS (condensed)

- **#61 20:56** — watchdog wrong-side REFUTED (opposite-side audit p=0.116, 85% no opposing setup = chop); LONG×CALM + ema300-pin gates REJECTED-WITH-DATA; STANDALONE_BYPASS exemption = CEO decree not drift.
- **#60 17:45** — shipped rsi_detect/rsi_exec/rsi_drift stamp (decider_run.py:5019, zero-behavior). Staleness filter + blanket EXTREME block REJECTED-WITH-DATA.
- **daily_orchestrator 17:00** — fixed `$0` shell-expansion corruption (48 strings), size-reduce reporting file-truth, auto_1hr regime-based kill policy.
- **#59 16:39** — WLD #16341 MFE false-peak root-caused (round-number 0.60); peak-sanity shadow pre-registered (close-time tick census vehicle).

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)
- **TAT (trail-arm-timeout) flip — READY AT 14/15 #66:** valid unique fires (scope-fixed bb-bounce + ai-trader+) = 14. First-fire counterfactual: base variant 7 SAVE +13.14pp vs 7 KILL −9.75pp = NET +3.39pp but fk 50% fails bar; **variant-C (fire only when pnl<0 at T) 5 SAVE +8.79pp / 0 KILL = fk 0%**. **Flip criteria LOCKED pre-15th-fire: 15 valid fires ∧ variant-C fk<20% ∧ net>0 ∧ CEO GO.**
- **coin_regime ALIGNED vs COUNTER — FIRST ANALYSIS RUN #66 (n=48):** ALIGNED 26T 42.3% +$0.10 vs COUNTER 22T 31.8% −$0.61 (LONG ALIGNED +$0.24 / LONG COUNTER −$0.42 / SHORT COUNTER 0/5). Directionally consistent but **p≈0.45 not significant, n=48 < 50 regime bar → COLLECT.** SHORT×COUNTER dampen cell still n=5 <20.
- **REJECTED #66 (do not re-propose):** same-token re-entry cooldown after same-day loss (14d: after-loss 65T 33.8% −$0.62 vs fresh 288T 35.8% −$4.36 = 2pp wash)

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
- **hmacd family kill-criteria — CLOSED MOOT #66** — HMACD_MTF_PLUS/MINUS already False (killed Oct 13/15), last trade Oct 13; n can never reach 20. Criteria retired.
- **hl_copy_trader watch** — 14d 11T 27% −$0.20, n<20; CEO domain
- **stale_exit cohort watch** — SYRUP −$0.23 today, continuation+ 4T/24h −$0.18 n<20
- **pp-cond shadow flip** — failed bars, re-eval vacation-end
- **post-arm breakeven ratchet** — blocked on escalation #17 candle OOS
- **pump-chain+ decay kill criteria — PRE-REGISTERED #62:** trigger = 14d n≥20 ∧ PnL<0 ∧ WR<30% at Oct 23 → Option A to CEO; **current 14d 53T +$0.02 30.2% = NOT met (#66 refresh; 7d −$0.26 monitor)**
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
