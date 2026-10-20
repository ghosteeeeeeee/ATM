# Current State — daily_orchestrator Oct 20 05:00 UTC

**Last Updated: 2026-10-20 05:00 UTC**
**Updated by: daily_orchestrator — disk cleanup (84%→83%), atr_sl_hit verified NOT a bug (7d 30.4% < 40%). Preceded by brain_auditor #33 04:40 (coin_regime stamp, zero-behavior).**

## PIPELINE STATUS

- **Trading LIVE** with size-reduce **0.5x** (marker 04:27; 7d WR 34.5% < 35 AND pnl −$3.39 < −$2). Auto-clears when WR≥35 AND pnl≥−$2, or WR≥37 AND pnl≥0.
- **24h 17T 5W −$0.88 (29.4%). | 7d 194T 67W −$3.39 (34.5%). | Trail ~$5.5 vs Chop ~−$7.9 — separation unchanged.**
- **1 open: BTC LONG #16293 ai-trader-pending +0.10% (1.7h, explicit SL/TP) HOLD.** (BLUR #16295 closed since last snapshot)
- **Vacation mode ACTIVE** — shadow-first, no constants changes.
- Protected flags 13/13 INTACT.
- **atr_sl_hit flag RESOLVED:** 24h 50% is n=8 thin-sample noise (avg −$0.05); 7d aggregate 30.4% < 40% line. SL-width study (CEO-gated) is the lever. Do not re-flag.
- **Disk 83%** (was 84%): journal vacuum 3d (717M freed) + stale archives removed. Remaining bloat = live DBs, not vacuumed mid-trading.

## THIS RUN — daily_orchestrator 05:00 UTC

**0 config changes. 1 infra action. 1 false-flag resolved.**

1. **Disk cleanup** — journalctl vacuum 3d freed 717M, removed 3 Oct-10 rotated log archives (~32M). 84%→83%, back under 85% WARN.
2. **atr_sl_hit 47-50% "monitor" flag closed** — not a bug (see above). auto_1hr can stop re-flagging; 7d rate is the correct measure and it's under threshold.

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
