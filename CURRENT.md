# Current State — brain_auditor Oct 22 2026-02:45 UTC

**Last Updated: 2026-10-22 02:45 UTC**
**Updated by: brain_auditor #67 — 0 trading-behavior changes (vacation soak final day). HEADLINE: (1) MIN_EXEC_CONFIDENCE 40→50 TESTED AND REJECTED-WITH-DATA (fk 31.5% > 20% bar, z p=0.214, non-pump bands non-monotonic). (2) CONF_FLOOR=30 re-verified INCREMENTALLY OPTIMAL — pump-chain bands <30 −$1.98 / 30-40 +$0.49 / 40-50 +$0.14 / 60-75 +$2.16; raising the floor to 40 or 50 would block POSITIVE bands. 30 is the knife edge, ships Oct 23 unchanged. (3) NEW: the queued Oct-23 stack (CONF_FLOOR −$1.85 + doji kill −$0.97) covers 88% of the fc40-50 bucket (−$3.22) — residual only −$0.40, so no global confidence floor is ever needed. Losers-vs-winners feature sweep: only final_confidence separates (p=0.013); rsi_14 p=0.55, volume_spike p=0.80, gap p=0.59, staleness p=0.055 → arm/no-arm stays the discriminator. Prior: brain_auditor #66 01:44.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** per `vacation_size_reduce.json` (file truth). Both resume legs still failing: 7d WR 36.7% AND PnL −$3.26 <0.
- **24h 33T 13W 39.4% −$0.77** — 20 losers never-armed chop, 13/13 winners trail-armed. **7d 159T 36.5% −$3.26.**
- **7d ARMED 64T 73.4% +$3.48 vs UNARMED 95T 11.6% −$6.74** (30d: 234T 78.2% +$16.79 vs 340T 19.7% −$21.74). Wealth gap unchanged.
- **Regime: bottoming repair / LOW volume (0.64)** — BTC below EMA300 ~84,400, continuum BELOW, scanner flipped LONG_BIAS, acceleration POSITIVE. 0 open flat 6h = correct (CONTINUUM-BLOCK 55 + BTC-CHOP 26 firing). Portfolio health: critical (watchdog).
- **Vacation mode ACTIVE to Oct 23** — shadow-first, no constants changes. Protected flags 13/13 INTACT.
- **READINESS: BTC reclaim EMA300 ~84,419 WITH volume → continuum-trend+ LONG (14d 8T 75% WR, 75% arm). Lose 84,180 with volume → SHORT only at RSI 55-65.**

## THIS RUN — brain_auditor #67 (2026-10-22 02:45 UTC)

**0 trading-behavior changes (vacation soak final day; every candidate is pre-registered for Oct 23+). 1 new candidate tested and rejected with data. 1 pre-ship verification upgraded from PASS to OPTIMAL. 1 loop closed.**

1. **HEADLINE — MIN_EXEC_CONFIDENCE 40→50 tested and REJECTED-WITH-DATA.** `final_confidence` 40-50 = **124T 31.5% −$3.22 (16d)** — the single largest bleed bucket ever isolated (every other band ≥−$0.76). But the lever fails three bars: (a) winner-kill 39/124 = **31.5% > 20% bar**; (b) two-proportion z on 40-50 vs 50+ = −1.24, **p=0.214 not significant**; (c) non-pump bands non-monotonic (40-50 −$1.49 / 50+ −$2.40) so confidence does not predict outside the pump-chain family. Global confidence floors stay dead.
2. **CONF_FLOOR=30 pre-ship verification upgraded to INCREMENTALLY OPTIMAL.** pump-chain family 16d by `trades.confidence`: **<30 40T 6W −$1.98 | 30-40 2T +$0.49 | 40-50 19T +$0.14 | 50-60 16T −$0.62 | 60-75 13T +$2.16 | 75+ 42T +$0.31.** Raising the floor to 40 or 50 would block **+$0.63 of positive PnL**; the old 30→70 proposal (#64) and any 30→40 variant are now closed with the same table. Ships Oct 23 unchanged.
3. **NEW: residual-bleed decomposition closes the confidence chapter.** fc40-50 −$3.22 = CONF_FLOOR −$1.85 (39T) + doji kill −$0.97 (16T) + **residual −$0.40 (12%)**. The queued Oct-23 stack therefore captures 88% of the largest bucket we have. Pre-registered kill-criteria: re-measure Oct 25; ship a signal-scoped floor only if residual ≤−$1.00 over 14d ∧ n≥20 ∧ fk<20%, else close permanently.
4. **LOSING AUTOPSY — 19 losers, 0 new patterns, with a full feature sweep.** 7d winners(n=51) vs losers(n=83): **final_confidence 116.4 vs 81.0 t=2.48 p=0.013 (only separator)**; rsi_14 53.3/52.2 p=0.55; volume_spike 0.67/0.63 p=0.80; gap_at_entry 0.25/0.14 p=0.59; staleness 2.06/2.82min p=0.055. Volume_spike LONG bands re-checked 16d (<0.5 171T −$1.64 | 0.5-1 52T −$1.18 | 1-2 25T +$0.42 | 2+ 12T −$0.55) — non-monotonic, and <1.0 block still 78% winner-kill (REJECTED stands). **arm/no-arm remains the discriminator.**
5. **WATCHDOG STEER 001 (wrong-side) — REFUTED for the 3rd run.** No entry feature predicts direction; the 20 losers are never-armed chop, and per the #61 opposite-side audit (p=0.116) the winning side on 85% of them is NO TRADE. Regime remains bottoming-repair / LOW volume; flat 0-open is correct.
6. **LAST-RUN VERIFY all PASS:** rsi_drift stamp **n=1 live** (POL drift 8.14, 0 ERROR, coverage 1/1 signal-path trades since ship) | ARM-GAP 1 line (SOL MFE 0.97 trail=FALSE) 0 ERROR | TAT **14/15** valid fires (no new fire since 2026-10-21 18:58 NEO #16344) | doji 0 trades since Oct 17 | volume-breakout 0 trades since Oct 15 14:24 | SHORT_RSI_HARD_FLOOR=45 **0 violations** (2 SHORT opens: CFX rsi 51.16, BTC ai-pending no-RSI known-exempt) | size-reduce **0.5x file truth** | protected **13/13** (12 real attrs + SIGNALS_REGISTRY) | kill flags V4/hmacd/oversold-bounce/volume-buildup+ all False, no leaks.
7. **PRE-REG STATUS:** pump-chain+ decay kill NOT MET (14d 53T +$0.02) | r2v2-long4 n=4 | volume_spike≥2.0 n=12(14d)/18(30d) | ai-trader-pending n=10 → Oct 26 | coin_regime n=48 p=0.45 COLLECT | arm-rate dampen shadow due at vacation-end.
8. **CREATIVE x2:** (a) residual confidence-bleed ledger + permanent kill-criteria (zero-behavior, re-measure Oct 25); (b) **pump-chain conf 60-75 premium study** — 13T +$2.16 from 10% of trades, top-3 winners (CRV +0.94, LDO +0.68, APT +0.53) all share EXTREME + gap≥1.10 + trail-armed. First *positive* (size-into) proposal for this family rather than another floor; collect to n≥20.
9. **SIDEWAYS:** `trades.confidence` and `final_confidence` are different scales (7d avg 62.0 vs 94.5; confidence = final − penalty offset). Any future floor must name its column. Pre-Oct-15 rows are unclamped (confidence max 499.4) → historical confidence-band queries unreliable.

## OLDER RUNS (condensed)

- **#61 20:56** — watchdog wrong-side REFUTED (opposite-side audit p=0.116, 85% no opposing setup = chop); LONG×CALM + ema300-pin gates REJECTED-WITH-DATA; STANDALONE_BYPASS exemption = CEO decree not drift.
- **#60 17:45** — shipped rsi_detect/rsi_exec/rsi_drift stamp (decider_run.py:5019, zero-behavior). Staleness filter + blanket EXTREME block REJECTED-WITH-DATA.
- **daily_orchestrator 17:00** — fixed `$0` shell-expansion corruption (48 strings), size-reduce reporting file-truth, auto_1hr regime-based kill policy.
- **#59 16:39** — WLD #16341 MFE false-peak root-caused (round-number 0.60); peak-sanity shadow pre-registered (close-time tick census vehicle).

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)
- **Residual confidence-bleed ledger — PRE-REGISTERED #67 (re-measure Oct 25):** fc40-50 −$3.22 = CONF_FLOOR −$1.85 + doji −$0.97 + residual −$0.40. Ship a signal-scoped floor only if residual ≤−$1.00 / 14d ∧ n≥20 ∧ fk<20%; else CLOSE the confidence-bleed chapter permanently.
- **pump-chain conf 60-75 premium study — PRE-REGISTERED #67:** 13T +$2.16, top-3 winners all EXTREME + gap≥1.10 + trail-armed. Positive (size-into) filter, collect to n≥20; test gap≥1.0 interaction as a SEPARATE second variable.
- **MIN_EXEC_CONFIDENCE 40→50 — REJECTED #67 (do not re-propose):** fk 31.5%, p=0.214, non-pump bands non-monotonic.
- **TAT (trail-arm-timeout) flip — READY AT 14/15 #66:** valid unique fires (scope-fixed bb-bounce + ai-trader+) = 14. First-fire counterfactual: base variant 7 SAVE +13.14pp vs 7 KILL −9.75pp = NET +3.39pp but fk 50% fails bar; **variant-C (fire only when pnl<0 at T) 5 SAVE +8.79pp / 0 KILL = fk 0%**. **Flip criteria LOCKED pre-15th-fire: 15 valid fires ∧ variant-C fk<20% ∧ net>0 ∧ CEO GO.**
- **coin_regime ALIGNED vs COUNTER — FIRST ANALYSIS RUN #66 (n=48):** ALIGNED 26T 42.3% +$0.10 vs COUNTER 22T 31.8% −$0.61 (LONG ALIGNED +$0.24 / LONG COUNTER −$0.42 / SHORT COUNTER 0/5). Directionally consistent but **p≈0.45 not significant, n=48 < 50 regime bar → COLLECT.** SHORT×COUNTER dampen cell still n=5 <20.
- **REJECTED #66 (do not re-propose):** same-token re-entry cooldown after same-day loss (14d: after-loss 65T 33.8% −$0.62 vs fresh 288T 35.8% −$4.36 = 2pp wash)

- **pump-chain- kill — VERDICT #63: CANCEL blanket kill** (collision: CONF_FLOOR captures 93% of bleed; kill destroys 8 winners +$1.27 for −$0.04 residual). Final disposition with CEO eyeball Oct 23. Oct 24: conf≥30 residual recheck → v6-requirement Option A only if n≥20 ∧ PnL<0 ∧ WR<30%.
- **PUMP_CHAIN_CONF_FLOOR=30 — PRE-SHIP VERIFIED #67 (OPTIMAL, ships Oct 23 CEO eyeball):** bands 30-40 +$0.49 / 40-50 +$0.14 prove 30 is the knife edge — do NOT raise. would-block 14d 40T 6W −$1.98 | winner-kill 6 × +$0.37 = 6.3% of pump-chain winners (under 20% bar) | **net save +$1.61** | 7d consistent 31T 3W −$1.98 | scope leak small (conf<30 non-pump −$0.28, covered elsewhere). Code NOT yet staged — stage Oct 23. LIVE PROOF: CFX #16347 entered conf 29.5.
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
