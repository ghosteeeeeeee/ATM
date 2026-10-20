# Current State — brain_auditor #43 Oct 20 ~21:45 UTC

**Last Updated: 2026-10-20 21:45 UTC**
**Updated by: brain_auditor #43 — 0 config changes (vacation soak). NEW: giveback cohort quantified (17 armed trades died to static ATR-SL, −$1.06/7d). coin_regime conf-floor finding. Watchdog false-alarm on BTC trail steer.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (vacation_size_reduce.json authoritative; auto_1hr log text drifts "0.3x" — reporting-only, runtime reads 0.5).
- **24h 20T 5W −$0.16 (25%) — shallow, containing.** 7d 162T 36.4% −$2.41. 30d unchanged trajectory.
- **7d exit family: TRAIL 59T 81.4% +$4.44 | HML 26T 0% −$2.77 | OTHER 77T 14.3% −$4.08.** atr_sl_hit is now the #1 bleed (51T 2%WR −$3.57) — larger than HML.
- **Open: 1 BTC LONG continuum-osc+ #16309 @82398, +0.53%,5h.** coin_regime=LONG_BIAS aligned. HOLD (peak_exit protection live; watchdog "trail not arming" steer = FALSE ALARM, see below).
- **Regime: LONG_BIAS both timeframes, continuum ABOVE, zscore STRONG_POS, breadth 87L/4S — cleanest long tide in days. Volatility NORMAL.**
- **Vacation mode ACTIVE** — shadow-first, no constants changes. Protected flags intact (78 refs, 25/25 False).

## THIS RUN — brain_auditor #43 (21:45 UTC)

**0 config changes. New quantification + 1 watchdog false-alarm corrected.**

1. **GIVEBACK COHORT (NEW, 7d):** 25T with MFE≥0.40 closed negative = −$1.38. Breakdown: atr_sl_hit 17T −$1.06 (avg MFE 0.85% → avg exit −2.13%), deep giveback MFE≥0.80 = 11T −$0.74. **Root cause: armed trades dying to STATIC ATR-SL** — `_collect_atr_updates` computes SL from entry, never ratchets with peak. pump_exit signals already trail from peak (position_manager.py:2909); default path does not. Poster child: COMP SHORT MFE +1.18% → exited −7.61% (EXTREME). **CREATIVE pre-registered: peak-trail shadow for default ATR path** — needs candle OOS, NOT shipped during soak.
2. **WATCHDOG STEER TRIAGE:** 001 REJECT (4th+ identical shallow bleed) | 002 VERIFIED-STRUCTURAL | 003 KILL-REJECT (pump-chain− 14d net **+$0.54**, 57T 24.6% — positive family) | **BTC-trail-arm steer = FALSE ALARM** — trailing_activated is a post-hoc label (TRUE iff exit_reason ILIKE %trail%), always NULL on open trades. 16309 HOLD.
3. **coin_regime STUDY UPDATE (n=11/20):** raw COUNTER 6T 16.7% −$0.20 vs ALIGNED 5T 60% +$0.60. **Conf-floor finding: 4/6 COUNTER stamps have conf≤15 (PUMP/ZRO conf=0 = unknown, not counter).** With conf≥25 floor: COUNTER 2T −$0.06 vs ALIGNED 3T +$0.03 — direction holds, sample thinner. **Decision protocol amended: classify with conf≥25 at n≥20.** COMP counterexample: ALIGNED SHORT (SHORT_BIAS 53) still lost −7.61% — alignment prevents wrong-side bleed, not EXTREME giveback.
4. **LAST-RUN VERIFY:** ARM-GAP instrumentation ✓ (0 fires = correct, only close since ship was ZRO win) | TAT scope ✓ | stamps 11/20 ✓ | protected 25/25 ✓ | size-reduce 0.5x ✓.

## SIDeways FIND

- **watchdog deep-analysis** recommends "confirm trail arms next cycle" via trailing_activated on an open trade — field misuse. auto_executable=false so no live risk; flagged to watchdog owner.

## OPEN LOOPS

- **Escalation #15 (19th request):** trail-engine race / peak-trail backtest — giveback cohort now quantified (17T −$1.06/7d), still needs self_learner candle OOS.
- **coin_regime counter-regime dampen: 11/20** → decision at n≥20 with conf≥25 floor.
- **TAT bb-bounce flip: 9/15 valid unique fires** (need 6 more).
- **pp-cond shadow flip:** failed bars (#39), re-eval vacation-end.
- **Post-vacation stack: ~14+ unvalidated soaks** — CEO eyeball on resume (~Oct 23).
- **Mid-trade regime-flip monitor:** pre-registered #42, build after dampen decision or cohort matures.
- **Peak-trail shadow:** pre-registered this run, blocked on candle OOS design.
