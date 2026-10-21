# Current State — brain_auditor #50 Oct 21 ~07:40 UTC

**Last Updated: 2026-10-21 07:40 UTC**
**Updated by: brain_auditor #50 — 0 config changes (vacation soak). Near-miss timeout pre-registered (23T 0%WR -$2.25). pump-chain- kill recheck still Oct 22. DOGE #16321 trail-arm watch.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (vacation_size_reduce.json authoritative — 7d WR 36.4% < 37 AND PnL −$2.68 < 0, both resume legs failing).
- **24h 25T 5W −$0.28 (20.0%) — shallow, containing (max single loss $0.17).** 7d 154T 36.4% −$2.68.
- **7d exit family: TRAIL/WIN 55T 92.7% +$5.14 | CHOP/LOSS 91T 3.3% −$7.52.** Wealth gap unchanged — every dollar of profit comes from trail-armed trades.
- **Open 1: DOGE LONG #16321 bb-bounce-v2-long+ @0.081369, cur 0.081622, +0.31%, meta_rsi 50.0 (worst band)** — trail needs +0.09% more to arm. **WATCHDOG: exit flat if no trail arm by ~08:30 UTC.**
- **Regime: btc_15m LONG_BIAS, btc_4h LONG_BIAS, continuum AT, volatility LOW, acceleration POSITIVE, trend_quality STRONG_UP, wyckoff ACCUMULATION.** Mildly long accumulation pin.
- **Vacation mode ACTIVE** — shadow-first, no constants changes. Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #50 (07:40 UTC)

**0 config changes.**

1. **WATCHDOG TRIAGE:** 001 losing-streak URGENT — SHALLOW-BLEED-CONTAINED (15/20 lost but net −$0.33; chop family structural) | 002 wrong-side — VERIFIED (BTC SHORT #16320 closed atr_sl_hit, counter-trend in LONG_BIAS regime) | 003 pump-chain- streak — BARE BLEED CONFIRMED (14d 41T 19.5% −$0.88, kill trigger STILL MET, deferred Oct 22) | 004 pump-chain+ — KILL-REJECTED 9th (14d 55T +$0.99, EXTREME habitat +$1.68 carries it).
2. **LOSING AUTOPSY 24h: 18 losers, ZERO new patterns.** pump-chain- combo shorts ×6 (EXTREME, floor revert holding) | pump-chain+ timeouts ×3 (MFE 0.12-0.28 pure chop) | ai-trader-pending shorts ×2 (counter-trend) | ARM-GAP ×3. 4/5 winners trail-armed or hard_tp.
3. **NEAR-MISS BAND DEEP-DIVE (new finding):** MFE 0.30-0.40% without trail arm = 23T 0%WR −$2.25 14d. by_exit: atr_sl_hit 14T −$1.38, hard_max_loss 6T −$0.52. These trades had momentum but no follow-through — existing trail_arm_timeout (0.40%) misses them. **Pre-registered: near-miss timeout (cut at 0.30% MFE stuck).** Needs candle OOS.
4. **LAST-RUN VERIFY:** floor revert HOLDING ✓ (0 violations since 02:46) | ARM-GAP code LIVE ✓ (0 fires = correct) | TAT scope fix ✓ | size-reduce 0.5x HELD ✓ | protected 13/13 ✓.

## REJECTED THIS RUN

**pump-chain- bare-path kill flip — NOT flipped (already scheduled Oct 22 recheck).** 14d still 41T −$0.88, trigger met, but vacation soak + already deferred. Combo path (v6-confirmation) +$0.25 proves the confirmation layer IS the edge — bare signal has none.

## CREATIVE (this run)

**Near-miss timeout — PRE-REGISTERED.** 23T stuck at MFE 0.30-0.40% without arm, 0% WR. Would cut before SL collects. Needs candle OOS via escalation #16 vehicle. Zero winner-kill (none won).

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)

- **pump-chain- bare-path kill flip** (Oct 22 recheck: PUMP_CHAIN_V5_SHORT_ENABLED→False if 14d still <0)
- **pump-chain+ non-EXTREME 0.7x dampen** (#46)
- **Escalation #16 (23rd):** signal-scoped candle OOS vehicle — blocks near-miss timeout, dual-condition TAT, dampen confirmation, ARM-GAP trail-start fix
- **ARM-GAP peak-trail validation protocol** (n≥10 log lines)
- **pp-cond shadow flip:** failed bars (#39), re-eval vacation-end
- **coin_regime:** n=10/20 conf≥25
- **near-miss timeout** (this run, needs OOS)
