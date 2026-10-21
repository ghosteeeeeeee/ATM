# Current State — brain_auditor #51 Oct 21 ~08:50 UTC

**Last Updated: 2026-10-21 08:50 UTC**
**Updated by: brain_auditor #51 — 0 config changes (vacation soak). CRITICAL: pump-chain- dual-emitter finding — Oct 22 kill plan WRONG as specified. DOGE #16323 trail-arm watch.**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (vacation_size_reduce.json authoritative — 7d WR 36.7% < 37 AND PnL −$2.53 < 0, both resume legs failing).
- **24h 25T 5W −$0.18 (20.0%) — shallow, containing.** SHORT side is THE bleed: 9T 1W −$0.41 vs LONG 16T 5W +$0.23. Every SHORT loser closed ABOVE entry. 7d 150T 36.7% −$2.53.
- **7d exit family: TRAIL 43T 90.7% +$4.12 | CHOP 85T 3.5% −$6.82.** Wealth gap unchanged — every dollar of profit comes from trail-armed trades.
- **Open 2 LONG:** DOGE #16323 continuation+ @0.081926, meta_rsi 28.6 (worst band, trail-arm deadline ~10:15 UTC) | BTC #16322 continuum-trend+ @83100, rsi 50 (clean, hold).
- **Regime: btc_15m LONG_BIAS, btc_4h LONG_BIAS, continuum ABOVE 88min, zscore +1.29, STRONG_UP, MARKUP, CALM, LOW vol.** Tape 101 LONG_BIAS / 3 SHORT_BIAS (129 tokens).
- **Vacation mode ACTIVE** — shadow-first, no constants changes. Protected flags 13/13 INTACT.

## THIS RUN — brain_auditor #51 (08:50 UTC)

**0 config changes.**

1. **🚨 CRITICAL FINDING — PUMP-CHAIN- DUAL EMITTER:** Pre-registered Oct 22 kill (PUMP_CHAIN_V5_SHORT_ENABLED→False) is WRONG as specified. Two emitters produce bare `pump-chain-`: (a) pump_flow_signal.py:51 SOURCE_SHORT='pump-chain-' gated by PUMP_FLOW_MINUS_ENABLED=True, (b) pump_chain_v5_short.py:43 SOURCE='pump-chain-' gated by PUMP_CHAIN_V5_SHORT_ENABLED=True. signal_schema.py:2012 blocks only if BOTH False. **Killing V5_SHORT alone leaves pump_flow emitting the bleed AND kills the profitable combo path (+$0.26/14d).** Correct target: require v6 confirmation OR CEO decision on PUMP_FLOW_MINUS.
2. **WATCHDOG TRIAGE:** 001 losing-streak URGENT — SHALLOW-BLEED-CONTAINED (14/20 lost, net −$0.10; chop family structural) | 002 wrong-side — VERIFIED (all 5 SHORT losers closed above entry, counter-trend in LONG_BIAS tape 101/3) | 003 pump-chain+ streak — HIGH BLOCK SHIPPED 03:37 catches CFX/BLUR (were HIGH), APT/AIXBT EXTREME correctly unblocked (14d EXTREME +$1.91 carries signal) | 004 ai-trader-pending — counter-trend shorts, AI_TRADER=False since Oct 19, pending orders still fire | 005 pump-chain- — BARE BLEED CONFIRMED (14d 39T 20.5% −$0.75, kill trigger STILL MET, plan CORRECTED this run).
3. **LOSING AUTOPSY 24h: 18 losers, ZERO new patterns.** pump-chain- shorts ×6 (EXTREME, counter-trend) | pump-chain+ timeouts ×4 (meta_rsi 50-57, HIGH/EXTREME) | ai-trader-pending shorts ×2 (BTC counter-trend) | singles ×6. 6 winners: ZRO r2v2-long5 +16.4% (RSI 74.5), HYPE bb-squeeze+ +11.9% (65.6) — every winner had momentum at entry.
4. **LAST-RUN VERIFY:** floor revert HOLDING ✓ (0 shorts RSI<45 since 02:46) | ARM-GAP code LIVE ✓ (CRV #16318 MFE 0.585% trail=FALSE should log) | TAT scope fix ✓ | size-reduce 0.5x HELD ✓ | protected 13/13 ✓ | HIGH block SHIPPED ✓ (first validation pending).

## REJECTED THIS RUN

**pump-chain- bare-path kill flip — NOT flipped. Kill plan CORRECTED:** do NOT flip V5_SHORT alone Oct 22 (dual emitter — leaves pump_flow bleed alive, kills profitable combo). Correct path: v6-requirement gate (code change) or CEO decision on PUMP_FLOW_MINUS_ENABLED.

## CREATIVE (this run)

**pump-chain- v6-confirmation SHADOW — PRE-REGISTERED.** Log when pump-chain- SHORT fires without concurrent pump-chain-v6- co-signal. Bare 14d −$0.75 vs combo +$0.26 — confirmation IS the edge. Zero live behavior. Quantifies bare-fire cohort for v6-requirement gate.

## STANDING PRE-REGISTRATIONS (vacation-end Oct 23)

- **pump-chain- kill plan CORRECTED** (Oct 22: do NOT flip V5_SHORT; propose v6-requirement gate or CEO decision on PUMP_FLOW_MINUS)
- **pump-chain- v6-confirmation shadow** (this run)
- **pump-chain+ non-EXTREME 0.7x dampen** (#46)
- **Escalation #16 (23rd):** signal-scoped candle OOS vehicle — blocks near-miss timeout, dual-condition TAT, dampen confirmation, ARM-GAP trail-start fix
- **ARM-GAP peak-trail validation protocol** (n≥10 log lines)
- **pp-cond shadow flip:** failed bars (#39), re-eval vacation-end
- **coin_regime:** n=15/20 conf≥25 (15 stamped since Oct 20)
- **near-miss timeout** (needs OOS)
- **tape-alignment SHORT dampen** (watch — if SHORT bleed persists past vacation-end)
