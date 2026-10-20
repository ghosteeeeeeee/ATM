# Current State — brain_auditor Oct 20 05:40 UTC

**Last Updated: 2026-10-20 05:40 UTC**
**Updated by: brain_auditor #34 — closed BTC #16293 regime-misaligned LONG at 81830 (−$0.02). Preceded by daily_orchestrator 05:00 (disk, atr_sl resolved) and brain_auditor #33 04:40 (coin_regime stamp).**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (7d WR 34.4% < 35 AND pnl −$3.62 < −$2 — both resume conditions failing).
- **24h 17T 4W −$0.96 (23.5%). | 7d 195T 67W −$3.62 (34.4%). | Trail ~97% WR vs Chop ~1% — separation unchanged. 24h winners 4/4 trail-family.**
- **0 open (flat)** — BTC #16293 closed 05:37 at 81830 (regime-misaligned SHORT_BIAS flip; price continued dumping after exit).
- **Regime: SHORT_BIAS 15m+4h | BTC AT/BELOW EMA300 81940 | trend_quality STRONG_DOWN | LOW vol CALM.** Stay flat / SHORT-only until EMA300 reclaim with volume.
- **Vacation mode ACTIVE** — shadow-first, no constants changes.
- Protected flags 13/13 INTACT.
- **atr_sl_hit flag RESOLVED** (7d 30.4% < 40%). Do not re-flag.

## THIS RUN — brain_auditor #34 (05:40 UTC)

**0 config changes (vacation). 1 position action.**

1. **CLOSED BTC LONG #16293** (ai-trader-pending, entry 81987 → exit 81830, −$0.02) — regime flipped SHORT_BIAS both TFs ~05:00, trade swimming upstream, watchdog: would-not-open-fresh. Exit preceded continued dump (saved ~$0.08 vs SL 81741 path).
2. Watchdog steers 001/002 VERIFIED, 003/004 MONITOR (kill rules not met: pump-chain+ 14d still +$1.09).
3. #33 coin_regime stamp verified PASS (0 stamped trades yet — expected, no execs since 04:41).
4. **CREATIVE pre-registered: regime-flip BE-rake SHADOW** — when direction disagrees with dual-TF flip and trade ±0.25% of entry, rake SL to BE. Ship post-vacation.

## PREVIOUS — brain_auditor #33 (04:40 UTC, abridged)

**SHIPPED: coin_regime + coin_regime_conf stamp** (decider_run.py:5000-5006) — reads `_hotset_regime` (already in scope at exec time), writes into `_exec_meta` alongside gap_at_entry/staleness/final_confidence. Zero-behavior. Unlocks the watchdog's core thesis ("coin regime at entry is the discriminator") for SQL analysis once 20+ stamped trades accumulate. Metadata previously had btc_regime only — per-token regime died at decision time.

**KEY FINDINGS:**
1. **GOAT SHORT RSI 73.6 = bear-exemption working, NOT a gate bug.** 14d SHORT detect-RSI 65-75 band: n=5 W=2 +$0.09 wash. ETC +$0.14 / LTC +$0.11 won same band. CEO Fix5 design correct. n≪20, no action.
2. **Watchdog's 5 pending oversold shorts (RSI 21-33) ALREADY BLOCKED** by SHORT_RSI_HARD_FLOOR=45 at both detect and exec time. They won't fill.
3. **gap_at_entry 1.0+ LONG = only profitable gap band** (14d 45T +$2.21 42.2% vs <0.5% 126T −$3.32 37.3%). ARB's 3 losses (gap 1.1-1.5) sit in the profitable band on aggregate — ARB-specific toxicity, not gap toxicity. **Do NOT tighten chase filters.**
4. **ARB 3x LONG losses verified:** all mid-band RSI 51-59, conf≤49.5 floor-admits, gap 1.1-1.5% — known cohorts, no new pattern.

**TAT STATUS: 11 unique fires since Oct 18** (base 7 true-saves / 3 false-kills; variant-C underwater-only 6S/0FK corrected). 4 more unique fires for the 15-fire flip bar. MFE-CUT: 6 unique fires.

**LAST-RUN VERIFY:** trailing_activated COMMENT ✓ | size-reduce 0.5x ✓ | TAT + MFE-CUT shadows collecting ✓ | ARM-BE dormant ✓ | protected 13/13 ✓.

**CEO ESCALATION CARRIED: exit-ladder signal-scoped backtest P0 (13th request).**

## PREVIOUS — brain_auditor #32 (03:42 UTC, abridged)
0 config (vacation). atr_sl recovery probe: 63% wrong-side / 37% tight-SL. TAT variant-C CORRECTED 6S/0FK not 9S/0FK.
